# Шпаргалка команд

Быстрый справочник по всем командам проекта.

## 🔧 Установка и настройка

```bash
# Создать виртуальное окружение
python -m venv venv

# Активировать (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Активировать (Linux/macOS)
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Установить браузер Playwright
playwright install chromium

# Создать конфигурацию WIX
Copy-Item config\wix_config.yaml.example config\wix_config.yaml    # Windows
cp config/wix_config.yaml.example config/wix_config.yaml           # Linux/macOS

# Создать конфигурацию Discourse
Copy-Item config\discourse_config.yaml.example config\discourse_config.yaml    # Windows
cp config/discourse_config.yaml.example config/discourse_config.yaml           # Linux/macOS
```

## 🔍 Анализ и парсинг

```bash
# Анализ структуры форума (визуальный режим)
python scripts/analyze_forum.py

# Запуск полного парсинга
python scripts/run_parser.py

# Парсинг с лимитами (для тестирования)
# Отредактировать config/wix_config.yaml:
# limits:
#   max_categories: 2
#   max_posts_per_category: 10
```

## 📤 Импорт в Discourse

```bash
# Импорт из JSON файла
python scripts/run_importer.py data/exported/forum_structure_20251017_120000.json

# Импорт последнего файла (Windows PowerShell)
python scripts/run_importer.py (Get-ChildItem data\exported\forum_structure_*.json | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName

# Импорт последнего файла (Linux/macOS)
python scripts/run_importer.py $(ls -t data/exported/forum_structure_*.json | head -1)
```

## 🗄️ Discourse на сервере

### Основные команды

```bash
# Перейти в директорию Discourse
cd /var/discourse

# Перезапустить Discourse
./launcher restart app

# Остановить Discourse
./launcher stop app

# Запустить Discourse
./launcher start app

# Ребилд (после изменения конфигурации)
./launcher rebuild app

# Посмотреть логи
./launcher logs app

# Следить за логами в реальном времени
./launcher logs app -f

# Войти в контейнер
./launcher enter app

# Выйти из контейнера
exit
```

### Резервное копирование

```bash
# Создать бэкап
cd /var/discourse
./launcher enter app
discourse backup
exit

# Посмотреть бэкапы
ls -lh /var/discourse/shared/standalone/backups/default/

# Скачать бэкап на локальный компьютер
scp root@your_server_ip:/var/discourse/shared/standalone/backups/default/backup-name.tar.gz ./
```

### Обновление Discourse

```bash
cd /var/discourse
git pull
./launcher rebuild app
```

## 🐛 Отладка

### Просмотр логов

```bash
# Логи парсера
cat logs/wix_parser.log

# Логи импортера
cat logs/discourse_importer.log

# Последние 50 строк лога
tail -n 50 logs/wix_parser.log

# Следить за логом в реальном времени
tail -f logs/wix_parser.log
```

### Проверка данных

```bash
# Просмотреть JSON файл (Windows PowerShell)
Get-Content data\exported\forum_structure_*.json | ConvertFrom-Json | ConvertTo-Json -Depth 10

# Просмотреть JSON файл (Linux/macOS)
cat data/exported/forum_structure_*.json | jq '.'

# Подсчитать постов в JSON
# Windows PowerShell
(Get-Content data\exported\forum_structure_*.json | ConvertFrom-Json).posts.Count

# Linux/macOS
jq '.posts | length' data/exported/forum_structure_*.json
```

### Python консоль для отладки

```python
# Запустить интерактивную оболочку Python
python

# Импортировать модули
from scripts.parser import wix_parser
import asyncio
import yaml

# Загрузить конфигурацию
with open('config/wix_config.yaml') as f:
    config = yaml.safe_load(f)

# Создать парсер
parser = wix_parser.WixForumParser()

# И т.д.
```

## 📊 Мониторинг VPS

```bash
# Использование диска
df -h

# Использование памяти
free -h

# Процессы и ресурсы
htop

# Docker контейнеры
docker ps

# Статистика Docker
docker stats

# Проверка портов
netstat -tulpn | grep LISTEN

# Проверка firewall
ufw status

# Проверка DNS
nslookup forum.fisherygroup.com

# Проверка SSL сертификата
echo | openssl s_client -servername forum.fisherygroup.com -connect forum.fisherygroup.com:443 2>/dev/null | openssl x509 -noout -dates
```

