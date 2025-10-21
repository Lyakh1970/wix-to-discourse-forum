# Структура сохранения данных

Подробное описание того, где и как сохраняются данные при парсинге.

## 📁 Корневая структура данных

```
fisherydb-forum/
└── data/
    ├── exported/         ← JSON файлы с результатами
    └── attachments/      ← Скачанные вложения (PDF, DOCX, JPG и т.д.)
```

---

## 1️⃣ JSON файлы (data/exported/)

### Формат имени файла

```
forum_structure_YYYYMMDD_HHMMSS.json
```

**Примеры:**
- `forum_structure_20251017_153045.json` - запуск 17 октября в 15:30:45
- `forum_structure_20251018_092130.json` - запуск 18 октября в 09:21:30

### Содержимое JSON файла

```json
{
  "export_date": "2025-10-17T15:30:45.123456",
  "forum_url": "https://www.fisherydb.com/forum/",
  
  "categories": [
    {
      "id": "cat_1",
      "title": "BRANDS",
      "url": "https://www.fisherydb.com/forum/brands",
      "description": "Vessel's electronics brand...",
      "posts_count": "174",
      
      "subcategories": [
        {
          "id": "cat_1_sub_1",
          "title": "SIMRAD",
          "url": "https://www.fisherydb.com/forum/simrad",
          "description": "Welcome! Have a look around...",
          
          "posts": [
            {
              "id": "cat_1_sub_1_post_1",
              "title": "KM SIMRAD FS-70 -> ES80. Настройка линии трала",
              "url": "https://www.fisherydb.com/forum/simrad/km-simrad-fs-70...",
              "author": "kap.morgun",
              "created_at": "Oct 05",
              "description": "04.09.2025 Произведена настройка...",
              "content": "<html><p>Полный HTML контент поста...</p></html>",
              
              "attachments": [
                {
                  "filename": "Фото_1.jpg",
                  "url": "https://abc123.usrfiles.com/ugd/def456/photo1.jpg",
                  "downloaded": true,
                  "local_path": "data/attachments/cat_1_sub_1_post_1/Фото_1_abc12345.jpg"
                },
                {
                  "filename": "document.pdf",
                  "url": "https://xyz789.usrfiles.com/ugd/ghi012/doc.pdf",
                  "downloaded": true,
                  "local_path": "data/attachments/cat_1_sub_1_post_1/document_xyz78901.pdf"
                }
              ],
              
              "comments": [
                {
                  "id": "cat_1_sub_1_post_1_comment_1",
                  "author": "user123",
                  "created_at": "Oct 06",
                  "content": "<p>HTML контент комментария</p>"
                }
              ]
            }
          ]
        }
      ]
    }
  ],
  
  "statistics": {
    "categories_parsed": 10,
    "subcategories_parsed": 74,
    "posts_parsed": 4945,
    "comments_parsed": 3000,
    "files_downloaded": 1250,
    "errors_count": 5
  },
  
  "summary": {
    "total_categories": 10,
    "total_subcategories": 74,
    "total_posts": 4945
  }
}
```

### Размер файла

**Тестовый парсинг (5 постов):**
- ~50-200 KB

**Полный парсинг (4,945 постов):**
- ~50-200 MB (зависит от размера контента)

---

## 2️⃣ Скачанные вложения (data/attachments/)

### Структура папок

```
data/attachments/
├── cat_1_sub_1_post_1/           ← Папка для поста 1
│   ├── Фото_1_abc12345.jpg       ← Файл с хэшем для уникальности
│   ├── Фото_2_def67890.jpg
│   ├── document_xyz54321.pdf
│   └── settings_qwe98765.xlsx
│
├── cat_1_sub_1_post_2/           ← Папка для поста 2
│   └── manual_poi45678.pdf
│
├── cat_1_sub_2_post_15/          ← Другая подкатегория
│   ├── scheme_zxc33221.png
│   └── report_asd77889.docx
│
└── cat_2_sub_1_post_5/           ← Другая категория
    └── installation_wer11223.pdf
```

### Именование файлов

**Формат:** `{original_name}_{hash}.{extension}`

**Примеры:**
- Оригинал: `document.pdf`
- Сохранено: `document_abc12345.pdf`

