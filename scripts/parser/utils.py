#!/usr/bin/env python3
"""
Вспомогательные утилиты для парсера
"""

import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from markdownify import markdownify as md


def clean_text(text: str) -> str:
    """
    Очистка текста от лишних пробелов и символов
    
    Args:
        text: Исходный текст
        
    Returns:
        Очищенный текст
    """
    if not text:
        return ""
    
    # Убрать множественные пробелы
    text = re.sub(r'\s+', ' ', text)
    
    # Убрать пробелы в начале и конце
    text = text.strip()
    
    return text


def html_to_markdown(html: str) -> str:
    """
    Конвертация HTML в Markdown
    
    Args:
        html: HTML строка
        
    Returns:
        Markdown строка
    """
    if not html:
        return ""
    
    # Конвертировать в Markdown
    markdown = md(
        html,
        heading_style="ATX",  # используйте # для заголовков
        bullets="-",  # используйте - для списков
        strong_em_symbol="**",  # используйте ** для жирного
        strip=['script', 'style']  # удалить script и style теги
    )
    
    # Очистить множественные переносы строк
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)
    
    return markdown.strip()


def extract_text_from_html(html: str) -> str:
    """
    Извлечение чистого текста из HTML
    
    Args:
        html: HTML строка
        
    Returns:
        Текст без тегов
    """
    if not html:
        return ""
    
    soup = BeautifulSoup(html, 'lxml')
    
    # Удалить script и style элементы
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Получить текст
    text = soup.get_text(separator=' ')
    
    return clean_text(text)


def parse_date(date_string: str) -> Optional[datetime]:
    """
    Парсинг даты из различных форматов
    
    Args:
        date_string: Строка с датой
        
    Returns:
        Объект datetime или None
    """
    if not date_string:
        return None
    
    # Список возможных форматов даты
    date_formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
        "%B %d, %Y",  # October 17, 2025
        "%b %d, %Y",  # Oct 17, 2025
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_string.strip(), fmt)
        except ValueError:
            continue
    
    # Если ни один формат не подошел, попробовать относительные даты
    # "5 дней назад", "2 hours ago", etc.
    # TODO: Реализовать парсинг относительных дат
    
    return None


def format_date(dt: datetime, format_string: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Форматирование даты в строку
    
    Args:
        dt: Объект datetime
        format_string: Формат вывода
        
    Returns:
        Отформатированная строка
    """
    if not dt:
        return ""
    
    return dt.strftime(format_string)


def make_absolute_url(base_url: str, relative_url: str) -> str:
    """
    Создание абсолютного URL из относительного
    
    Args:
        base_url: Базовый URL
        relative_url: Относительный URL
        
    Returns:
        Абсолютный URL
    """
    return urljoin(base_url, relative_url)


def is_valid_url(url: str) -> bool:
    """
    Проверка валидности URL
    
    Args:
        url: URL для проверки
        
    Returns:
        True если URL валиден
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def generate_slug(text: str) -> str:
    """
    Генерация URL-friendly slug из текста
    
    Args:
        text: Исходный текст
        
    Returns:
        Slug
    """
    from slugify import slugify
    return slugify(text, max_length=100)


def extract_wix_attachment_info(href: str) -> dict:
    """
    Извлечение информации о вложении из WIX URL
    
    Args:
        href: URL вложения (https://{uuid}.usrfiles.com/ugd/{hash})
        
    Returns:
        Словарь с uuid и hash
    """
    pattern = r'https://([^.]+)\.usrfiles\.com/ugd/([^/]+)'
    match = re.match(pattern, href)
    
    if match:
        return {
            'uuid': match.group(1),
            'hash': match.group(2),
            'full_url': href
        }
    
    return {}


def calculate_reading_time(text: str, words_per_minute: int = 200) -> int:
    """
    Расчет времени чтения текста
    
    Args:
        text: Текст
        words_per_minute: Средняя скорость чтения (слов в минуту)
        
    Returns:
        Время чтения в минутах
    """
    if not text:
        return 0
    
    # Подсчет слов
    words = len(text.split())
    
    # Расчет времени
    minutes = max(1, round(words / words_per_minute))
    
    return minutes


def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """
    Обрезка текста до определенной длины
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина
        suffix: Суффикс для добавления в конец
        
    Returns:
        Обрезанный текст
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)].rsplit(' ', 1)[0] + suffix


def extract_numbers_from_text(text: str) -> list:
    """
    Извлечение чисел из текста
    
    Args:
        text: Текст
        
    Returns:
        Список чисел
    """
    if not text:
        return []
    
    numbers = re.findall(r'\d+', text)
    return [int(n) for n in numbers]


def remove_html_tags(text: str) -> str:
    """
    Удаление HTML тегов из текста (простой способ)
    
    Args:
        text: Текст с HTML
        
    Returns:
        Текст без HTML
    """
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)


class ProgressTracker:
    """Простой трекер прогресса"""
    
    def __init__(self, total: int, description: str = "Progress"):
        self.total = total
        self.current = 0
        self.description = description
        
    def update(self, step: int = 1):
        """Обновить прогресс"""
        self.current += step
        percentage = (self.current / self.total) * 100 if self.total > 0 else 0
        print(f"\r{self.description}: {self.current}/{self.total} ({percentage:.1f}%)", end='')
        
    def finish(self):
        """Завершить прогресс"""
        print()  # Новая строка


if __name__ == "__main__":
    # Тесты
    print("Тест HTML → Markdown:")
    html = "<h1>Заголовок</h1><p>Параграф с <strong>жирным</strong> текстом</p>"
    print(html_to_markdown(html))
    
    print("\nТест очистки текста:")
    print(clean_text("  Много    пробелов   "))
    
    print("\nТест извлечения WIX URL:")
    url = "https://abc123.usrfiles.com/ugd/def456/file.pdf"
    print(extract_wix_attachment_info(url))

