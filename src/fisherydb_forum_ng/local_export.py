from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .models import ATTACHMENT_EXTENSIONS, FileInventory, LocalInventory


FORUM_HINT_NAMES = {
    "forum_structure_detailed.json",
    "category_mapping.json",
    "discourse_categories.json",
    "CATEGORY_MAPPING_REVIEW.md",
    "parser.log",
    "parser_with_dedup_comments.py",
    "parse_category_brands.py",
}


def safe_read_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return None
    except Exception:
        return None


def file_inventory(path: Path, root: Path) -> FileInventory:
    return FileInventory(
        path=str(path.relative_to(root)),
        suffix=path.suffix.lower(),
        size_bytes=path.stat().st_size,
    )


def walk_local_export(root: Path) -> LocalInventory:
    inv = LocalInventory(root=str(root))

    if not root.exists():
        inv.warnings.append(f"Root does not exist: {root}")
        return inv

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        inv.total_files += 1
        suffix = path.suffix.lower()
        inv.by_extension[suffix or "<no extension>"] = inv.by_extension.get(suffix or "<no extension>", 0) + 1

        fi = file_inventory(path, root)

        if suffix == ".json":
            inv.json_files.append(fi)
        elif suffix in {".html", ".htm"}:
            inv.html_files.append(fi)
        elif suffix in {".md", ".markdown"}:
            inv.markdown_files.append(fi)
        elif suffix in ATTACHMENT_EXTENSIONS:
            inv.attachment_like_files.append(fi)

        if path.name in FORUM_HINT_NAMES:
            inv.candidate_forum_files.append(str(path.relative_to(root)))

    inv.detected_counts = detect_counts(root, inv)
    return inv


def detect_counts(root: Path, inv: LocalInventory) -> dict[str, Any]:
    counts: dict[str, Any] = {
        "json_files_scanned": 0,
        "possible_records": 0,
        "possible_posts": 0,
        "possible_comments": 0,
        "possible_attachments_referenced": 0,
        "files_with_posts_like_data": [],
        "thread_json_files": [],
        "sqlite_databases": [],
        "field_quality": {},
    }

    field_quality = {
        "threads_missing_title": 0,
        "threads_missing_date": 0,
        "threads_missing_author": 0,
        "threads_missing_category": 0,
        "posts_missing_body": 0,
        "posts_missing_date": 0,
        "posts_missing_author": 0,
        "posts_missing_attachments_local_path": 0,
    }

    for fi in inv.json_files:
        path = root / fi.path
        data = safe_read_json(path)
        if data is None:
            continue

        counts["json_files_scanned"] += 1

        thread_stats = inspect_threads_json(data)
        if thread_stats["threads"] or thread_stats["posts"]:
            counts["thread_json_files"].append({"path": fi.path, **thread_stats})
            counts["possible_records"] += thread_stats["threads"]
            counts["possible_posts"] += thread_stats["posts"]
            counts["possible_comments"] += thread_stats["comments"]
            counts["possible_attachments_referenced"] += thread_stats["attachments"]
            for key, value in thread_stats["field_quality"].items():
                field_quality[key] += value
            continue

        stats = inspect_json_for_forum_data(data)
        if stats["records"] or stats["comments"] or stats["attachments"]:
            counts["files_with_posts_like_data"].append(
                {
                    "path": fi.path,
                    "records": stats["records"],
                    "comments": stats["comments"],
                    "attachments": stats["attachments"],
                    "keys_seen": stats["keys_seen"],
                }
            )
            counts["possible_records"] += stats["records"]
            counts["possible_comments"] += stats["comments"]
            counts["possible_attachments_referenced"] += stats["attachments"]

    for db_path in root.rglob("*.db"):
        db_stats = inspect_sqlite_database(db_path, root)
        if db_stats:
            counts["sqlite_databases"].append(db_stats)

    counts["field_quality"] = field_quality
    return counts