**Зачем хэш?**
- Уникальность (разные посты могут иметь файлы с одинаковыми именами)
- Связь с оригинальным URL
- Защита от перезаписи

### Разрешенные типы файлов

Согласно `config/wix_config.yaml`:

```yaml
allowed_extensions:
  - ".pdf"      ← PDF документы
  - ".docx"     ← Word документы
  - ".xlsx"     ← Excel таблицы
  - ".jpg"      ← Изображения
  - ".png"      ← Изображения
  - ".gif"      ← Изображения
```

### Ограничения

- **Максимальный размер файла:** 100 MB (настраивается)
- **Пропускаются:** Файлы > 100 MB
- **Логируются:** Все пропущенные файлы

---

## 📊 Оценка объема данных

### После тестового парсинга (1 категория, 5 постов):

```
data/
├── exported/
│   └── forum_structure_20251017_153045.json  (~100 KB)
└── attachments/
    ├── cat_1_sub_1_post_1/  (~5-10 файлов, ~5-20 MB)
    ├── cat_1_sub_1_post_2/  (~2-5 файлов, ~2-10 MB)
    └── ...
    
Итого: ~100 MB
```

### После полного парсинга (10 категорий, 74 подкатегории, 4,945 постов):

```
data/
├── exported/
│   └── forum_structure_20251017_153045.json  (~50-200 MB)
└── attachments/
    ├── cat_1_sub_1_post_1/
    ├── cat_1_sub_1_post_2/
    ├── ... (4,945 папок с постами)
    └── cat_10_sub_74_post_XXX/
    
Итого: ~500 MB - 2 GB
```

**Рекомендация:** Убедитесь что на диске есть минимум **5 GB свободного места**.

---

## 🔍 Просмотр сохраненных данных

### Команды для проверки

**PowerShell:**

```powershell
# Посмотреть все JSON файлы
Get-ChildItem data\exported\*.json

# Посмотреть размер JSON файла
Get-Item data\exported\forum_structure_*.json | Select-Object Name, Length

# Посмотреть содержимое JSON (первые строки)
Get-Content data\exported\forum_structure_*.json -Head 20

# Подсчитать скачанные вложения
Get-ChildItem -Recurse data\attachments\*.* | Measure-Object | Select-Object Count

# Подсчитать размер вложений
Get-ChildItem -Recurse data\attachments | Measure-Object -Property Length -Sum | Select-Object Sum

# Посмотреть структуру папок вложений
Get-ChildItem data\attachments -Directory | Format-Table Name, @{Name="Files"; Expression={(Get-ChildItem $_.FullName).Count}}
```

**Linux/macOS:**

```bash
# Посмотреть JSON файлы
ls -lh data/exported/

# Красиво показать JSON
jq '.' data/exported/forum_structure_*.json | less

# Подсчитать вложения
find data/attachments -type f | wc -l

# Размер вложений
du -sh data/attachments/

# Статистика из JSON
jq '.statistics' data/exported/forum_structure_*.json
```

---

## 📄 Пример JSON записи

### Минимальный пост (без вложений):

```json
{
  "id": "cat_1_sub_1_post_1",
  "title": "Вопрос по SIMRAD",
  "url": "https://www.fisherydb.com/forum/simrad/question-123",
  "author": "user123",
  "created_at": "Oct 05",
  "description": "Краткое описание...",
  "content": "<p>Полный HTML контент...</p>",
  "attachments": [],
  "comments": []
}
```

**Размер:** ~1-2 KB

### Пост с вложениями и комментариями:

```json
{
  "id": "cat_1_sub_1_post_1",
  "title": "KM SIMRAD FS-70 -> ES80",
  "url": "https://www.fisherydb.com/forum/simrad/km-simrad-fs-70-es80",
  "author": "kap.morgun",
  "created_at": "Oct 05",
  "description": "04.09.2025 Произведена настройка...",
  "content": "<html>... (15 KB HTML контента) ...</html>",
  "attachments": [
    {
      "filename": "Фото_1.jpg",
      "url": "https://abc123.usrfiles.com/ugd/def456/photo1.jpg",
      "downloaded": true,
      "local_path": "data/attachments/cat_1_sub_1_post_1/Фото_1_abc12345.jpg"
    },
    {
      "filename": "Фото_2.jpg",
      "url": "https://xyz789.usrfiles.com/ugd/ghi012/photo2.jpg",
      "downloaded": true,
      "local_path": "data/attachments/cat_1_sub_1_post_1/Фото_2_xyz78901.jpg"
    }
  ],
  "comments": [
    {
      "id": "cat_1_sub_1_post_1_comment_1",
      "author": "another_user",
      "created_at": "Oct 06",
      "content": "<p>Спасибо за информацию!</p>"
    }
  ]
}
```

