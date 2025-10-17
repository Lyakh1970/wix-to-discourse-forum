#!/usr/bin/env python3
"""
Скрипт для запуска импортера в Discourse
"""

import asyncio
import sys
from pathlib import Path

# Добавить текущую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from importer.discourse_importer import DiscourseImporter


async def main():
    """Главная функция"""
    print("=" * 80)
    print("ИМПОРТЕР В DISCOURSE ФОРУМ")
    print("=" * 80)
    print()
    
    # Проверить аргументы
    if len(sys.argv) < 2:
        print("❌ Ошибка: Не указан файл с данными для импорта")
        print()
        print("📝 Использование:")
        print(f"   python {Path(__file__).name} <путь_к_json_файлу>")
        print()
        print("Пример:")
        print(f"   python {Path(__file__).name} data/exported/forum_structure_20251017_120000.json")
        print()
        return
    
    json_file = Path(sys.argv[1])
    
    # Проверить существование файла
    if not json_file.exists():
        print(f"❌ Ошибка: Файл не найден: {json_file}")
        print()
        return
    
    # Проверить конфигурацию
    config_file = Path("config/discourse_config.yaml")
    
    if not config_file.exists():
        print("❌ Ошибка: Файл конфигурации Discourse не найден!")
        print(f"   Ожидается: {config_file.absolute()}")
        print()
        print("📝 Создайте файл конфигурации на основе примера:")
        print("   cp config/discourse_config.yaml.example config/discourse_config.yaml")
        print()
        return
    
    print(f"📥 Импорт данных из: {json_file}")
    print()
    
    # Подтверждение
    response = input("⚠️  Вы уверены, что хотите начать импорт? (yes/no): ")
    
    if response.lower() not in ['yes', 'y', 'да', 'д']:
        print("Импорт отменен.")
        return
    
    print()
    
    # Создать импортер
    try:
        async with DiscourseImporter(str(config_file)) as importer:
            await importer.import_from_json(str(json_file))
        
        print()
        print("✅ Импорт завершен!")
        print()
        print("📊 Статистика:")
        print(f"   Категорий создано: {importer.stats['categories_created']}")
        print(f"   Топиков создано: {importer.stats['topics_created']}")
        print(f"   Постов создано: {importer.stats['posts_created']}")
        print(f"   Вложений загружено: {importer.stats['attachments_uploaded']}")
        print(f"   Ошибок: {importer.stats['errors']}")
        print()
        
    except KeyboardInterrupt:
        print()
        print("⚠️  Импорт прерван пользователем")
        print()
        
    except Exception as e:
        print()
        print(f"❌ Ошибка при импорте: {e}")
        print()
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