def is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def inspect_threads_json(data: Any) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "category": None,
        "declared_thread_count": None,
        "threads": 0,
        "posts": 0,
        "comments": 0,
        "attachments": 0,
        "field_quality": {
            "threads_missing_title": 0,
            "threads_missing_date": 0,
            "threads_missing_author": 0,
            "threads_missing_category": 0,
            "posts_missing_body": 0,
            "posts_missing_date": 0,
            "posts_missing_author": 0,
            "posts_missing_attachments_local_path": 0,
        },
    }

    if not isinstance(data, dict) or not isinstance(data.get("threads"), list):
        return stats

    stats["category"] = data.get("category")
    stats["declared_thread_count"] = data.get("thread_count")

    for thread in data["threads"]:
        if not isinstance(thread, dict):
            continue
        stats["threads"] += 1
        if is_missing(thread.get("title")):
            stats["field_quality"]["threads_missing_title"] += 1
        if is_missing(thread.get("created_at")):
            stats["field_quality"]["threads_missing_date"] += 1
        if not thread.get("author"):
            stats["field_quality"]["threads_missing_author"] += 1
        if is_missing(thread.get("category_slug")):
            stats["field_quality"]["threads_missing_category"] += 1

        posts = thread.get("posts")
        if not isinstance(posts, list):
            continue

        for post in posts:
            if not isinstance(post, dict):
                continue
            stats["posts"] += 1
            if post.get("is_comment"):
                stats["comments"] += 1
            if is_missing(post.get("content_text")) and is_missing(post.get("content_html")):
                stats["field_quality"]["posts_missing_body"] += 1
            if is_missing(post.get("created_at")):
                stats["field_quality"]["posts_missing_date"] += 1
            if not post.get("author"):
                stats["field_quality"]["posts_missing_author"] += 1

            attachments = post.get("attachments") if isinstance(post.get("attachments"), list) else []
            images = post.get("images") if isinstance(post.get("images"), list) else []
            stats["attachments"] += len(attachments) + len(images)
            for attachment in [*attachments, *images]:
                if isinstance(attachment, dict) and is_missing(attachment.get("local_path")):
                    stats["field_quality"]["posts_missing_attachments_local_path"] += 1

    return stats


def inspect_sqlite_database(path: Path, root: Path) -> dict[str, Any] | None:
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error:
        return None

    try:
        tables = {
            row[0]
            for row in con.execute("select name from sqlite_master where type='table'")
        }
        expected = {"categories", "authors", "threads", "posts", "attachments"}
        if not expected & tables:
            return None

        stats: dict[str, Any] = {
            "path": str(path.relative_to(root)),
            "tables": sorted(tables),
            "counts": {},
            "field_quality": {},
        }
        for table in sorted(expected & tables):
            stats["counts"][table] = con.execute(f"select count(*) from {table}").fetchone()[0]

        if "posts" in tables:
            stats["counts"]["comments"] = con.execute(
                "select count(*) from posts where is_comment = 1"
            ).fetchone()[0]
            stats["field_quality"]["posts_missing_body"] = con.execute(
                "select count(*) from posts where coalesce(trim(content_text), '') = '' "
                "and coalesce(trim(content_html), '') = ''"
            ).fetchone()[0]
            stats["field_quality"]["posts_missing_date"] = con.execute(
                "select count(*) from posts where coalesce(trim(created_at), '') = ''"
            ).fetchone()[0]
            stats["field_quality"]["posts_missing_author"] = con.execute(
                "select count(*) from posts where coalesce(trim(author_username), '') = ''"
            ).fetchone()[0]

        if "threads" in tables:
            stats["field_quality"]["threads_missing_title"] = con.execute(
                "select count(*) from threads where coalesce(trim(title), '') = ''"
            ).fetchone()[0]
            stats["field_quality"]["threads_missing_date"] = con.execute(
                "select count(*) from threads where coalesce(trim(created_at), '') = ''"
            ).fetchone()[0]
            stats["field_quality"]["threads_missing_author"] = con.execute(
                "select count(*) from threads where coalesce(trim(author_username), '') = ''"
            ).fetchone()[0]
            stats["field_quality"]["threads_missing_category"] = con.execute(
                "select count(*) from threads where coalesce(trim(category_slug), '') = ''"
            ).fetchone()[0]

        if "attachments" in tables:
            stats["counts"]["images"] = con.execute(
                "select count(*) from attachments where is_image = 1"
            ).fetchone()[0]
            stats["field_quality"]["attachments_missing_local_path"] = con.execute(
                "select count(*) from attachments where coalesce(trim(local_path), '') = ''"
            ).fetchone()[0]

        return stats
    finally:
        con.close()


def inspect_json_for_forum_data(data: Any) -> dict[str, Any]:
    stats = {
        "records": 0,
        "comments": 0,
        "attachments": 0,
        "keys_seen": [],
    }

    def visit(obj: Any) -> None:
        if isinstance(obj, dict):
            keys = set(obj.keys())
            interesting = keys & {
                "title", "body", "content", "html", "markdown", "comments",
                "attachments", "images", "author", "date", "created_at",
                "url", "source_url", "category"
            }
            if interesting:
                stats["keys_seen"] = sorted(set(stats["keys_seen"]) | interesting)

            if {"title", "url"} <= keys or {"title", "content"} <= keys or {"title", "body"} <= keys:
                stats["records"] += 1

            comments = obj.get("comments")
            if isinstance(comments, list):
                stats["comments"] += len(comments)

            attachments = obj.get("attachments")
            if isinstance(attachments, list):
                stats["attachments"] += len(attachments)

            images = obj.get("images")
            if isinstance(images, list):
                stats["attachments"] += len(images)

            for value in obj.values():
                visit(value)

        elif isinstance(obj, list):
            for item in obj:
                visit(item)

    visit(data)
    stats["keys_seen"] = stats["keys_seen"][:50]
    return stats


