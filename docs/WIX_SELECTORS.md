# Селекторы WIX форума

Документация найденных селекторов на основе анализа HTML структуры форума.

## 📋 Data-hook атрибуты

WIX использует специальные `data-hook` атрибуты для идентификации элементов.

### Категории и подкатегории

```html
<li data-hook="category-list-item">
  <a data-hook="category-list-item__link" href="/forum/brands">
    <h2 data-hook="category-list-item__title">BRANDS</h2>
  </a>
  <p data-hook="category-list-item__description">
    Vessel's electronics brand (Furuno, Simrad, Sailor etc...)
  </p>
  <div data-hook="category-list-item__total-posts">
    <span>174</span>
  </div>
</li>
```

**Селекторы:**
- Элемент категории: `li[data-hook='category-list-item']`
- Ссылка на категорию: `a[data-hook='category-list-item__link']`
- Заголовок: `h2[data-hook='category-list-item__title']`
- Описание: `p[data-hook='category-list-item__description']`
- Количество постов: `[data-hook='category-list-item__total-posts'] span`

### Подкатегории

Подкатегории используют те же атрибуты, но с префиксом `subcategory`:

```html
<a data-hook="subcategory-list-item__link" href="/forum/simrad">
  <h2 data-hook="category-list-item__title">SIMRAD</h2>
</a>
```

**Селекторы:**
- Элемент: `li[data-hook='category-list-item']` (тот же!)
- Ссылка: `a[data-hook='subcategory-list-item__link']`

### Посты

```html
<div data-hook="post-list-item" role="article">
  <div data-hook="post-title">
    <a href="/forum/simrad/km-simrad-fs-70-es80">
      KM SIMRAD FS-70 -> ES80
    </a>
  </div>
  <div data-hook="avatar__name">kap.morgun</div>
  <span data-hook="time-ago">Oct 05</span>
  <div data-hook="post-description">
    04.09.2025 Произведена настройка...
  </div>
  <div data-hook="post-list-item__view-count">
    <span>4</span>
  </div>
  <div data-hook="post-list-item__comment-count">
    <span>0</span>
  </div>
</div>
```

**Селекторы:**
- Элемент поста: `div[data-hook='post-list-item']`
- Заголовок: `[data-hook='post-title']`
- Автор: `[data-hook='avatar__name']`
- Дата: `[data-hook='time-ago']`
- Описание: `[data-hook='post-description']`
- Просмотры: `[data-hook='post-list-item__view-count'] span`
- Комментарии: `[data-hook='post-list-item__comment-count'] span`

### Комментарии

```html
<div data-hook="comment">
  <div data-hook="avatar__name">username</div>
  <span data-hook="time-ago">Oct 05</span>
  <div class="comment-content">
    Текст комментария...
  </div>
</div>
```

**Селекторы:**
- Список: `[data-hook='comments-list']`
- Элемент комментария: `[data-hook='comment']`
- Автор: `[data-hook='avatar__name']`
- Дата: `[data-hook='time-ago']`
- Контент: `.comment-content`

### Вложения

```html
<a class="PaFuZ" href="https://abc123.usrfiles.com/ugd/def456_hash/filename.pdf">
  <span>filename.pdf</span>
</a>
```

**Селектор:** `a.PaFuZ`

**Структура URL:** `https://{uuid}.usrfiles.com/ugd/{hash}/{filename}`

## 🎨 CSS классы

### Основные элементы

- `.forum-text-color` - цвет текста форума
- `.forum-link-hover-color` - цвет ссылок при наведении
- `.forum-card-background-color` - фон карточек
- `.forum-card-border-color` - граница карточек
- `.forum-title-classic-font` - шрифт заголовков
- `.forum-content-classic-font` - шрифт контента

### Специфичные классы

- `.post-list-item` - элемент поста
- `.post-title` - заголовок поста
- `.post-header` - заголовочная часть
- `.post-content` - контент поста
- `.ricos-viewer` - просмотрщик rich-content

## 🔗 URL структура

### Категории
```
https://www.fisherydb.com/forum/brands
https://www.fisherydb.com/forum/mrto-2022-2023-2024
https://www.fisherydb.com/forum/issues-log-log-polomok
```

### Подкатегории
```
https://www.fisherydb.com/forum/simrad
https://www.fisherydb.com/forum/furuno
https://www.fisherydb.com/forum/km-issues
```

### Посты
```
https://www.fisherydb.com/forum/simrad/km-simrad-fs-70-es80-nastroyka-linii-trala-s-tz-fs-70-na-eholot-es-80
https://www.fisherydb.com/forum/furuno/furuno-fcv-38-echo-sounder-settings
```

## 📅 Форматы дат

WIX использует короткий формат без года:

- `Oct 05` - 5 октября (текущего года)
- `Sep 11` - 11 сентября
- `Jun 06` - 6 июня

Парсер автоматически добавляет текущий год при обработке.

## 🔐 Приватные разделы

Некоторые категории имеют иконку замка:

```html
<h2 data-hook="category-list-item__title">
  MN ISSUE
  <span class="LFZg4I">
    <svg data-hook="lock-empty-icon">...</svg>
  </span>
</h2>
```

**Селектор для проверки:** `svg[data-hook='lock-empty-icon']`

Эти разделы требуют авторизации.

## 🔧 Конфигурация селекторов

Все эти селекторы уже добавлены в `config/wix_config.yaml`:

```yaml
selectors:
  # Категории
  category_item: "li[data-hook='category-list-item']"
  category_title: "h2[data-hook='category-list-item__title']"
  category_description: "p[data-hook='category-list-item__description']"
  category_link: "a[data-hook='category-list-item__link'], a[data-hook='subcategory-list-item__link']"
  
  # Подкатегории
  subcategory_item: "li[data-hook='category-list-item']"
  subcategory_link: "a[data-hook='subcategory-list-item__link']"
  subcategory_title: "h2[data-hook='category-list-item__title']"
  
  # Посты
  post_item: "div[data-hook='post-list-item']"
  post_title: "[data-hook='post-title']"
  post_description: "[data-hook='post-description']"
  post_author: "[data-hook='avatar__name']"
  post_date: "[data-hook='time-ago']"
  post_views: "[data-hook='post-list-item__view-count']"
  post_comments: "[data-hook='post-list-item__comment-count']"
  
  # Детали поста
  post_full_content: ".post-content, .ricos-viewer"
  
  # Комментарии
  comment_list: "[data-hook='comments-list']"
  comment_item: "[data-hook='comment']"
  comment_author: "[data-hook='avatar__name']"
  comment_date: "[data-hook='time-ago']"
  comment_content: ".comment-content"
  
  # Вложения
  attachment_link: "a.PaFuZ"
```

## 📝 Примечания

1. **data-hook атрибуты** более надежны чем CSS классы, так как WIX часто генерирует случайные классы
2. **Категории и подкатегории** используют одинаковые селекторы - различаются только по контексту (на какой странице находятся)
3. **Даты в формате "Oct 05"** требуют добавления текущего года
4. **Вложения (PaFuZ)** доступны без авторизации по прямым URL

## 🧪 Тестирование селекторов

Для проверки селекторов используйте:

1. **Анализ форума:**
   ```bash
   python scripts/analyze_forum.py
   ```

2. **DevTools в браузере:**
   - Открыть форум
   - F12 → Console
   - Ввести: `document.querySelectorAll('[data-hook="post-list-item"]').length`

3. **Playwright Inspector:**
   ```bash
   playwright codegen https://www.fisherydb.com/forum/
   ```

---

**Статус:** ✅ Все селекторы найдены и добавлены в конфигурацию

