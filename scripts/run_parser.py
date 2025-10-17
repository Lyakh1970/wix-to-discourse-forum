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
    print("=" * 80)
    print("ПАРСЕР WIX ФОРУМА FISHERY GROUP")
    print("=" * 80)
    print()
    
    # Проверить наличие конфигурации
    config_file = Path("config/wix_config.yaml")
    
    if not config_file.exists():
        print("❌ Ошибка: Файл конфигурации не найден!")
        print(f"   Ожидается: {config_file.absolute()}")
        print()
        print("📝 Создайте файл конфигурации на основе примера:")
        print("   cp config/wix_config.yaml.example config/wix_config.yaml")
        print()
        return
    
    # Создать парсер
    parser = WixForumParser(str(config_file))
    
    # Запустить парсинг
    try:
        await parser.run_full_parse()
        
        print()
        print("✅ Парсинг завершен успешно!")
        print()
        print("📁 Результаты сохранены в:")
        print(f"   {Path('data/exported').absolute()}")
        print()
        
    except KeyboardInterrupt:
        print()
        print("⚠️  Парсинг прерван пользователем")
        print()
        
    except Exception as e:
        print()
        print(f"❌ Ошибка при парсинге: {e}")
        print()
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