**Размер JSON:** ~20-50 KB  
**Размер вложений:** 2-10 MB (зависит от фото)

---

## 🗂️ Организация вложений

### По папкам постов

**Преимущества:**
- ✅ Легко найти вложения конкретного поста
- ✅ Не нужно искать в одной большой папке
- ✅ Можно легко удалить вложения одного поста
- ✅ Структура соответствует иерархии форума

**Пример:**
```
Пост: "KM SIMRAD FS-70 -> ES80"
ID: cat_1_sub_1_post_1

Вложения сохранены в:
data/attachments/cat_1_sub_1_post_1/
├── Фото_1_abc12345.jpg
├── Фото_2_def67890.jpg
├── Фото_3_ghi54321.jpg
├── Фото_4_jkl98765.jpg
├── Фото_5_mno33221.jpg
└── Фото_6_pqr77889.jpg
```

### Связь JSON ↔ Файлы

В JSON файле есть прямые ссылки на локальные файлы:

```json
"attachments": [
  {
    "filename": "Фото_1.jpg",
    "url": "https://...",  ← Оригинальный URL
    "downloaded": true,     ← Статус скачивания
    "local_path": "data/attachments/cat_1_sub_1_post_1/Фото_1_abc12345.jpg"  ← Локальный путь
  }
]
```

---

## 🔢 Примерная статистика

### Тестовый парсинг (лимиты: 1 категория, 5 постов)

| Элемент | Количество | Размер |
|---------|------------|--------|
| JSON файл | 1 | ~100-500 KB |
| Папок с вложениями | ~5 | - |
| Файлов скачано | ~10-25 | ~20-50 MB |
| **Итого** | - | **~50-100 MB** |

### Полный парсинг (без лимитов: все 4,945 постов)

| Элемент | Количество | Размер |
|---------|------------|--------|
| JSON файл | 1 | ~50-200 MB |
| Папок с вложениями | ~4,945 | - |
| Файлов скачано | ~1,000-2,000 | ~500 MB - 2 GB |
| **Итого** | - | **~600 MB - 3 GB** |

**Примечание:** Размер зависит от:
- Количества вложений в постах
- Размера PDF/DOCX/изображений
- Наличия больших файлов (> 100 MB пропускаются)

---

## 📝 Логи (logs/)

```
logs/
└── parser.log    ← Детальный лог работы парсера
```

**Формат лога:**
```
2025-10-17 15:30:45,123 - wix_parser - INFO - 🚀 НАЧАЛО ПОЛНОГО ПАРСИНГА ФОРУМА
2025-10-17 15:30:50,456 - wix_parser - INFO - Инициализация браузера...
2025-10-17 15:30:55,789 - wix_parser - INFO - ✓ Авторизация выполнена успешно
2025-10-17 15:31:00,012 - wix_parser - INFO - Найдено элементов категорий: 10
2025-10-17 15:31:05,345 - wix_parser - DEBUG -   ✓ Категория: BRANDS
...
```

**Размер:** ~1-50 MB (зависит от уровня логирования и количества данных)

---

## 🧹 Очистка данных

### Удалить результаты тестового парсинга

```powershell
# Удалить JSON
Remove-Item data\exported\*.json

# Удалить вложения
Remove-Item -Recurse data\attachments\*

# Удалить логи
Remove-Item logs\*.log
```

### Удалить только старые файлы

```powershell
# Удалить JSON старше 7 дней
Get-ChildItem data\exported\*.json | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } | Remove-Item

# Удалить большие файлы (>100MB)
Get-ChildItem -Recurse data\attachments | Where-Object { $_.Length -gt 100MB } | Remove-Item
```

---

## 💾 Резервное копирование

### Перед полным парсингом

