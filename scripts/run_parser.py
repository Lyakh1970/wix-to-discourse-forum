#!/usr/bin/env python3
"""
Скрипт для запуска парсера WIX форума
"""

import asyncio
import sys
from pathlib import Path

# Добавить текущую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from parser.wix_parser import WixForumParser


async def main():
    """Главная функция"""
    print("\n" + "=" * 80)
    print("🚀 ПАРСЕР WIX ФОРУМА FISHERY GROUP")
    print("=" * 80)
    print()
    
    # Проверить наличие конфигурации
    config_file = Path("config/wix_config.yaml")
    
    if not config_file.exists():
        print("❌ Ошибка: Файл конфигурации не найден!")
        print(f"   Ожидается: {config_file.absolute()}")
        print()
        print("📝 Создайте файл конфигурации на основе примера:")
        print("   Windows: Copy-Item config\\wix_config.yaml.example config\\wix_config.yaml")
        print("   Linux/Mac: cp config/wix_config.yaml.example config/wix_config.yaml")
        print()
        return
    
    print("✓ Конфигурация найдена")
    print(f"✓ Логи будут записаны в: logs/parser.log")
    print()
    
    # Создать парсер
    parser = WixForumParser(str(config_file))
    
    # Запустить парсинг
    try:
        await parser.run_full_parse()
        
        print()
        print("=" * 80)
        print("✅ ПАРСИНГ ЗАВЕРШЕН УСПЕШНО!")
        print("=" * 80)
        print()
        print("📁 Результаты сохранены в:")
        print(f"   {Path('data/exported').absolute()}")
        print()
        print("📊 Итоговая статистика:")
        print(f"   ✓ Категорий:     {parser.stats['categories_parsed']}")
        print(f"   ✓ Подкатегорий:  {parser.stats['subcategories_parsed']}")
        print(f"   ✓ Постов:        {parser.stats['posts_parsed']}")
        print(f"   ✓ Комментариев:  {parser.stats['comments_parsed']}")
        print(f"   ✓ Файлов:        {parser.stats['files_downloaded']}")
        if parser.stats['errors_count'] > 0:
            print(f"   ⚠ Ошибок:        {parser.stats['errors_count']}")
        print()
        
    except KeyboardInterrupt:
        print()
        print("=" * 80)
        print("⚠️  ПАРСИНГ ПРЕРВАН ПОЛЬЗОВАТЕЛЕМ")
        print("=" * 80)
        print()
        if hasattr(parser, 'stats'):
            print("📊 Частичная статистика:")
            print(f"   Обработано категорий:    {parser.stats['categories_parsed']}")
            print(f"   Обработано подкатегорий: {parser.stats['subcategories_parsed']}")
            print(f"   Обработано постов:       {parser.stats['posts_parsed']}")
            print()
        
    except Exception as e:
        print()
        print("=" * 80)
        print("❌ КРИТИЧЕСКАЯ ОШИБКА")
        print("=" * 80)
        print(f"\nОшибка: {e}")
        print()
        print("📝 Подробности в логе: logs/parser.log")
        print()
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

