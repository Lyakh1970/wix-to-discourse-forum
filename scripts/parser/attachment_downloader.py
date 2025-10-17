#!/usr/bin/env python3
"""
Модуль для скачивания вложений из WIX форума
"""

import asyncio
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

import aiohttp
from loguru import logger
from tqdm import tqdm


class AttachmentDownloader:
    """Класс для скачивания вложений"""
    
    def __init__(self, config: Dict):
        """
        Инициализация загрузчика
        
        Args:
            config: Конфигурация из wix_config.yaml
        """
        self.config = config
        self.download_dir = Path(config['attachments']['download_dir'])
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.downloaded_count = 0
        self.failed_count = 0
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def _get_file_extension(self, filename: str, url: str) -> str:
        """
        Определение расширения файла
        
        Args:
            filename: Имя файла
            url: URL файла
            
        Returns:
            Расширение файла с точкой
        """
        # Попробовать извлечь из имени файла
        if '.' in filename:
            return '.' + filename.split('.')[-1].lower()
        
        # Если не удалось, попробовать из URL
        parsed = urlparse(url)
        if '.' in parsed.path:
            return '.' + parsed.path.split('.')[-1].lower()
        
        return ''
    
    def _generate_safe_filename(self, original_filename: str, url: str) -> str:
        """
        Генерация безопасного имени файла
        
        Args:
            original_filename: Оригинальное имя файла
            url: URL файла
            
        Returns:
            Безопасное имя файла
        """
        # Использовать хэш URL для уникальности
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        
        # Очистить имя файла от специальных символов
        safe_name = "".join(
            c for c in original_filename 
            if c.isalnum() or c in (' ', '.', '_', '-')
        ).strip()
        
        # Если имя пустое, использовать хэш
        if not safe_name or safe_name == '.':
            ext = self._get_file_extension(original_filename, url)
            safe_name = f"attachment_{url_hash}{ext}"
        else:
            # Добавить хэш к имени для уникальности
            name_parts = safe_name.rsplit('.', 1)
            if len(name_parts) == 2:
                safe_name = f"{name_parts[0]}_{url_hash}.{name_parts[1]}"
            else:
                safe_name = f"{safe_name}_{url_hash}"
        
        return safe_name
    
    def _is_allowed_extension(self, filename: str) -> bool:
        """
        Проверка разрешенного расширения файла
        
        Args:
            filename: Имя файла
            
        Returns:
            True если расширение разрешено
        """
        allowed = self.config['attachments']['allowed_extensions']
        
        # Если список пустой, разрешить все
        if not allowed:
            return True
        
        ext = Path(filename).suffix.lower()
        return ext in allowed
    
    async def download_file(
        self, 
        url: str, 
        filename: str,
        post_id: str = None
    ) -> Optional[str]:
        """
        Скачивание одного файла
        
        Args:
            url: URL файла
            filename: Оригинальное имя файла
            post_id: ID поста (для организации по папкам)
            
        Returns:
            Путь к сохраненному файлу или None при ошибке
        """
        try:
            # Проверить расширение
            if not self._is_allowed_extension(filename):
                logger.warning(f"Пропущен файл с неразрешенным расширением: {filename}")
                return None
            
            # Генерировать безопасное имя файла
            safe_filename = self._generate_safe_filename(filename, url)
            
            # Определить путь сохранения
            if post_id:
                save_dir = self.download_dir / post_id
                save_dir.mkdir(parents=True, exist_ok=True)
            else:
                save_dir = self.download_dir
            
            file_path = save_dir / safe_filename
            
            # Проверить, не скачан ли уже файл
            if file_path.exists():
                logger.debug(f"Файл уже существует: {file_path}")
                return str(file_path)
            
            # Скачать файл
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status != 200:
                    logger.error(f"Ошибка загрузки {url}: HTTP {response.status}")
                    self.failed_count += 1
                    return None
                
                # Проверить размер файла
                content_length = response.headers.get('Content-Length')
                if content_length:
                    size_mb = int(content_length) / (1024 * 1024)
                    max_size = self.config['attachments']['max_file_size']
                    
                    if size_mb > max_size:
                        logger.warning(
                            f"Файл слишком большой ({size_mb:.1f} MB): {filename}"
                        )
                        self.failed_count += 1
                        return None
                
                # Сохранить файл
                content = await response.read()
                file_path.write_bytes(content)
                
                logger.debug(f"Скачан файл: {filename} → {file_path}")
                self.downloaded_count += 1
                
                return str(file_path)
                
        except asyncio.TimeoutError:
            logger.error(f"Таймаут при загрузке: {url}")
            self.failed_count += 1
            return None
            
        except Exception as e:
            logger.exception(f"Ошибка при загрузке {url}: {e}")
            self.failed_count += 1
            return None
    
    async def download_attachments(
        self,
        attachments: List[Dict],
        post_id: str = None,
        show_progress: bool = True
    ) -> List[Dict]:
        """
        Скачивание списка вложений
        
        Args:
            attachments: Список словарей с данными вложений
            post_id: ID поста
            show_progress: Показывать прогресс-бар
            
        Returns:
            Обновленный список вложений с локальными путями
        """
        if not attachments:
            return []
        
        iterator = tqdm(attachments, desc="Скачивание вложений") if show_progress else attachments
        
        updated_attachments = []
        
        for attachment in iterator:
            url = attachment.get('url')
            filename = attachment.get('filename', 'unknown')
            
            if not url:
                logger.warning(f"Пропущено вложение без URL: {filename}")
                continue
            
            local_path = await self.download_file(url, filename, post_id)
            
            # Обновить данные вложения
            attachment['downloaded'] = local_path is not None
            attachment['local_path'] = local_path
            
            updated_attachments.append(attachment)
            
            # Небольшая задержка между загрузками
            await asyncio.sleep(0.5)
        
        return updated_attachments
    
    def get_stats(self) -> Dict:
        """
        Получить статистику загрузок
        
        Returns:
            Словарь со статистикой
        """
        return {
            'downloaded': self.downloaded_count,
            'failed': self.failed_count,
            'total': self.downloaded_count + self.failed_count
        }


async def test_download():
    """Тестовая функция"""
    # Пример использования
    import yaml
    
    with open('config/wix_config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    test_attachments = [
        {
            'filename': 'test_document.pdf',
            'url': 'https://example.com/file.pdf'
        }
    ]
    
    async with AttachmentDownloader(config) as downloader:
        updated = await downloader.download_attachments(
            test_attachments,
            post_id='test_post_123'
        )
        
        print("Статистика:", downloader.get_stats())
        print("Результат:", updated)


if __name__ == "__main__":
    asyncio.run(test_download())