**Создайте папку для бэкапов:**
```powershell
mkdir backups
```

**После успешного парсинга:**
```powershell
# Сжать данные в архив
Compress-Archive -Path data\exported\*, data\attachments\* -DestinationPath backups\forum_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').zip

# Или скопировать в безопасное место
Copy-Item -Recurse data\ backups\data_$(Get-Date -Format 'yyyyMMdd_HHmmss')\
```

### На внешний диск

```powershell
# Предположим внешний диск D:\
Copy-Item -Recurse data\ D:\fisherydb-forum-backup\
```

---

## 🔄 Workflow работы с данными

### 1. Парсинг

```bash
python scripts/run_parser.py
# ↓
# Создается: data/exported/forum_structure_20251017_153045.json
# Создаются: data/attachments/{post_id}/*.pdf, *.jpg, ...
```

### 2. Проверка

```powershell
# Посмотреть статистику из JSON
$data = Get-Content data\exported\forum_structure_*.json | ConvertFrom-Json
$data.statistics

# Проверить вложения
Get-ChildItem -Recurse data\attachments\*.* | Measure-Object
```

### 3. Резервное копирование

```powershell
Compress-Archive -Path data\* -DestinationPath backups\forum_$(Get-Date -Format 'yyyyMMdd').zip
```

### 4. Импорт в Discourse

```bash
python scripts/run_importer.py data/exported/forum_structure_20251017_153045.json
# ↑
# Читает JSON
# Загружает вложения из data/attachments/
# Создает в Discourse
```

---

## 📍 Абсолютные пути

**Текущее расположение:**

```
E:\OneDrive\Documents\Cursor\fisherydb-forum\
```

**Полные пути к данным:**

- **JSON:** `E:\OneDrive\Documents\Cursor\fisherydb-forum\data\exported\`
- **Вложения:** `E:\OneDrive\Documents\Cursor\fisherydb-forum\data\attachments\`
- **Логи:** `E:\OneDrive\Documents\Cursor\fisherydb-forum\logs\`

---

## ⚙️ Настройка путей (если нужно изменить)

### В config/wix_config.yaml:

```yaml
# Изменить путь к вложениям
attachments:
  download_dir: "D:/forum_attachments"  # Другой диск
  
# Изменить путь к JSON
export:
  output_dir: "D:/forum_exported"       # Другой диск
  
# Изменить путь к логам
logging:
  file: "D:/forum_logs/parser.log"     # Другой диск
```

**Примечание:** В Windows используйте либо `\` либо `/` в путях

---

## 📦 Что будет после парсинга

### Визуализация

```
data/
│
├── exported/
│   └── forum_structure_20251017_153045.json  📄 50-200 MB
│       ├── 10 категорий
│       ├── 74 подкатегории
│       ├── 4,945 постов
│       └── ~3,000 комментариев
│
└── attachments/  📁 500 MB - 2 GB
    ├── cat_1_sub_1_post_1/  (6 файлов)
    ├── cat_1_sub_1_post_2/  (3 файла)
    ├── cat_1_sub_1_post_3/  (2 файла)
    ├── ... (4,942 папки)
    └── cat_10_sub_74_post_XXX/  (1 файл)
```

### Что с этим делать дальше?

1. **Проверить данные** - открыть JSON, посмотреть вложения
2. **Сделать бэкап** - на всякий случай
3. **Запустить импорт** в Discourse
4. **После успешного импорта** - можно удалить локальные данные

---

## ✅ Готовы к парсингу?

**Убедитесь что:**
- [x] На диске есть минимум 5 GB свободного места
- [x] Путь `E:\OneDrive\Documents\Cursor\fisherydb-forum\data\` доступен
- [x] У вас есть права на запись в эту папку
- [x] Интернет стабильный (для скачивания вложений)

**Команда для запуска:**
```bash
python scripts/run_parser.py
```

**Результат будет в:**
- 📄 `data/exported/forum_structure_*.json`
- 📁 `data/attachments/{post_id}/`
- 📋 `logs/parser.log`

---

**Вопросы? Смотрите:**
- [QUICK_START.md](../QUICK_START.md) - быстрый старт
- [docs/TESTING.md](TESTING.md) - тестирование
- [CHEATSHEET.md](../CHEATSHEET.md) - команды

