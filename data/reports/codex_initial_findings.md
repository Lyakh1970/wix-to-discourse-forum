# Codex Initial Findings

Дата проверки: 2026-05-18

Источник: `E:\OneDrive\Documents\Claude\projects\fisherydb-forum-parser`

## Краткое резюме

Локальный декабрьский массив выглядит как основной экспорт старого форума FisheryDB, а не как случайный набор промежуточных файлов. В нём найден центральный SQLite-индекс `output\forum_data.db`, 60 категорийных `threads.json`, локальные папки `images` / `attachments`, а также файлы маппинга категорий для Discourse.

По обновлённой инвентаризации найдено примерно:

- категорий в SQLite: 67;
- тем / threads: 589;
- строк posts: 1236;
- комментариев: 647;
- ссылок на вложения в SQLite: 1151;
- ссылок на вложения / изображения в JSON: 1158;
- локальных attachment-like файлов: 1139.

Импорт в Discourse не выполнялся. Исходный каталог не изменялся.

## Найденные ключевые файлы

- `output\forum_data.db` — основной структурированный индекс с таблицами `categories`, `authors`, `threads`, `posts`, `attachments`.
- `output\*\threads.json` — 60 JSON-файлов по категориям; внутри есть `threads`, вложенные `posts`, `is_comment`, `attachments`, `images`.
- `category_mapping.json` — найден.
- `CATEGORY_MAPPING_REVIEW.md` — найден.
- `discourse_categories.json` — найден.
- `parser.log` — найден.
- `frame_content.html` — найден, вероятно диагностический / промежуточный HTML.
- `forum_structure_detailed.json` — не найден.
- `auth_state.json` — найден в исходном каталоге; это секретный/сессионный файл, не коммитить.

## Предварительная оценка полноты

Массив выглядит достаточно полным для первичного локального аудита: есть и JSON-представление, и SQLite-база, и локально скачанные изображения/файлы. Самые крупные категории по числу тем: `fs-issues`, `km-issues`, `ks-issues`, `marport-1`, `mk-issues`, `mv-issues`, `other-equipment` — по 30 тем каждая.

Однако полнота пока не доказана относительно Wix Groups и текущего Discourse. Также в таблице `categories` поле `thread_count` везде равно 0, поэтому фактические количества нужно брать из таблицы `threads` или из `threads.json`, а не из declared category counts.

## Главные проблемы качества данных

- `forum_structure_detailed.json` отсутствует, поэтому структуру форума нужно восстанавливать из `forum_data.db`, `category_mapping.json`, `discourse_categories.json` и `CATEGORY_MAPPING_REVIEW.md`.
- В SQLite у 15 attachment-записей пустой `local_path`; в JSON-проверке таких ссылок 18. При этом все непустые `local_path` существуют локально.
- Разница между количеством ссылок на вложения в SQLite (1151) и JSON (1158) требует сверки.
- Поля `title`, `body/content`, `date`, `author`, `category` выглядят заполненными: по текущим проверкам 0 пустых title/date/author/category у тем и 0 пустых body/date/author у posts.
- Дубликаты по `thread.id`, `thread.url`, `post.id`, `attachment.id` в SQLite не обнаружены.
- Комментарии не лежат в отдельном верхнеуровневом `comments` поле; они представлены как `posts` с `is_comment = true`. Старый вариант инвентаризации поэтому показывал 0 комментариев.

## Что сделать следующим шагом

1. Сформировать отдельный отчёт по структуре категорий из `forum_data.db`, `category_mapping.json` и `CATEGORY_MAPPING_REVIEW.md`.
2. Сверить 1151/1158 attachment references и вывести список записей без `local_path`.
3. Проверить соответствие 60 `output\*\threads.json` против 67 категорий SQLite: какие категории есть в базе, но не имеют отдельного `threads.json`, и наоборот.
4. Начать read-only сравнение с Wix Groups по seed-списку из `config\wix_groups.yaml`, без нового массового парсинга.
5. После этого сделать read-only inventory текущего Discourse и собрать матрицу `Wix Groups / Local Export / Discourse`.
