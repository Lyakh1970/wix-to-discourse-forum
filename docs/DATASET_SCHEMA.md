# Dataset Schema — Draft

This document describes the normalized dataset we want to derive from the December 2025 export.

## Normalized topic/post record

```json
{
  "source_url": "",
  "wix_group_url": "",
  "category_source": "",
  "category_discourse": "",
  "title": "",
  "author": "",
  "created_at": "",
  "body_html": "",
  "body_markdown": "",
  "comments": [],
  "attachments": [],
  "images": [],
  "import_status": ""
}
```

## Comment record

```json
{
  "author": "",
  "created_at": "",
  "body_html": "",
  "body_markdown": "",
  "attachments": []
}
```

## Attachment record

```json
{
  "source_url": "",
  "local_path": "",
  "filename": "",
  "mime_type": "",
  "size_bytes": 0,
  "sha256": "",
  "status": "present|missing|unknown"
}
```
