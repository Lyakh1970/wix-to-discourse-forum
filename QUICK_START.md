# Быстрый старт

Краткая инструкция для начала работы с проектом миграции форума.

## ⚡ Быстрая установка (5 минут)

### 1. Подготовка окружения

```bash
# Создать виртуальное окружение
python -m venv venv

# Активировать (Windows)
.\venv\Scripts\Activate.ps1

# Активировать (Linux/macOS)
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt
playwright install chromium
```

### 2. Настройка конфигурации

```bash
# Windows
Copy-Item config\wix_config.yaml.example config\wix_config.yaml

# Linux/macOS
cp config/wix_config.yaml.example config/wix_config.yaml
```

Отредактируйте `config/wix_config.yaml`:
```yaml
auth:
  username: "ваш_логин"
  password: "ваш_пароль"
```

## 🔍 Фаза 1: Анализ форума (10 минут)

Перед полным парсингом проведите разведку:

```bash
python scripts/analyze_forum.py
```

Этот скрипт:
- ✅ Откроет форум в браузере
- ✅ Проанализирует HTML структуру
- ✅ Найдет селекторы для категорий и постов
- ✅ Сохранит HTML страницы для изучения

**Результат:** `data/exported/forum_page_sample.html`

## 📥 Фаза 2: Парсинг форума (1-3 часа)

> ⚠️ Перед запуском убедитесь, что обновили селекторы в `config/wix_config.yaml` на основе анализа!

```bash
python scripts/run_parser.py
```

Этот скрипт:
- ✅ Соберет все категории и подкатегории
- ✅ Спарсит все 4,945 постов
- ✅ Скачает все вложения
- ✅ Сохранит данные в JSON

**Результат:** 
- `data/exported/forum_structure_YYYYMMDD_HHMMSS.json`
- `data/attachments/` - папка с файлами

## 🗄️ Фаза 3: Настройка Discourse (2-3 часа)

### 3.1 Создать VPS

1. Зарегистрируйтесь на [Digital Ocean](https://www.digitalocean.com/)
2. Создайте Droplet:
   - Ubuntu 22.04 LTS
   - 4 GB RAM / 2 vCPU
   - $24/месяц

Подробнее: [docs/VPS_SETUP.md](docs/VPS_SETUP.md)

### 3.2 Установить Discourse

```bash
# На сервере
git clone https://github.com/discourse/discourse_docker.git /var/discourse
cd /var/discourse
./discourse-setup
```

### 3.3 Получить API ключ

1. Войдите как администратор
2. Admin → API → New API Key
3. Скопируйте ключ

### 3.4 Настроить конфигурацию импортера

```bash
# На вашем компьютере
cp config/discourse_config.yaml.example config/discourse_config.yaml
```

Отредактируйте `config/discourse_config.yaml`:
```yaml
discourse_url: "https://forum.fisherygroup.com"
api:
  key: "ваш_api_ключ"
  username: "admin"
```

## 📤 Фаза 4: Импорт данных (2-4 часа)

```bash
python scripts/run_importer.py data/exported/forum_structure_YYYYMMDD_HHMMSS.json
```

Этот скрипт:
- ✅ Создаст все категории
- ✅ Импортирует все посты
- ✅ Загрузит все вложения
- ✅ Сохранит метаданные (даты, авторы)

## ✅ Фаза 5: Проверка (30 минут)

1. Откройте ваш Discourse форум
2. Проверьте:
   - [ ] Все категории созданы
   - [ ] Посты на месте
   - [ ] Вложения открываются
   - [ ] Комментарии импортированы
   - [ ] Поиск работает

3. Если есть проблемы:
   - Проверьте логи: `logs/discourse_importer.log`
   - Посмотрите статистику: `data/import_stats.json`

## 📊 Ожидаемое время выполнения

| Фаза | Время |
|------|-------|
| Установка | 5 мин |
| Анализ форума | 10 мин |
| Парсинг (4,945 постов) | 1-3 часа |
| Настройка Discourse | 2-3 часа |
| Импорт данных | 2-4 часа |
| Проверка | 30 мин |
| **ИТОГО** | **6-11 часов** |

## 🆘 Частые проблемы

### Проблема: "playwright: command not found"

**Решение:**
```bash
playwright install
```

### Проблема: Парсер не находит элементы

**Решение:**
1. Запустите `python scripts/analyze_forum.py`
2. Обновите селекторы в `config/wix_config.yaml`
3. Попробуйте снова

### Проблема: API ошибка 403 при импорте

**Решение:**
1. Проверьте API ключ в `config/discourse_config.yaml`
2. Убедитесь, что ключ имеет права "All Users"
3. Проверьте URL Discourse (должен быть https://)

### Проблема: Вложения не загружаются

**Решение:**
1. Проверьте настройки загрузки в Discourse:
   - Admin → Settings → Files
   - Увеличьте `max attachment size kb`
2. Проверьте разрешенные типы файлов:
   - `authorized extensions`

## 🔗 Полезные команды

### Парсинг

```bash
# Анализ структуры
python scripts/analyze_forum.py

# Полный парсинг
python scripts/run_parser.py

# Парсинг с лимитами (тестирование)
# Отредактируйте config/wix_config.yaml:
limits:
  max_categories: 2
  max_posts_per_category: 10
```

### Discourse

```bash
# На сервере
cd /var/discourse

# Перезапуск
./launcher restart app

# Логи
./launcher logs app

# Бэкап
./launcher enter app
discourse backup
```

## 📚 Дополнительная документация

- **Полная дорожная карта:** [docs/PROJECT_ROADMAP.md](docs/PROJECT_ROADMAP.md)
- **Детальная установка:** [INSTALL.md](INSTALL.md)
- **Настройка VPS:** [docs/VPS_SETUP.md](docs/VPS_SETUP.md)

## 🎯 Следующие шаги

После успешной миграции:

1. [ ] Настроить редиректы со старого форума
2. [ ] Оповестить пользователей о переезде
3. [ ] Настроить автоматические бэкапы
4. [ ] Настроить мониторинг сервера
5. [ ] Обучить модераторов работе с Discourse

---

**Готовы начать?** → [INSTALL.md](INSTALL.md)

