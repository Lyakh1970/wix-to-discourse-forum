#!/usr/bin/env python3
"""
Основной парсер для WIX форума Fishery Group
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from playwright.async_api import async_playwright, Page, Browser
import yaml
from tqdm import tqdm

from .attachment_downloader import AttachmentDownloader

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/parser.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class WixForumParser:
    """Парсер для извлечения данных из WIX форума"""
    
    def __init__(self, config_path: str = "config/wix_config.yaml"):
        """
        Инициализация парсера
        
        Args:
            config_path: Путь к конфигурационному файлу
        """
        self.config = self._load_config(config_path)
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
        # Данные
        self.categories: List[Dict] = []
        self.subcategories: List[Dict] = []
        self.posts: List[Dict] = []
        
        # Статистика
        self.stats = {
            'categories_parsed': 0,
            'subcategories_parsed': 0,
            'posts_parsed': 0,
            'comments_parsed': 0,
            'files_downloaded': 0,
            'errors_count': 0
        }
        
        # Загрузчик вложений
        self.downloader: Optional[AttachmentDownloader] = None
        
    def _load_config(self, config_path: str) -> Dict:
        """Загрузка конфигурации из YAML"""
        # Создать директорию для логов
        Path('logs').mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
        
    async def initialize_browser(self):
        """Инициализация браузера Playwright"""
        logger.info("Инициализация браузера...")
        
        playwright = await async_playwright().start()
        
        self.browser = await playwright.chromium.launch(
            headless=self.config['parsing']['headless']
        )
        
        context = await self.browser.new_context(
            user_agent=self.config['parsing']['user_agent']
        )
        
        self.page = await context.new_page()
        
        # Установить таймаут
        self.page.set_default_timeout(
            self.config['parsing']['page_load_timeout'] * 1000
        )
        
        logger.info("Браузер инициализирован")
        
    async def login(self):
        """Авторизация на форуме (если требуется)"""
        auth_config = self.config.get('auth', {})
        
        if not auth_config.get('required', False):
            logger.info("Авторизация не требуется")
            return
            
        logger.info("Выполнение авторизации...")
        
        try:
            # Перейти на страницу входа
            await self.page.goto(self.config['forum_url'])
            await self.page.wait_for_load_state('networkidle')
            
            # Найти и кликнуть на кнопку "Log In"
            login_button = await self.page.query_selector('text="Log In"')
            if not login_button:
                # Попробовать альтернативные селекторы
                login_button = await self.page.query_selector('[data-testid="signUp.switchToSignUp"]')
            
            if login_button:
                await login_button.click()
                await self.page.wait_for_timeout(2000)  # Подождать открытия формы
                
                # Заполнить форму входа
                # Попробовать найти поля email и password
                email_input = await self.page.query_selector('input[type="email"], input[name="email"]')
                password_input = await self.page.query_selector('input[type="password"], input[name="password"]')
                
                if email_input and password_input:
                    await email_input.fill(auth_config['username'])
                    await password_input.fill(auth_config['password'])
                    
                    # Найти и кликнуть кнопку входа
                    submit_button = await self.page.query_selector('button[type="submit"]')
                    if submit_button:
                        await submit_button.click()
                        await self.page.wait_for_load_state('networkidle')
                        await self.page.wait_for_timeout(3000)  # Подождать завершения авторизации
                        
                        logger.info("✓ Авторизация выполнена успешно")
                    else:
                        logger.warning("Не найдена кнопка отправки формы")
                else:
                    logger.warning("Не найдены поля ввода логина/пароля")
            else:
                logger.warning("Не найдена кнопка Log In - возможно уже авторизованы")
                
        except Exception as e:
            logger.error(f"✗ Ошибка при авторизации: {e}")
            # Продолжаем работу даже если авторизация не удалась
        
    async def parse_categories(self) -> List[Dict]:
        """
        Парсинг категорий форума
        
        Returns:
            Список категорий с метаданными
        """
        logger.info("Начало парсинга категорий...")
        
        try:
            await self.page.goto(self.config['forum_url'])
            await self.page.wait_for_load_state('networkidle')
            await self.page.wait_for_timeout(2000)  # Дать время для загрузки динамического контента
            
            categories = []
            
            # Найти все элементы категорий
            category_elements = await self.page.query_selector_all(
                self.config['selectors']['category_item']
            )
            
            logger.info(f"Найдено элементов категорий: {len(category_elements)}")
            
            # Применить лимит если указан
            max_categories = self.config.get('limits', {}).get('max_categories')
            if max_categories:
                category_elements = category_elements[:max_categories]
            
            for idx, elem in enumerate(category_elements):
                try:
                    # Получить заголовок категории
                    title_elem = await elem.query_selector(self.config['selectors']['category_title'])
                    if not title_elem:
                        continue
                    
                    title = await title_elem.inner_text()
                    title = title.strip()
                    
                    # Получить ссылку на категорию
                    link_elem = await elem.query_selector(self.config['selectors']['category_link'])
                    url = await link_elem.get_attribute('href') if link_elem else None
                    
                    # Получить описание
                    desc_elem = await elem.query_selector(self.config['selectors']['category_description'])
                    description = await desc_elem.inner_text() if desc_elem else ""
                    
                    # Получить количество постов
                    posts_elem = await elem.query_selector('[data-hook="category-list-item__total-posts"]')
                    posts_count_text = await posts_elem.inner_text() if posts_elem else "0"
                    
                    category = {
                        'id': f"cat_{idx + 1}",
                        'title': title,
                        'url': url if url and url.startswith('http') else f"https://www.fisherydb.com{url}" if url else None,
                        'description': description.strip(),
                        'posts_count': posts_count_text.strip(),
                        'subcategories': []
                    }
                    
                    categories.append(category)
                    self.stats['categories_parsed'] += 1
                    
                    logger.debug(f"  ✓ Категория: {title}")
                    
                except Exception as e:
                    logger.warning(f"Ошибка при парсинге категории {idx}: {e}")
                    continue
            
            logger.info(f"✓ Успешно спарсено категорий: {len(categories)}")
            self.categories = categories
            
            return categories
            
        except Exception as e:
            logger.error(f"✗ Ошибка при парсинге категорий: {e}")
            self.stats['errors_count'] += 1
            raise
    
    async def parse_subcategories(self, category: Dict) -> List[Dict]:
        """
        Парсинг подкатегорий для категории
        
        Args:
            category: Словарь с данными категории
            
        Returns:
            Список подкатегорий
        """
        logger.info(f"Парсинг подкатегорий для: {category['title']}")
        
        try:
            subcategories = []
            
            # Если у категории есть URL, переходим на страницу категории
            if not category.get('url'):
                logger.debug(f"  У категории {category['title']} нет URL, пропускаем")
                return subcategories
            
            # Перейти на страницу категории
            await self.page.goto(category['url'])
            await self.page.wait_for_load_state('networkidle')
            await self.page.wait_for_timeout(2000)
            
            # Найти элементы подкатегорий (они используют те же селекторы что и категории)
            subcat_elements = await self.page.query_selector_all(
                self.config['selectors']['subcategory_item']
            )
            
            logger.debug(f"  Найдено подкатегорий: {len(subcat_elements)}")
            
            for idx, elem in enumerate(subcat_elements):
                try:
                    # Получить заголовок
                    title_elem = await elem.query_selector(self.config['selectors']['subcategory_title'])
                    if not title_elem:
                        continue
                    
                    title = await title_elem.inner_text()
                    title = title.strip()
                    
                    # Получить ссылку
                    link_elem = await elem.query_selector(self.config['selectors']['subcategory_link'])
                    url = await link_elem.get_attribute('href') if link_elem else None
                    
                    # Получить описание
                    desc_elem = await elem.query_selector(self.config['selectors']['category_description'])
                    description = await desc_elem.inner_text() if desc_elem else ""
                    
                    subcategory = {
                        'id': f"{category['id']}_sub_{idx + 1}",
                        'title': title,
                        'url': url if url and url.startswith('http') else f"https://www.fisherydb.com{url}" if url else None,
                        'description': description.strip(),
                        'posts': []
                    }
                    
                    subcategories.append(subcategory)
                    
                    logger.debug(f"    ✓ Подкатегория: {title}")
                    
                except Exception as e:
                    logger.warning(f"Ошибка при парсинге подкатегории {idx}: {e}")
                    continue
            
            self.stats['subcategories_parsed'] += len(subcategories)
            
            return subcategories
            
        except Exception as e:
            logger.error(f"✗ Ошибка при парсинге подкатегорий {category['title']}: {e}")
            self.stats['errors_count'] += 1
            return []
    
    async def parse_posts(self, subcategory: Dict) -> List[Dict]:
        """
        Парсинг постов в подкатегории
        
        Args:
            subcategory: Словарь с данными подкатегории
            
        Returns:
            Список постов
        """
        logger.info(f"Парсинг постов в: {subcategory['title']}")
        
        try:
            posts = []
            
            # Если у подкатегории есть URL, переходим на её страницу
            if not subcategory.get('url'):
                logger.debug(f"  У подкатегории {subcategory['title']} нет URL, пропускаем")
                return posts
            
            # Перейти на страницу подкатегории
            await self.page.goto(subcategory['url'])
            await self.page.wait_for_load_state('networkidle')
            await self.page.wait_for_timeout(2000)
            
            # Найти элементы постов
            post_elements = await self.page.query_selector_all(
                self.config['selectors']['post_item']
            )
            
            logger.debug(f"  Найдено постов на текущей странице: {len(post_elements)}")
            
            # Попытаться загрузить больше постов если есть пагинация
            # WIX форум может использовать "Load More" или бесконечную прокрутку
            try:
                # Попробовать найти кнопку "Load More" или "Show More"
                load_more_button = await self.page.query_selector('button:has-text("Load More"), button:has-text("Show More")')
                
                attempts = 0
                max_attempts = 10  # Максимум 10 попыток загрузки
                
                while load_more_button and attempts < max_attempts:
                    await load_more_button.click()
                    await self.page.wait_for_timeout(2000)
                    
                    # Обновить список постов
                    new_post_elements = await self.page.query_selector_all(
                        self.config['selectors']['post_item']
                    )
                    
                    if len(new_post_elements) == len(post_elements):
                        # Больше нет новых постов
                        break
                    
                    post_elements = new_post_elements
                    load_more_button = await self.page.query_selector('button:has-text("Load More"), button:has-text("Show More")')
                    attempts += 1
                    
                    logger.debug(f"  Загружено постов: {len(post_elements)} (попытка {attempts})")
                
            except Exception as e:
                logger.debug(f"Нет пагинации или ошибка загрузки: {e}")
            
            # Применить лимит если указан
            max_posts = self.config.get('limits', {}).get('max_posts_per_category')
            if max_posts:
                post_elements = post_elements[:max_posts]
                logger.debug(f"  Применен лимит: {max_posts} постов")
            
            for idx, elem in enumerate(post_elements):
                try:
                    # Получить заголовок поста
                    title_elem = await elem.query_selector(self.config['selectors']['post_title'])
                    if not title_elem:
                        continue
                    
                    title_text = await title_elem.inner_text()
                    
                    # Получить ссылку на пост
                    link_elem = await title_elem.query_selector('a')
                    url = await link_elem.get_attribute('href') if link_elem else None
                    
                    # Получить автора
                    author_elem = await elem.query_selector(self.config['selectors']['post_author'])
                    author = await author_elem.inner_text() if author_elem else "Unknown"
                    
                    # Получить дату
                    date_elem = await elem.query_selector(self.config['selectors']['post_date'])
                    created_at = await date_elem.inner_text() if date_elem else ""
                    
                    # Получить описание
                    desc_elem = await elem.query_selector(self.config['selectors']['post_description'])
                    description = await desc_elem.inner_text() if desc_elem else ""
                    
                    post = {
                        'id': f"{subcategory['id']}_post_{idx + 1}",
                        'title': title_text.strip(),
                        'url': url if url and url.startswith('http') else f"https://www.fisherydb.com{url}" if url else None,
                        'author': author.strip(),
                        'created_at': created_at.strip(),
                        'description': description.strip(),
                        'content': '',  # Будет заполнено при детальном парсинге
                        'attachments': [],
                        'comments': []
                    }
                    
                    posts.append(post)
                    
                    logger.debug(f"      ✓ Пост: {title_text[:50]}...")
                    
                except Exception as e:
                    logger.warning(f"Ошибка при парсинге поста {idx}: {e}")
                    continue
            
            self.stats['posts_parsed'] += len(posts)
            
            return posts
            
        except Exception as e:
            logger.error(f"✗ Ошибка при парсинге постов в {subcategory['title']}: {e}")
            self.stats['errors_count'] += 1
            return []
    
    async def parse_post_details(self, post: Dict) -> Dict:
        """
        Парсинг деталей конкретного поста
        
        Args:
            post: Словарь с базовой информацией о посте
            
        Returns:
            Обновленный пост с полным контентом, комментариями и вложениями
        """
        if not post.get('url'):
            logger.debug(f"У поста нет URL, пропускаем детальный парсинг")
            return post
        
        logger.debug(f"Детальный парсинг поста: {post['title'][:50]}...")
        
        try:
            await self.page.goto(post['url'])
            await self.page.wait_for_load_state('networkidle')
            await self.page.wait_for_timeout(2000)
            
            # Получить полный контент поста
            content_elem = await self.page.query_selector(self.config['selectors']['post_full_content'])
            if content_elem:
                content_html = await content_elem.inner_html()
                post['content'] = content_html
            
            # Парсинг вложений
            attachment_links = await self.page.query_selector_all(
                self.config['selectors']['attachment_link']
            )
            
            for link in attachment_links:
                try:
                    href = await link.get_attribute('href')
                    filename = await link.inner_text()
                    
                    if href:
                        post['attachments'].append({
                            'filename': filename.strip(),
                            'url': href,
                            'downloaded': False,
                            'local_path': None
                        })
                except Exception as e:
                    logger.debug(f"Ошибка при парсинге вложения: {e}")
            
            # Парсинг комментариев
            max_comments = self.config.get('limits', {}).get('max_comments_per_post')
            
            comment_elements = await self.page.query_selector_all(
                self.config['selectors']['comment_item']
            )
            
            if max_comments:
                comment_elements = comment_elements[:max_comments]
            
            for idx, comment_elem in enumerate(comment_elements):
                try:
                    # Автор комментария
                    author_elem = await comment_elem.query_selector(self.config['selectors']['comment_author'])
                    author = await author_elem.inner_text() if author_elem else "Unknown"
                    
                    # Дата комментария
                    date_elem = await comment_elem.query_selector(self.config['selectors']['comment_date'])
                    created_at = await date_elem.inner_text() if date_elem else ""
                    
                    # Контент комментария
                    content_elem = await comment_elem.query_selector(self.config['selectors']['comment_content'])
                    content = await content_elem.inner_html() if content_elem else ""
                    
                    post['comments'].append({
                        'id': f"{post['id']}_comment_{idx + 1}",
                        'author': author.strip(),
                        'created_at': created_at.strip(),
                        'content': content
                    })
                    
                    self.stats['comments_parsed'] += 1
                    
                except Exception as e:
                    logger.debug(f"Ошибка при парсинге комментария {idx}: {e}")
            
            logger.debug(f"  ✓ Вложений: {len(post['attachments'])}, комментариев: {len(post['comments'])}")
            
        except Exception as e:
            logger.warning(f"Ошибка при детальном парсинге поста: {e}")
            self.stats['errors_count'] += 1
        
        return post
    
    
    async def run_full_parse(self):
        """Полный парсинг форума"""
        logger.info("=" * 80)
        logger.info("🚀 НАЧАЛО ПОЛНОГО ПАРСИНГА ФОРУМА")
        logger.info("=" * 80)
        
        start_time = datetime.now()
        
        try:
            # Инициализировать загрузчик вложений
            self.downloader = AttachmentDownloader(self.config)
            await self.downloader.__aenter__()
            
            await self.initialize_browser()
            await self.login()
            
            # Парсинг категорий
            categories = await self.parse_categories()
            
            # Парсинг каждой категории
            logger.info(f"\n📂 Обработка {len(categories)} категорий...")
            
            for category in tqdm(categories, desc="Категории", unit="cat"):
                # Парсинг подкатегорий
                subcategories = await self.parse_subcategories(category)
                category['subcategories'] = subcategories
                
                # Парсинг постов в каждой подкатегории
                if subcategories:
                    logger.info(f"\n  📁 Обработка подкатегорий в '{category['title']}'...")
                    
                    for subcategory in tqdm(subcategories, desc=f"  Подкатегории", leave=False):
                        posts = await self.parse_posts(subcategory)
                        subcategory['posts'] = posts
                        
                        # Обработка постов - детальный парсинг
                        if posts:
                            for post in tqdm(posts, desc=f"    Детали постов", leave=False):
                                # Парсинг деталей поста (комментарии, вложения)
                                await self.parse_post_details(post)
                                
                                # Скачать вложения если есть
                                if post.get('attachments') and self.downloader:
                                    updated_attachments = await self.downloader.download_attachments(
                                        post['attachments'],
                                        post_id=post['id'],
                                        show_progress=False
                                    )
                                    post['attachments'] = updated_attachments
                                    self.stats['files_downloaded'] += len([a for a in updated_attachments if a.get('downloaded')])
                                
                                # Задержка между постами
                                await asyncio.sleep(1)
                        
                        # Задержка между запросами
                        await asyncio.sleep(
                            self.config['parsing']['delay_between_requests']
                        )
            
            # Сохранение результатов
            self.save_results()
            
            # Подсчет времени выполнения
            end_time = datetime.now()
            duration = end_time - start_time
            
            # Вывод статистики
            self._print_statistics(duration)
            
            logger.info("=" * 80)
            logger.info("✅ ПАРСИНГ ЗАВЕРШЕН УСПЕШНО")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.exception(f"❌ Критическая ошибка при парсинге: {e}")
            self.stats['errors_count'] += 1
            raise
            
        finally:
            # Закрыть загрузчик вложений
            if self.downloader:
                await self.downloader.__aexit__(None, None, None)
            
            # Закрыть браузер
            if self.browser:
                await self.browser.close()
    
    def _print_statistics(self, duration):
        """Вывод статистики выполнения"""
        logger.info("\n" + "=" * 80)
        logger.info("📊 СТАТИСТИКА ПАРСИНГА")
        logger.info("=" * 80)
        logger.info(f"✓ Обработано категорий:     {self.stats['categories_parsed']}")
        logger.info(f"✓ Обработано подкатегорий:  {self.stats['subcategories_parsed']}")
        logger.info(f"✓ Обработано постов:        {self.stats['posts_parsed']}")
        logger.info(f"✓ Обработано комментариев:  {self.stats['comments_parsed']}")
        logger.info(f"✓ Скачано файлов:           {self.stats['files_downloaded']}")
        logger.info(f"⚠ Ошибок:                   {self.stats['errors_count']}")
        logger.info(f"⏱ Время выполнения:         {duration}")
        logger.info("=" * 80 + "\n")
    
    def save_results(self):
        """Сохранение результатов в JSON"""
        output_dir = Path(self.config['export']['output_dir'])
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Сохранить структуру форума
        structure_file = output_dir / f"forum_structure_{timestamp}.json"
        
        data = {
            'export_date': datetime.now().isoformat(),
            'forum_url': self.config['forum_url'],
            'categories': self.categories,
            'statistics': self.stats,
            'summary': {
                'total_categories': len(self.categories),
                'total_subcategories': sum(
                    len(cat.get('subcategories', [])) 
                    for cat in self.categories
                ),
                'total_posts': sum(
                    len(subcat.get('posts', []))
                    for cat in self.categories
                    for subcat in cat.get('subcategories', [])
                )
            }
        }
        
        with open(structure_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n💾 Результаты сохранены в: {structure_file}")


async def main():
    """Главная функция"""
    parser = WixForumParser()
    await parser.run_full_parse()


if __name__ == "__main__":
    asyncio.run(main())

