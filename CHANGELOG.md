# История изменений

## [Unreleased] - 2025-10-17

### Добавлено ✨

#### Улучшенное логирование
- Стандартное логирование Python вместо loguru
- Запись в файл `logs/parser.log` с кодировкой UTF-8
- Вывод в консоль с timestamp и уровнем логирования
- Структурированный формат: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

#### Прогресс-бары 📊
- Визуальные прогресс-бары с использованием `tqdm`
- Отдельные прогресс-бары для:
  - Категорий
  - Подкатегорий
  - Постов
  - Комментариев

#### Статистика выполнения 📈
- Подсчет обработанных элементов:
  - `categories_parsed` - количество категорий
  - `subcategories_parsed` - количество подкатегорий
  - `posts_parsed` - количество постов
  - `comments_parsed` - количество комментариев
  - `files_downloaded` - количество скачанных файлов
  - `errors_count` - количество ошибок

- Вывод статистики:
  - В процессе выполнения (логи)
  - После завершения (консоль)
  - В JSON файле результатов
  - При прерывании пользователем

#### Улучшенная обработка ошибок
- Try-except блоки во всех основных функциях
- Логирование ошибок с emoji индикаторами (✓/✗)
- Продолжение работы при ошибках в отдельных элементах
- Подсчет ошибок в статистике

#### Измерение времени выполнения ⏱
- Автоматический расчет времени парсинга
- Вывод в статистике

### Улучшено 🔧

#### `scripts/parser/wix_parser.py`
- Добавлен словарь `self.stats` для статистики
- Метод `_print_statistics()` для вывода итоговой статистики
- Метод `run_full_parse()` с прогресс-барами и измерением времени
- Все методы парсинга обернуты в try-except
- Улучшенное логирование с emoji (🚀, ✓, ✗, 📊, и т.д.)

#### `scripts/parser/attachment_downloader.py`
- Замена loguru на стандартный logging
- Совместимость с новой системой логирования

#### `scripts/run_parser.py`
- Красивый вывод статистики после завершения
- Вывод частичной статистики при прерывании
- Улучшенные сообщения об ошибках
- Указание пути к логам

### Изменено

#### Формат JSON результатов
Добавлена секция `statistics`:
```json
{
  "export_date": "...",
  "forum_url": "...",
  "categories": [...],
  "statistics": {
    "categories_parsed": 0,
    "subcategories_parsed": 0,
    "posts_parsed": 0,
    "comments_parsed": 0,
    "files_downloaded": 0,
    "errors_count": 0
  },
  "summary": {
    "total_categories": 0,
    "total_subcategories": 0,
    "total_posts": 0
  }
}
```

## [1.0.0] - 2025-10-17

### Добавлено ✨

- Начальная версия проекта
- Документация:
  - README.md
  - INSTALL.md
  - QUICK_START.md
  - CHEATSHEET.md
  - PROJECT_SUMMARY.md
  - docs/PROJECT_ROADMAP.md
  - docs/VPS_SETUP.md
  - docs/NEXT_STEPS.md

- Парсер WIX форума:
  - `scripts/parser/wix_parser.py` - основной парсер
  - `scripts/parser/attachment_downloader.py` - загрузчик файлов
  - `scripts/parser/utils.py` - утилиты

- Импортер Discourse:
  - `scripts/importer/discourse_importer.py`

- Скрипты запуска:
  - `scripts/run_parser.py`
  - `scripts/run_importer.py`
  - `scripts/analyze_forum.py`

- Конфигурация:
  - `config/wix_config.yaml.example`
  - `config/discourse_config.yaml.example`

- Инфраструктура:
  - `requirements.txt`
  - `.gitignore`

---

## Формат

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/),
и проект придерживается [Semantic Versioning](https://semver.org/lang/ru/).

## Типы изменений

- **Добавлено** - новые функции
- **Изменено** - изменения в существующей функциональности
- **Устарело** - функции, которые скоро будут удалены
- **Удалено** - удаленные функции
- **Исправлено** - исправление багов
- **Безопасность** - в случае уязвимостей

