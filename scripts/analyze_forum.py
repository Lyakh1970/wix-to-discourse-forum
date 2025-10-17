#!/usr/bin/env python3
"""
Скрипт для предварительного анализа структуры WIX форума
Используется для разведки перед полным парсингом
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright
import yaml


async def analyze_forum():
    """Анализ структуры форума"""
    
    print("=" * 80)
    print("АНАЛИЗ СТРУКТУРЫ WIX ФОРУМА")
    print("=" * 80)
    print()
    
    # Загрузить конфигурацию
    config_file = Path("config/wix_config.yaml")
    
    if not config_file.exists():
        print("❌ Файл конфигурации не найден!")
        print(f"   Создайте: {config_file}")
        return
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    forum_url = config['forum_url']
    
    print(f"🔍 Анализируем: {forum_url}")
    print()
    
    async with async_playwright() as p:
        # Запустить браузер
        browser = await p.chromium.launch(headless=False)  # Видимый режим для анализа
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Перейти на главную страницу форума
            print("📄 Загрузка главной страницы...")
            await page.goto(forum_url, wait_until='networkidle')
            print("✅ Страница загружена")
            print()
            
            # Получить заголовок страницы
            title = await page.title()
            print(f"📌 Заголовок страницы: {title}")
            print()
            
            # Анализ категорий
            print("🔎 Поиск категорий...")
            print()
            
            # Попробовать найти различные селекторы
            selectors_to_try = [
                "a[href*='category']",
                "div[class*='category']",
                "div[class*='subcategory']",
                "[data-hook*='category']",
                ".category-item",
                ".subcategory-item",
            ]
            
            for selector in selectors_to_try:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        print(f"  ✓ Найдено {len(elements)} элементов для: {selector}")
                        
                        # Показать первые 3 элемента
                        for i, elem in enumerate(elements[:3]):
                            try:
                                text = await elem.inner_text()
                                text = text.strip()[:100]  # Первые 100 символов
                                print(f"    [{i+1}] {text}")
                            except:
                                pass
                        print()
                except Exception as e:
                    continue
            
            # Анализ ссылок на подразделы
            print("🔗 Анализ ссылок...")
            print()
            
            all_links = await page.query_selector_all('a[href]')
            
            forum_links = []
            for link in all_links:
                href = await link.get_attribute('href')
                if href and 'forum' in href.lower():
                    text = await link.inner_text()
                    forum_links.append({
                        'text': text.strip()[:80],
                        'href': href
                    })
            
            # Убрать дубликаты
            unique_links = {link['href']: link for link in forum_links}
            
            print(f"  📊 Найдено уникальных ссылок форума: {len(unique_links)}")
            print()
            
            # Показать несколько примеров
            print("  Примеры ссылок:")
            for i, (href, link) in enumerate(list(unique_links.items())[:10]):
                print(f"    [{i+1}] {link['text']}")
                print(f"        → {href[:100]}")
            print()
            
            # Анализ элементов с классом PaFuZ (вложения)
            print("📎 Поиск вложений (класс PaFuZ)...")
            print()
            
            attachments = await page.query_selector_all('a.PaFuZ')
            if attachments:
                print(f"  ✓ Найдено вложений: {len(attachments)}")
                
                for i, att in enumerate(attachments[:5]):
                    href = await att.get_attribute('href')
                    text = await att.inner_text()
                    print(f"    [{i+1}] {text}")
                    print(f"        → {href}")
                print()
            else:
                print("  ℹ️  Вложения не найдены на главной странице")
                print("     (они могут быть внутри отдельных постов)")
                print()
            
            # HTML структура
            print("🏗️  Анализ HTML структуры...")
            print()
            
            html_content = await page.content()
            
            # Статистика
            print(f"  📏 Размер HTML: {len(html_content):,} символов")
            print(f"  🔢 Количество всех ссылок: {len(all_links)}")
            
            # Поиск data-hook атрибутов (WIX часто их использует)
            import re
            data_hooks = re.findall(r'data-hook=["\']([^"\']+)["\']', html_content)
            unique_hooks = set(data_hooks)
            
            if unique_hooks:
                print(f"  🎣 Найдено data-hook атрибутов: {len(unique_hooks)}")
                print("     Примеры:")
                for hook in list(unique_hooks)[:10]:
                    print(f"       - {hook}")
            print()
            
            # Сохранить HTML для детального анализа
            output_file = Path("data/exported/forum_page_sample.html")
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(html_content, encoding='utf-8')
            
            print(f"💾 HTML страницы сохранен в: {output_file}")
            print()
            
            # Рекомендации
            print("=" * 80)
            print("📝 РЕКОМЕНДАЦИИ")
            print("=" * 80)
            print()
            print("1. Изучите сохраненный HTML файл для определения правильных селекторов")
            print("2. Обновите config/wix_config.yaml с найденными селекторами")
            print("3. Проверьте, требуется ли авторизация для доступа к контенту")
            print("4. Определите структуру URL для навигации по категориям")
            print()
            
            # Пауза перед закрытием
            print("Нажмите Enter для закрытия браузера...")
            input()
            
        except Exception as e:
            print(f"❌ Ошибка при анализе: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            await browser.close()
    
    print()
    print("✅ Анализ завершен")
    print()


if __name__ == "__main__":
    asyncio.run(analyze_forum())

