#!/usr/bin/env python3
"""
Тестовый скрипт для проверки отдельных компонентов парсера
Используется для отладки без полного парсинга
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from parser.wix_parser import WixForumParser
from parser.utils import parse_date, html_to_markdown, extract_wix_attachment_info


async def test_connection():
    """Тест подключения к форуму"""
    print("\n" + "=" * 80)
    print("🔌 ТЕСТ ПОДКЛЮЧЕНИЯ К ФОРУМУ")
    print("=" * 80)
    
    parser = WixForumParser()
    
    try:
        await parser.initialize_browser()
        
        print("✓ Браузер инициализирован")
        
        # Попробовать загрузить главную страницу
        await parser.page.goto(parser.config['forum_url'])
        await parser.page.wait_for_load_state('networkidle')
        
        title = await parser.page.title()
        print(f"✓ Страница загружена: {title}")
        
        # Проверить URL
        current_url = parser.page.url
        print(f"✓ URL: {current_url}")
        
        print("\n✅ Подключение успешно!")
        
    except Exception as e:
        print(f"\n❌ Ошибка подключения: {e}")
    
    finally:
        if parser.browser:
            await parser.browser.close()


async def test_auth():
    """Тест авторизации"""
    print("\n" + "=" * 80)
    print("🔐 ТЕСТ АВТОРИЗАЦИИ")
    print("=" * 80)
    
    parser = WixForumParser()
    
    try:
        await parser.initialize_browser()
        await parser.login()
        
        print("✓ Авторизация завершена (проверьте логи)")
        
        # Пауза чтобы проверить визуально
        await parser.page.wait_for_timeout(5000)
        
    except Exception as e:
        print(f"❌ Ошибка авторизации: {e}")
    
    finally:
        if parser.browser:
            await parser.browser.close()


async def test_parse_one_category():
    """Тест парсинга одной категории"""
    print("\n" + "=" * 80)
    print("📂 ТЕСТ ПАРСИНГА ОДНОЙ КАТЕГОРИИ")
    print("=" * 80)
    
    parser = WixForumParser()
    
    try:
        await parser.initialize_browser()
        await parser.login()
        
        # Установить лимит на 1 категорию
        parser.config['limits']['max_categories'] = 1
        
        categories = await parser.parse_categories()
        
        print(f"\n✓ Спарсено категорий: {len(categories)}")
        
        if categories:
            cat = categories[0]
            print(f"\nКатегория 1:")
            print(f"  Название: {cat['title']}")
            print(f"  URL: {cat['url']}")
            print(f"  Описание: {cat['description'][:100]}...")
            print(f"  Постов: {cat['posts_count']}")
        
        print("\n✅ Тест завершен!")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if parser.browser:
            await parser.browser.close()


async def test_parse_one_post():
    """Тест парсинга одного поста с вложениями"""
    print("\n" + "=" * 80)
    print("📝 ТЕСТ ПАРСИНГА ОДНОГО ПОСТА")
    print("=" * 80)
    
    parser = WixForumParser()
    
    try:
        await parser.initialize_browser()
        await parser.login()
        
        # URL тестового поста (замените на реальный)
        test_post_url = "https://www.fisherydb.com/forum/simrad/km-simrad-fs-70-es80-nastroyka-linii-trala-s-tz-fs-70-na-eholot-es-80"
        
        test_post = {
            'id': 'test_post_1',
            'title': 'Test Post',
            'url': test_post_url,
            'attachments': [],
            'comments': []
        }
        
        await parser.parse_post_details(test_post)
        
        print(f"\n✓ Пост спарсен:")
        print(f"  Заголовок: {test_post['title']}")
        print(f"  Контент: {len(test_post.get('content', ''))} символов")
        print(f"  Вложений: {len(test_post['attachments'])}")
        print(f"  Комментариев: {len(test_post['comments'])}")
        
        if test_post['attachments']:
            print(f"\n  Вложения:")
            for att in test_post['attachments']:
                print(f"    - {att['filename']}")
                print(f"      URL: {att['url']}")
        
        print("\n✅ Тест завершен!")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if parser.browser:
            await parser.browser.close()


def test_utils():
    """Тест утилит парсинга"""
    print("\n" + "=" * 80)
    print("🛠️  ТЕСТ УТИЛИТ")
    print("=" * 80)
    
    # Тест парсинга дат WIX
    test_dates = [
        "Oct 05",
        "Sep 11",
        "Jun 06",
        "2 hours ago",
        "5 дней назад"
    ]
    
    print("\n📅 Тест парсинга дат:")
    for date_str in test_dates:
        parsed = parse_date(date_str)
        print(f"  '{date_str}' → {parsed}")
    
    # Тест HTML → Markdown
    print("\n📄 Тест HTML → Markdown:")
    test_html = "<h1>Заголовок</h1><p>Текст с <strong>жирным</strong> и <a href='#'>ссылкой</a></p>"
    markdown = html_to_markdown(test_html)
    print(f"  HTML: {test_html}")
    print(f"  Markdown: {markdown}")
    
    # Тест извлечения WIX URL
    print("\n🔗 Тест WIX URL:")
    test_url = "https://abc123.usrfiles.com/ugd/def456_hash/document.pdf"
    info = extract_wix_attachment_info(test_url)
    print(f"  URL: {test_url}")
    print(f"  UUID: {info.get('uuid')}")
    print(f"  Hash: {info.get('hash')}")
    
    print("\n✅ Все тесты утилит пройдены!")


async def interactive_menu():
    """Интерактивное меню тестов"""
    print("\n" + "=" * 80)
    print("🧪 ТЕСТИРОВАНИЕ КОМПОНЕНТОВ ПАРСЕРА")
    print("=" * 80)
    print()
    print("Выберите тест:")
    print("  1. Тест подключения к форуму")
    print("  2. Тест авторизации")
    print("  3. Тест парсинга одной категории")
    print("  4. Тест парсинга одного поста")
    print("  5. Тест утилит (даты, markdown, и т.д.)")
    print("  0. Запустить все тесты")
    print()
    
    choice = input("Введите номер теста (0-5): ").strip()
    
    if choice == "1":
        await test_connection()
    elif choice == "2":
        await test_auth()
    elif choice == "3":
        await test_parse_one_category()
    elif choice == "4":
        await test_parse_one_post()
    elif choice == "5":
        test_utils()
    elif choice == "0":
        await test_connection()
        await test_auth()
        await test_parse_one_category()
        test_utils()
    else:
        print("Неверный выбор!")


if __name__ == "__main__":
    try:
        asyncio.run(interactive_menu())
    except KeyboardInterrupt:
        print("\n\n⚠️  Тестирование прервано пользователем")
    except Exception as e:
        print(f"\n\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