## 🔐 Безопасность

```bash
# Обновить систему (Ubuntu)
apt update && apt upgrade -y

# Проверить открытые порты
nmap your_server_ip

# Проверить неудачные попытки входа
grep "Failed password" /var/log/auth.log

# Изменить SSH порт (после изменения в /etc/ssh/sshd_config)
systemctl restart sshd
```

## 🧹 Очистка

```bash
# Удалить скачанные вложения (освободить место)
rm -rf data/attachments/*

# Удалить экспортированные JSON файлы
rm -rf data/exported/*

# Удалить логи
rm -rf logs/*

# Очистить Docker (на VPS)
docker system prune -a

# Очистить старые образы Docker
docker image prune -a
```

## 🔄 Git команды

```bash
# Инициализировать репозиторий
git init

# Добавить все файлы
git add .

# Коммит
git commit -m "Initial commit: forum migration project"

# Добавить remote
git remote add origin https://github.com/your-org/fisherydb-forum.git

# Запушить
git push -u origin main

# Клонировать на другой машине
git clone https://github.com/your-org/fisherydb-forum.git

# Обновить из remote
git pull
```

## 📦 Управление зависимостями

```bash
# Обновить все пакеты
pip install --upgrade pip
pip install --upgrade -r requirements.txt

# Добавить новый пакет
pip install package-name
pip freeze > requirements.txt

# Проверить установленные пакеты
pip list

# Проверить устаревшие пакеты
pip list --outdated
```

## 🧪 Тестирование

```bash
# Запустить тесты (когда будут созданы)
pytest tests/

# Запустить с выводом
pytest tests/ -v

# Запустить конкретный тест
pytest tests/test_parser.py

# Запустить с покрытием кода
pytest --cov=scripts tests/
```

## 💻 Полезные Python команды

```python
# Проверить версию Python
python --version

# Проверить установленные модули
python -c "import playwright; print(playwright.__version__)"

# Запустить простой HTTP сервер для просмотра HTML
python -m http.server 8000
# Открыть http://localhost:8000/data/exported/

# Красиво вывести JSON
python -m json.tool data/exported/forum_structure_*.json

# Проверить синтаксис Python файла
python -m py_compile scripts/parser/wix_parser.py
```

## 🌐 cURL команды для тестирования

```bash
# Проверить доступность форума
curl -I https://www.fisherydb.com/forum/

# Проверить Discourse API
curl -X GET "https://forum.fisherygroup.com/categories.json" \
  -H "Api-Key: your_api_key" \
  -H "Api-Username: admin"

# Создать категорию через API
curl -X POST "https://forum.fisherygroup.com/categories.json" \
  -H "Api-Key: your_api_key" \
  -H "Api-Username: admin" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Category",
    "color": "0088CC",
    "text_color": "FFFFFF"
  }'
```

## 🔍 Поиск и фильтрация

```bash
# Найти все Python файлы
find . -name "*.py"

# Найти в файлах
grep -r "TODO" scripts/

# Найти файлы больше 10MB
find data/attachments -size +10M

# Подсчитать строки кода
find scripts -name "*.py" -exec wc -l {} + | tail -1

# Поиск в логах
grep "ERROR" logs/wix_parser.log
```

## 📈 Статистика проекта

```bash
# Количество Python файлов
find . -name "*.py" | wc -l

# Количество строк в Python файлах
find . -name "*.py" -exec cat {} + | wc -l

# Количество скачанных вложений
find data/attachments -type f | wc -l

# Размер всех вложений
du -sh data/attachments/

# Размер экспортированных JSON
du -sh data/exported/
```

## 🔗 Быстрые ссылки

```bash
# Открыть документацию в браузере (если есть markdown viewer)
# Windows
start README.md

# macOS
open README.md

# Linux
xdg-open README.md
```

---

**💡 Совет:** Добавьте эти команды в свой любимый инструмент для заметок для быстрого доступа!

