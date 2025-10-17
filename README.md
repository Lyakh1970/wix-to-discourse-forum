# Fishery DB Forum Migration

Проект миграции форума Fishery Group с платформы WIX на самостоятельный Discourse форум.

## 🎯 Цель проекта

Перенос всего контента форума (10 категорий, 74 подраздела, 4945 постов, ~3000 комментариев) с WIX на независимую платформу Discourse с сохранением структуры и всех вложений.

## 📁 Структура проекта

```
fisherydb-forum/
├── docs/                       # Документация
│   └── PROJECT_ROADMAP.md     # Детальная дорожная карта
├── scripts/                    # Скрипты миграции
│   ├── parser/                # Парсер WIX форума
│   │   ├── wix_parser.py
│   │   ├── structure_mapper.py
│   │   ├── content_scraper.py
│   │   ├── attachment_downloader.py
│   │   └── utils.py
│   └── importer/              # Импортер в Discourse
│       ├── discourse_importer.py
│       ├── user_mapper.py
│       ├── category_creator.py
│       ├── post_creator.py
│       └── attachment_uploader.py
├── data/                       # Экспортированные данные
│   ├── exported/              # JSON с контентом
│   └── attachments/           # Скачанные файлы
├── config/                     # Конфигурационные файлы
│   ├── wix_config.yaml
│   └── discourse_config.yaml
├── tests/                      # Тесты
├── requirements.txt            # Python зависимости
└── README.md                   # Этот файл
```

## 🚀 Быстрый старт

### Предварительные требования

- Python 3.10+
- Git
- Доступ к WIX форуму (логин/пароль)
- VPS для Discourse (на этапе импорта)

### Установка

```bash
# Клонировать репозиторий
git clone <repository-url>
cd fisherydb-forum

# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

# Установить зависимости
pip install -r requirements.txt

# Установить Playwright браузеры
playwright install
```

### Конфигурация

Скопировать примеры конфигов и заполнить своими данными:

```bash
cp config/wix_config.yaml.example config/wix_config.yaml
cp config/discourse_config.yaml.example config/discourse_config.yaml
```

## 📖 Документация

- **Дорожная карта проекта:** [docs/PROJECT_ROADMAP.md](docs/PROJECT_ROADMAP.md)
- **Установка и настройка:** [INSTALL.md](INSTALL.md)
- **Настройка VPS:** [docs/VPS_SETUP.md](docs/VPS_SETUP.md)

## 🛠️ Технологии

- **Парсинг:** Playwright, BeautifulSoup4, Requests
- **Обработка данных:** Pandas, JSON
- **Импорт:** Discourse API, Python Requests
- **Инфраструктура:** Docker, Ubuntu, Nginx
- **Форум:** Discourse

## 🎯 Быстрый старт

**Хотите начать прямо сейчас?** → [QUICK_START.md](QUICK_START.md)

### Базовые команды

```bash
# 1. Установка
pip install -r requirements.txt
playwright install chromium

# 2. Анализ форума
python scripts/analyze_forum.py

# 3. Парсинг
python scripts/run_parser.py

# 4. Импорт в Discourse
python scripts/run_importer.py data/exported/forum_structure_*.json
```

## 📝 Статус проекта

- [x] ✅ Создание дорожной карты и документации
- [x] ✅ Разработка парсера WIX
- [x] ✅ Разработка скачивателя вложений
- [x] ✅ Разработка импортера Discourse
- [x] ✅ Документация по настройке VPS
- [ ] ⏳ Тестирование на реальных данных
- [ ] ⏳ Полная миграция

## 🔄 Процесс миграции

1. **Анализ** → Изучение структуры WIX форума
2. **Парсинг** → Извлечение всех данных (посты, комментарии, файлы)
3. **Настройка** → Подготовка Discourse сервера
4. **Импорт** → Перенос данных в Discourse
5. **Проверка** → Тестирование и верификация
6. **Запуск** → Переключение пользователей на новый форум

## 👥 Команда

- Fishery Group Team

## 📄 Лицензия

Приватный проект Fishery Group

---

**Следующий шаг:** См. [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) для детального плана действий.

