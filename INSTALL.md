# Руководство по установке

Это руководство поможет вам настроить окружение для миграции форума.

## 📋 Предварительные требования

### Системные требования
- **Python:** 3.10 или выше
- **Git:** для клонирования репозитория
- **Windows/Linux/macOS:** любая ОС с поддержкой Python

### Для разработки
- Текстовый редактор или IDE (VS Code, PyCharm, и т.д.)
- Базовые знания Python и работы с терминалом

## 🚀 Установка

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd fisherydb-forum
```

Если это новый проект, просто создайте директорию:

```bash
mkdir fisherydb-forum
cd fisherydb-forum
```

### 2. Создание виртуального окружения

#### Windows (PowerShell)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

#### Linux/macOS
```bash
python3 -m venv venv
source venv/bin/activate
```

После активации вы должны увидеть `(venv)` в начале командной строки.

### 3. Установка зависимостей

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Установка браузера для Playwright

Playwright требует установки браузера:

```bash
playwright install chromium
```

Или установить все поддерживаемые браузеры:

```bash
playwright install
```

### 5. Создание конфигурационных файлов

Скопируйте примеры конфигураций и заполните их своими данными:

#### Windows (PowerShell)
```powershell
Copy-Item config\wix_config.yaml.example config\wix_config.yaml
Copy-Item config\discourse_config.yaml.example config\discourse_config.yaml
```

#### Linux/macOS
```bash
cp config/wix_config.yaml.example config/wix_config.yaml
cp config/discourse_config.yaml.example config/discourse_config.yaml
```

### 6. Настройка конфигураций

#### WIX конфигурация (`config/wix_config.yaml`)

Откройте файл и заполните:

```yaml
auth:
  username: "ваш_логин"
  password: "ваш_пароль"
  required: true  # или false, если авторизация не нужна
```

Остальные параметры можно оставить по умолчанию.

#### Discourse конфигурация (`config/discourse_config.yaml`)

Этот файл понадобится позже, на этапе импорта:

```yaml
discourse_url: "https://your-discourse-forum.com"

api:
  key: "ваш_api_ключ"
  username: "admin"
```

API ключ создается в админ-панели Discourse:
1. Перейдите в Admin → API
2. Создайте новый API ключ с правами "All Users"

## ✅ Проверка установки

Проверьте, что все установлено корректно:

```bash
python --version
# Должна быть версия 3.10+

python -c "import playwright; print('Playwright OK')"
# Должно вывести: Playwright OK

python -c "import yaml; print('PyYAML OK')"
# Должно вывести: PyYAML OK
```

## 📁 Структура проекта после установки

```
fisherydb-forum/
├── config/
│   ├── wix_config.yaml              ✅ создан вами
│   ├── discourse_config.yaml        ✅ создан вами
│   ├── wix_config.yaml.example      
│   └── discourse_config.yaml.example
├── data/
│   ├── exported/                     (будет заполнен парсером)
│   └── attachments/                  (будет заполнен парсером)
├── docs/
│   └── PROJECT_ROADMAP.md
├── logs/                             (создастся автоматически)
├── scripts/
│   ├── parser/
│   ├── importer/
│   ├── run_parser.py
│   └── run_importer.py
├── venv/                             ✅ создан вами
├── .gitignore
├── INSTALL.md
├── README.md
└── requirements.txt
```

## 🎯 Следующие шаги

После установки:

1. **Изучите документацию:** [docs/PROJECT_ROADMAP.md](docs/PROJECT_ROADMAP.md)
2. **Запустите тестовый парсинг:** (см. раздел "Использование" в README.md)
3. **Настройте VPS для Discourse** (когда будете готовы к импорту)

## 🆘 Решение проблем

### Ошибка: `playwright: command not found`

После установки Playwright через pip, установите браузеры:

```bash
playwright install
```

### Ошибка: `ModuleNotFoundError: No module named 'yaml'`

Убедитесь, что виртуальное окружение активировано и зависимости установлены:

```bash
pip install -r requirements.txt
```

### Ошибка: `Permission denied` (Linux/macOS)

Убедитесь, что скрипты имеют права на выполнение:

```bash
chmod +x scripts/*.py
```

### Проблемы с кодировкой (Windows)

Если видите кракозябры вместо кириллицы, установите кодировку UTF-8:

```powershell
$env:PYTHONIOENCODING="utf-8"
```

Или добавьте в начало Python скриптов:

```python
# -*- coding: utf-8 -*-
```

## 📚 Дополнительные ресурсы

- [Python Virtual Environments](https://docs.python.org/3/tutorial/venv.html)
- [Playwright Python Documentation](https://playwright.dev/python/)
- [Discourse API Documentation](https://docs.discourse.org/)

---

Если у вас возникли проблемы, не описанные в этом руководстве, обратитесь к команде Fishery Group.

