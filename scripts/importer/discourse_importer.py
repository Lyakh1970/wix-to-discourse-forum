#!/usr/bin/env python3
"""
Импортер данных в Discourse форум
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

import httpx
import yaml
from loguru import logger
from tqdm import tqdm


class DiscourseImporter:
    """Класс для импорта данных в Discourse"""
    
    def __init__(self, config_path: str = "config/discourse_config.yaml"):
        """
        Инициализация импортера
        
        Args:
            config_path: Путь к конфигурационному файлу
        """
        self.config = self._load_config(config_path)
        
        self.base_url = self.config['discourse_url'].rstrip('/')
        self.api_key = self.config['api']['key']
        self.api_username = self.config['api']['username']
        
        self.client: Optional[httpx.AsyncClient] = None
        
        # Статистика
        self.stats = {
            'categories_created': 0,
            'topics_created': 0,
            'posts_created': 0,
            'attachments_uploaded': 0,
            'errors': 0
        }
        
        # Мапинг старых ID к новым
        self.category_mapping = {}
        self.user_mapping = {}
        
        self._setup_logging()
    
    def _load_config(self, config_path: str) -> Dict:
        """Загрузка конфигурации"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _setup_logging(self):
        """Настройка логирования"""
        log_config = self.config.get('logging', {})
        log_file = log_config.get('file', './logs/discourse_importer.log')
        
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            log_file,
            rotation="10 MB",
            retention="1 week",
            level=log_config.get('level', 'INFO'),
            encoding='utf-8'
        )
    
    async def __aenter__(self):
        """Async context manager entry"""
        headers = {
            'Api-Key': self.api_key,
            'Api-Username': self.api_username,
            'Content-Type': 'application/json'
        }
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=30.0
        )
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.aclose()
    
    async def _api_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Optional[Dict]:
        """
        Выполнение API запроса к Discourse
        
        Args:
            method: HTTP метод (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            **kwargs: Дополнительные параметры для httpx
            
        Returns:
            JSON ответ или None при ошибке
        """
        try:
            response = await self.client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            
            if response.status_code == 204:  # No Content
                return {}
            
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP ошибка {e.response.status_code} при запросе {endpoint}: {e.response.text}"
            )
            self.stats['errors'] += 1
            return None
            
        except Exception as e:
            logger.exception(f"Ошибка при запросе {endpoint}: {e}")
            self.stats['errors'] += 1
            return None
    
    async def create_category(
        self,
        name: str,
        slug: str,
        description: str = "",
        parent_category_id: Optional[int] = None,
        color: str = "0088CC"
    ) -> Optional[int]:
        """
        Создание категории в Discourse
        
        Args:
            name: Название категории
            slug: URL slug
            description: Описание
            parent_category_id: ID родительской категории
            color: Цвет в hex формате
            
        Returns:
            ID созданной категории или None
        """
        if self.config['import']['dry_run']:
            logger.info(f"[DRY RUN] Создание категории: {name}")
            return 999  # Fake ID for dry run
        
        payload = {
            'name': name,
            'slug': slug,
            'color': color,
            'text_color': 'FFFFFF'
        }
        
        if description:
            payload['description'] = description
        
        if parent_category_id:
            payload['parent_category_id'] = parent_category_id
        
        result = await self._api_request(
            'POST',
            '/categories.json',
            json=payload
        )
        
        if result and 'category' in result:
            category_id = result['category']['id']
            logger.info(f"Создана категория: {name} (ID: {category_id})")
            self.stats['categories_created'] += 1
            return category_id
        
        return None
    
    async def create_topic(
        self,
        title: str,
        raw: str,
        category_id: int,
        created_at: Optional[datetime] = None,
        tags: List[str] = None
    ) -> Optional[int]:
        """
        Создание топика в Discourse
        
        Args:
            title: Заголовок топика
            raw: Содержимое (Markdown)
            category_id: ID категории
            created_at: Дата создания (для backdating)
            tags: Список тегов
            
        Returns:
            ID созданного топика или None
        """
        if self.config['import']['dry_run']:
            logger.info(f"[DRY RUN] Создание топика: {title}")
            return 999  # Fake ID
        
        payload = {
            'title': title,
            'raw': raw,
            'category': category_id
        }
        
        if tags:
            payload['tags'] = tags
        
        if created_at and self.config['content']['preserve_dates']:
            payload['created_at'] = created_at.isoformat()
        
        result = await self._api_request(
            'POST',
            '/posts.json',
            json=payload
        )
        
        if result and 'topic_id' in result:
            topic_id = result['topic_id']
            logger.info(f"Создан топик: {title} (ID: {topic_id})")
            self.stats['topics_created'] += 1
            return topic_id
        
        return None
    
    async def create_post(
        self,
        topic_id: int,
        raw: str,
        created_at: Optional[datetime] = None
    ) -> Optional[int]:
        """
        Создание поста (комментария) в топике
        
        Args:
            topic_id: ID топика
            raw: Содержимое (Markdown)
            created_at: Дата создания
            
        Returns:
            ID созданного поста или None
        """
        if self.config['import']['dry_run']:
            logger.debug(f"[DRY RUN] Создание поста в топике {topic_id}")
            return 999
        
        payload = {
            'topic_id': topic_id,
            'raw': raw
        }
        
        if created_at and self.config['content']['preserve_dates']:
            payload['created_at'] = created_at.isoformat()
        
        result = await self._api_request(
            'POST',
            '/posts.json',
            json=payload
        )
        
        if result and 'id' in result:
            post_id = result['id']
            self.stats['posts_created'] += 1
            return post_id
        
        return None
    
    async def upload_attachment(
        self,
        file_path: str,
        topic_id: Optional[int] = None
    ) -> Optional[str]:
        """
        Загрузка вложения в Discourse
        
        Args:
            file_path: Путь к файлу
            topic_id: ID топика (опционально)
            
        Returns:
            URL загруженного файла или None
        """
        if self.config['import']['dry_run']:
            logger.debug(f"[DRY RUN] Загрузка файла: {file_path}")
            return "http://example.com/fake-upload.pdf"
        
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                logger.error(f"Файл не найден: {file_path}")
                return None
            
            # Проверка размера файла
            size_mb = file_path.stat().st_size / (1024 * 1024)
            max_size = self.config['attachments']['max_file_size']
            
            if size_mb > max_size:
                logger.warning(f"Файл слишком большой ({size_mb:.1f} MB): {file_path}")
                return None
            
            # Подготовка данных для загрузки
            files = {
                'file': (file_path.name, open(file_path, 'rb'))
            }
            
            params = {'type': 'composer'}
            if topic_id:
                params['topic_id'] = topic_id
            
            # Убрать Content-Type заголовок для multipart/form-data
            headers = dict(self.client.headers)
            headers.pop('Content-Type', None)
            
            response = await self.client.post(
                '/uploads.json',
                files=files,
                params=params,
                headers=headers
            )
            
            response.raise_for_status()
            result = response.json()
            
            if 'url' in result:
                upload_url = result['url']
                logger.debug(f"Загружен файл: {file_path.name} → {upload_url}")
                self.stats['attachments_uploaded'] += 1
                return upload_url
            
        except Exception as e:
            logger.exception(f"Ошибка при загрузке файла {file_path}: {e}")
            self.stats['errors'] += 1
        
        return None
    
    async def import_from_json(self, json_file: str):
        """
        Импорт данных из JSON файла
        
        Args:
            json_file: Путь к JSON файлу с экспортированными данными
        """
        logger.info("=" * 80)
        logger.info("НАЧАЛО ИМПОРТА В DISCOURSE")
        logger.info("=" * 80)
        
        # Загрузить данные
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        categories = data.get('categories', [])
        
        # Импорт категорий
        for category in tqdm(categories, desc="Импорт категорий"):
            await self._import_category(category)
            
            # Задержка между запросами
            await asyncio.sleep(self.config['import']['delay_between_requests'])
        
        # Сохранение статистики
        self.save_stats()
        
        logger.info("=" * 80)
        logger.info("ИМПОРТ ЗАВЕРШЕН")
        logger.info(f"Статистика: {self.stats}")
        logger.info("=" * 80)
    
    async def _import_category(self, category: Dict):
        """Импорт одной категории со всем содержимым"""
        from slugify import slugify
        
        # Создать категорию
        category_id = await self.create_category(
            name=category['title'],
            slug=slugify(category['title']),
            description=category.get('description', '')
        )
        
        if not category_id:
            logger.error(f"Не удалось создать категорию: {category['title']}")
            return
        
        # Сохранить маппинг
        self.category_mapping[category.get('id')] = category_id
        
        # Импорт подкатегорий
        for subcategory in category.get('subcategories', []):
            await self._import_subcategory(subcategory, category_id)
    
    async def _import_subcategory(self, subcategory: Dict, parent_id: int):
        """Импорт подкатегории"""
        from slugify import slugify
        
        # Создать подкатегорию
        subcat_id = await self.create_category(
            name=subcategory['title'],
            slug=slugify(subcategory['title']),
            parent_category_id=parent_id
        )
        
        if not subcat_id:
            return
        
        # Импорт постов
        for post in subcategory.get('posts', []):
            await self._import_post(post, subcat_id)
            await asyncio.sleep(self.config['import']['delay_between_requests'])
    
    async def _import_post(self, post: Dict, category_id: int):
        """Импорт поста"""
        from ..parser.utils import html_to_markdown
        
        # Конвертировать контент
        content = post.get('content', '')
        if self.config['content']['convert_to_markdown']:
            content = html_to_markdown(content)
        
        # Добавить disclaimer если нужно
        if self.config['content']['add_disclaimer']:
            disclaimer = self.config['content']['disclaimer_text'].format(
                date=post.get('created_at', 'неизвестно')
            )
            content = f"{content}\n\n{disclaimer}"
        
        # Создать топик
        created_at = None
        if post.get('created_at'):
            from dateutil import parser as date_parser
            try:
                created_at = date_parser.parse(post['created_at'])
            except:
                pass
        
        topic_id = await self.create_topic(
            title=post['title'],
            raw=content,
            category_id=category_id,
            created_at=created_at
        )
        
        if not topic_id:
            return
        
        # Импорт вложений
        if self.config['attachments']['upload_attachments']:
            for attachment in post.get('attachments', []):
                if attachment.get('local_path'):
                    await self.upload_attachment(
                        attachment['local_path'],
                        topic_id
                    )
        
        # Импорт комментариев
        for comment in post.get('comments', []):
            comment_content = comment.get('content', '')
            if self.config['content']['convert_to_markdown']:
                comment_content = html_to_markdown(comment_content)
            
            await self.create_post(topic_id, comment_content)
    
    def save_stats(self):
        """Сохранение статистики импорта"""
        if not self.config['stats']['save_stats']:
            return
        
        stats_file = Path(self.config['stats']['stats_file'])
        stats_file.parent.mkdir(parents=True, exist_ok=True)
        
        stats_data = {
            'import_date': datetime.now().isoformat(),
            'discourse_url': self.base_url,
            'statistics': self.stats
        }
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Статистика сохранена в: {stats_file}")


async def main():
    """Главная функция"""
    import sys
    
    if len(sys.argv) < 2:
        print("Использование: python discourse_importer.py <путь_к_json_файлу>")
        return
    
    json_file = sys.argv[1]
    
    async with DiscourseImporter() as importer:
        await importer.import_from_json(json_file)


if __name__ == "__main__":
    asyncio.run(main())