def to_dict(inv: LocalInventory) -> dict[str, Any]:
    return {
        "root": inv.root,
        "total_files": inv.total_files,
        "by_extension": dict(sorted(inv.by_extension.items())),
        "json_files": [x.__dict__ for x in inv.json_files],
        "html_files": [x.__dict__ for x in inv.html_files],
        "markdown_files": [x.__dict__ for x in inv.markdown_files],
        "attachment_like_files_count": len(inv.attachment_like_files),
        "attachment_like_files_sample": [x.__dict__ for x in inv.attachment_like_files[:100]],
        "candidate_forum_files": inv.candidate_forum_files,
        "detected_counts": inv.detected_counts,
        "warnings": inv.warnings,
    }


def write_markdown_report(inv: LocalInventory, output_path: Path) -> None:
    data = to_dict(inv)

    lines = []
    lines.append("# Local Export Inventory")
    lines.append("")
    lines.append(f"Root: `{inv.root}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total files: **{inv.total_files}**")
    lines.append(f"- JSON files: **{len(inv.json_files)}**")
    lines.append(f"- HTML files: **{len(inv.html_files)}**")
    lines.append(f"- Markdown files: **{len(inv.markdown_files)}**")
    lines.append(f"- Attachment-like files: **{len(inv.attachment_like_files)}**")
    lines.append("")

    lines.append("## Extensions")
    lines.append("")
    lines.append("| Extension | Count |")
    lines.append("|---|---:|")
    for ext, count in sorted(inv.by_extension.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"| `{ext}` | {count} |")
    lines.append("")

    lines.append("## Candidate forum files")
    lines.append("")
    if inv.candidate_forum_files:
        for p in inv.candidate_forum_files:
            lines.append(f"- `{p}`")
    else:
        lines.append("_No known candidate files found by name._")
    lines.append("")

    dc = inv.detected_counts
    lines.append("## Detected forum-like data")
    lines.append("")
    lines.append(f"- JSON files scanned: **{dc.get('json_files_scanned', 0)}**")
    lines.append(f"- Possible topic/post records: **{dc.get('possible_records', 0)}**")
    lines.append(f"- Possible post rows: **{dc.get('possible_posts', 0)}**")
    lines.append(f"- Possible comments: **{dc.get('possible_comments', 0)}**")
    lines.append(f"- Possible attachments/images referenced: **{dc.get('possible_attachments_referenced', 0)}**")
    lines.append("")

    thread_files = dc.get("thread_json_files", [])
    lines.append("## Thread JSON files")
    lines.append("")
    if thread_files:
        lines.append("| File | Category | Threads | Posts | Comments | Attachments | Missing body |")
        lines.append("|---|---|---:|---:|---:|---:|---:|")
        for item in thread_files[:200]:
            fq = item.get("field_quality", {})
            lines.append(
                f"| `{item['path']}` | {item.get('category') or ''} | "
                f"{item['threads']} | {item['posts']} | {item['comments']} | "
                f"{item['attachments']} | {fq.get('posts_missing_body', 0)} |"
            )
    else:
        lines.append("_No structured thread JSON files detected._")
    lines.append("")

    sqlite_databases = dc.get("sqlite_databases", [])
    lines.append("## SQLite databases")
    lines.append("")
    if sqlite_databases:
        for db in sqlite_databases:
            counts = db.get("counts", {})
            lines.append(f"- `{db['path']}`")
            lines.append(f"  - Categories: **{counts.get('categories', 0)}**")
            lines.append(f"  - Threads: **{counts.get('threads', 0)}**")
            lines.append(f"  - Posts: **{counts.get('posts', 0)}**")
            lines.append(f"  - Comments: **{counts.get('comments', 0)}**")
            lines.append(f"  - Attachments: **{counts.get('attachments', 0)}**")
            lines.append(f"  - Images: **{counts.get('images', 0)}**")
    else:
        lines.append("_No forum-like SQLite databases detected._")
    lines.append("")

    fq = dc.get("field_quality", {})
    lines.append("## Field quality")
    lines.append("")
    if fq:
        lines.append("| Check | Count |")
        lines.append("|---|---:|")
        for key, count in sorted(fq.items()):
            lines.append(f"| `{key}` | {count} |")
    else:
        lines.append("_No field quality checks available._")
    lines.append("")

    lines.append("## Files with post-like data")
    lines.append("")
    files = dc.get("files_with_posts_like_data", [])
    if files:
        lines.append("| File | Records | Comments | Attachments | Keys seen |")
        lines.append("|---|---:|---:|---:|---|")
        for item in files[:200]:
            keys = ", ".join(item.get("keys_seen", []))
            lines.append(
                f"| `{item['path']}` | {item['records']} | {item['comments']} | {item['attachments']} | {keys} |"
            )
    else:
        lines.append("_No post-like JSON data detected yet._")
    lines.append("")

    if inv.warnings:
        lines.append("## Warnings")
        lines.append("")
        for warning in inv.warnings:
            lines.append(f"- {warning}")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
