from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def analyze_local_dataset(root: Path) -> dict[str, Any]:
    report: dict[str, Any] = {
        "root": str(root),
        "warnings": [],
        "key_files": {},
        "sqlite": {},
        "thread_json": {},
        "category_mapping": {},
        "discourse_categories": {},
        "category_reconciliation": {},
        "attachment_reconciliation": {},
        "quality": {},
        "recommendations": [],
    }

    if not root.exists():
        report["warnings"].append(f"Root does not exist: {root}")
        return report

    paths = {
        "forum_data_db": root / "output" / "forum_data.db",
        "category_mapping_json": root / "category_mapping.json",
        "category_mapping_review_md": root / "CATEGORY_MAPPING_REVIEW.md",
        "discourse_categories_json": root / "discourse_categories.json",
        "forum_structure_detailed_json": root / "forum_structure_detailed.json",
        "auth_state_json": root / "auth_state.json",
    }
    report["key_files"] = {
        name: {
            "exists": path.exists(),
            "path": str(path.relative_to(root)) if path.exists() else str(path),
            "size_bytes": path.stat().st_size if path.exists() else None,
        }
        for name, path in paths.items()
    }

    sqlite_data = inspect_forum_database(paths["forum_data_db"], root)
    report["sqlite"] = sqlite_data

    thread_json_data = inspect_thread_json_files(root)
    report["thread_json"] = thread_json_data

    mapping_data = inspect_category_mapping(paths["category_mapping_json"])
    report["category_mapping"] = mapping_data

    discourse_data = inspect_discourse_categories(paths["discourse_categories_json"])
    report["discourse_categories"] = discourse_data

    report["category_reconciliation"] = reconcile_categories(
        sqlite_data, thread_json_data, mapping_data, discourse_data
    )
    report["attachment_reconciliation"] = reconcile_attachments(
        root, sqlite_data, thread_json_data
    )
    report["quality"] = inspect_quality(sqlite_data)
    report["recommendations"] = build_recommendations(report)
    return report


def inspect_forum_database(path: Path, root: Path) -> dict[str, Any]:
    data: dict[str, Any] = {
        "exists": path.exists(),
        "path": str(path.relative_to(root)) if path.exists() else str(path),
        "tables": [],
        "counts": {},
        "categories": [],
        "duplicate_counts": {},
        "attachment_issues": {},
    }
    if not path.exists():
        return data

    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        tables = [
            row["name"]
            for row in con.execute("select name from sqlite_master where type='table' order by name")
        ]
        data["tables"] = tables
        for table in ["authors", "categories", "threads", "posts", "attachments"]:
            if table in tables:
                data["counts"][table] = con.execute(f"select count(*) from {table}").fetchone()[0]

        if "posts" in tables:
            data["counts"]["comments"] = con.execute(
                "select count(*) from posts where is_comment = 1"
            ).fetchone()[0]
            data["counts"]["root_posts"] = con.execute(
                "select count(*) from posts where coalesce(is_comment, 0) = 0"
            ).fetchone()[0]

        if "attachments" in tables:
            data["counts"]["images"] = con.execute(
                "select count(*) from attachments where is_image = 1"
            ).fetchone()[0]
            data["counts"]["non_images"] = con.execute(
                "select count(*) from attachments where coalesce(is_image, 0) = 0"
            ).fetchone()[0]
            missing_local_path = [
                dict(row)
                for row in con.execute(
                    "select id, post_id, url, filename, file_type, local_path, is_image "
                    "from attachments where coalesce(trim(local_path), '') = '' "
                    "order by post_id, filename"
                )
            ]
            broken_local_path = []
            for row in con.execute(
                "select id, post_id, url, filename, file_type, local_path, is_image "
                "from attachments where coalesce(trim(local_path), '') <> '' "
                "order by post_id, filename"
            ):
                item = dict(row)
                if not (root / item["local_path"]).exists():
                    broken_local_path.append(item)
            data["attachment_issues"] = {
                "missing_local_path_count": len(missing_local_path),
                "missing_local_path": missing_local_path,
                "broken_local_path_count": len(broken_local_path),
                "broken_local_path": broken_local_path,
            }

        if "categories" in tables and "threads" in tables:
            data["categories"] = [
                dict(row)
                for row in con.execute(
                    "select c.slug, c.name, c.url, c.parent_slug, c.thread_count as declared_thread_count, "
                    "count(t.id) as actual_thread_count "
                    "from categories c left join threads t on t.category_slug = c.slug "
                    "group by c.slug, c.name, c.url, c.parent_slug, c.thread_count "
                    "order by actual_thread_count desc, c.slug"
                )
            ]

        data["duplicate_counts"] = {
            "thread_ids": duplicate_count(con, "threads", "id"),
            "thread_urls": duplicate_count(con, "threads", "url"),
            "post_ids": duplicate_count(con, "posts", "id"),
            "attachment_ids": duplicate_count(con, "attachments", "id"),
        }
        return data
    finally:
        con.close()


def duplicate_count(con: sqlite3.Connection, table: str, column: str) -> int:
    try:
        return con.execute(
            f"select count(*) from (select {column} from {table} group by {column} having count(*) > 1)"
        ).fetchone()[0]
    except sqlite3.Error:
        return 0


def inspect_thread_json_files(root: Path) -> dict[str, Any]:
    files = []
    categories = []
    totals = Counter()
    attachments_by_key: Counter[str] = Counter()
    missing_local_path = []

    for path in sorted((root / "output").glob("*/threads.json")):
        data = read_json(path)
        if not isinstance(data, dict):
            continue
        threads = data.get("threads")
        if not isinstance(threads, list):
            continue

        rel = str(path.relative_to(root))
        category = data.get("category") or path.parent.name
        categories.append(category)
        item = {
            "path": rel,
            "category": category,
            "declared_thread_count": data.get("thread_count"),
            "threads": 0,
            "posts": 0,
            "comments": 0,
            "attachments": 0,
            "images": 0,
            "missing_local_path": 0,
        }

        for thread in threads:
            if not isinstance(thread, dict):
                continue
            item["threads"] += 1
            posts = thread.get("posts") if isinstance(thread.get("posts"), list) else []
            for post in posts:
                if not isinstance(post, dict):
                    continue
                item["posts"] += 1
                if post.get("is_comment"):
                    item["comments"] += 1
                for key in ["attachments", "images"]:
                    values = post.get(key) if isinstance(post.get(key), list) else []
                    item["attachments"] += len(values)
                    if key == "images":
                        item["images"] += len(values)
                    for attachment in values:
                        if not isinstance(attachment, dict):
                            continue
                        marker = attachment.get("local_path") or attachment.get("url") or attachment.get("filename")
                        if marker:
                            attachments_by_key[str(marker)] += 1
                        if not attachment.get("local_path"):
                            item["missing_local_path"] += 1
                            missing_local_path.append(
                                {
                                    "category": category,
                                    "thread_id": thread.get("id"),
                                    "post_id": post.get("id"),
                                    "filename": attachment.get("filename"),
                                    "url": attachment.get("url"),
                                }
                            )

        for key in ["threads", "posts", "comments", "attachments", "images", "missing_local_path"]:
            totals[key] += item[key]
        files.append(item)

    return {
        "file_count": len(files),
        "categories": sorted(categories),
        "totals": dict(totals),
        "files": files,
        "attachment_reference_keys_count": len(attachments_by_key),
        "duplicate_attachment_reference_keys": [
            {"key": key, "count": count}
            for key, count in attachments_by_key.items()
            if count > 1
        ][:100],
        "missing_local_path": missing_local_path,
    }


def inspect_category_mapping(path: Path) -> dict[str, Any]:
    data = read_json(path)
    mapping = data.get("mapping") if isinstance(data, dict) and isinstance(data.get("mapping"), dict) else {}
    thread_overrides = (
        data.get("_thread_overrides")
        if isinstance(data, dict) and isinstance(data.get("_thread_overrides"), dict)
        else {}
    )
    values = list(mapping.values())
    value_counts = Counter(values)
    return {
        "exists": path.exists(),
        "mapped_slug_count": len(mapping),
        "mapped_discourse_category_count": len(set(values)),
        "thread_override_count": len(thread_overrides),
        "mapping": mapping,
        "thread_overrides": thread_overrides,
        "many_to_one_discourse_categories": [
            {"discourse_category_id": key, "source_slug_count": count}
            for key, count in sorted(value_counts.items(), key=lambda x: (-x[1], x[0]))
            if count > 1
        ],
    }


def inspect_discourse_categories(path: Path) -> dict[str, Any]:
    data = read_json(path)
    categories = data if isinstance(data, list) else []
    ids = {item.get("id") for item in categories if isinstance(item, dict)}
    return {
        "exists": path.exists(),
        "category_count": len(categories),
        "ids": sorted(x for x in ids if x is not None),
        "categories": [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "slug": item.get("slug"),
                "parent_category_id": item.get("parent_category_id"),
                "topic_count": item.get("topic_count"),
                "post_count": item.get("post_count"),
            }
            for item in categories
            if isinstance(item, dict)
        ],
    }


def reconcile_categories(
    sqlite_data: dict[str, Any],
    thread_json_data: dict[str, Any],
    mapping_data: dict[str, Any],
    discourse_data: dict[str, Any],
) -> dict[str, Any]:
    sqlite_slugs = {item["slug"] for item in sqlite_data.get("categories", [])}
    json_slugs = set(thread_json_data.get("categories", []))
    mapping_slugs = set(mapping_data.get("mapping", {}).keys())
    discourse_ids = set(discourse_data.get("ids", []))
    mapped_ids = set(mapping_data.get("mapping", {}).values())

    return {
        "sqlite_category_count": len(sqlite_slugs),
        "thread_json_category_count": len(json_slugs),
        "mapping_slug_count": len(mapping_slugs),
        "sqlite_without_thread_json": sorted(sqlite_slugs - json_slugs),
        "thread_json_without_sqlite": sorted(json_slugs - sqlite_slugs),
        "sqlite_without_mapping": sorted(sqlite_slugs - mapping_slugs),
        "mapping_without_sqlite": sorted(mapping_slugs - sqlite_slugs),
        "mapped_discourse_ids_missing_from_discourse_categories": sorted(mapped_ids - discourse_ids),
        "discourse_ids_referenced_by_mapping_count": len(mapped_ids),
    }


def reconcile_attachments(
    root: Path,
    sqlite_data: dict[str, Any],
    thread_json_data: dict[str, Any],
) -> dict[str, Any]:
    sqlite_total = sqlite_data.get("counts", {}).get("attachments", 0)
    json_total = thread_json_data.get("totals", {}).get("attachments", 0)
    local_files = []
    for folder in (root / "output").glob("*"):
        if not folder.is_dir():
            continue
        for child_name in ["attachments", "images"]:
            child = folder / child_name
            if child.exists():
                local_files.extend(path for path in child.glob("*") if path.is_file())
    by_suffix = Counter(path.suffix.lower() or "<no extension>" for path in local_files)
    return {
        "sqlite_attachment_rows": sqlite_total,
        "json_attachment_references": json_total,
        "json_minus_sqlite": json_total - sqlite_total,
        "local_output_attachment_or_image_files": len(local_files),
        "local_files_by_extension": dict(sorted(by_suffix.items())),
        "sqlite_missing_local_path_count": sqlite_data.get("attachment_issues", {}).get("missing_local_path_count", 0),
        "sqlite_broken_local_path_count": sqlite_data.get("attachment_issues", {}).get("broken_local_path_count", 0),
        "json_missing_local_path_count": len(thread_json_data.get("missing_local_path", [])),
        "sqlite_missing_local_path": sqlite_data.get("attachment_issues", {}).get("missing_local_path", []),
        "json_missing_local_path": thread_json_data.get("missing_local_path", []),
    }


def inspect_quality(sqlite_data: dict[str, Any]) -> dict[str, Any]:
    db_path = sqlite_data.get("path")
    if not sqlite_data.get("exists"):
        return {"warnings": ["No SQLite database found."]}

    return {
        "duplicate_counts": sqlite_data.get("duplicate_counts", {}),
        "category_declared_thread_count_zero": sum(
            1
            for item in sqlite_data.get("categories", [])
            if item.get("declared_thread_count") == 0
        ),
        "categories_with_threads": sum(
            1
            for item in sqlite_data.get("categories", [])
            if item.get("actual_thread_count", 0) > 0
        ),
        "database_path": db_path,
    }


def build_recommendations(report: dict[str, Any]) -> list[str]:
    recs = []
    reconciliation = report.get("category_reconciliation", {})
    attachments = report.get("attachment_reconciliation", {})

    if reconciliation.get("sqlite_without_thread_json"):
        recs.append("Review SQLite categories without threads.json before Wix/Discourse comparison.")
    if reconciliation.get("sqlite_without_mapping"):
        recs.append("Add or explicitly dismiss SQLite categories missing from category_mapping.json.")
    if reconciliation.get("mapped_discourse_ids_missing_from_discourse_categories"):
        recs.append("Check mapped Discourse IDs that are not present in discourse_categories.json.")
    if attachments.get("sqlite_missing_local_path_count") or attachments.get("json_missing_local_path_count"):
        recs.append("Resolve attachment records without local_path or mark them as remote-only.")
    if attachments.get("json_minus_sqlite"):
        recs.append("Compare JSON attachment references against SQLite attachment rows.")
    if not recs:
        recs.append("Proceed to read-only Wix Groups verification.")
    return recs


def write_json_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def write_markdown_report(report: dict[str, Any], path: Path) -> None:
    lines = []
    key_files = report.get("key_files", {})
    sqlite_counts = report.get("sqlite", {}).get("counts", {})
    thread_totals = report.get("thread_json", {}).get("totals", {})
    category = report.get("category_reconciliation", {})
    attachments = report.get("attachment_reconciliation", {})
    quality = report.get("quality", {})

    lines.append("# Local Dataset Analysis")
    lines.append("")
    lines.append(f"Root: `{report.get('root')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- SQLite categories: **{sqlite_counts.get('categories', 0)}**")
    lines.append(f"- SQLite threads: **{sqlite_counts.get('threads', 0)}**")
    lines.append(f"- SQLite posts: **{sqlite_counts.get('posts', 0)}**")
    lines.append(f"- SQLite comments: **{sqlite_counts.get('comments', 0)}**")
    lines.append(f"- SQLite attachments: **{sqlite_counts.get('attachments', 0)}**")
    lines.append(f"- Thread JSON files: **{report.get('thread_json', {}).get('file_count', 0)}**")
    lines.append(f"- JSON threads/posts/comments: **{thread_totals.get('threads', 0)} / {thread_totals.get('posts', 0)} / {thread_totals.get('comments', 0)}**")
    lines.append(f"- JSON attachment references: **{thread_totals.get('attachments', 0)}**")
    lines.append("")

    lines.append("## Key Files")
    lines.append("")
    lines.append("| File | Status | Size |")
    lines.append("|---|---|---:|")
    for name, item in key_files.items():
        status = "found" if item.get("exists") else "missing"
        size = item.get("size_bytes")
        lines.append(f"| `{name}` | {status} | {size if size is not None else ''} |")
    lines.append("")

    lines.append("## Category Reconciliation")
    lines.append("")
    lines.append(f"- SQLite categories: **{category.get('sqlite_category_count', 0)}**")
    lines.append(f"- Thread JSON categories: **{category.get('thread_json_category_count', 0)}**")
    lines.append(f"- Mapping slugs: **{category.get('mapping_slug_count', 0)}**")
    lines.append(f"- Discourse IDs referenced by mapping: **{category.get('discourse_ids_referenced_by_mapping_count', 0)}**")
    append_list(lines, "SQLite categories without `threads.json`", category.get("sqlite_without_thread_json", []))
    append_list(lines, "`threads.json` categories absent from SQLite", category.get("thread_json_without_sqlite", []))
    append_list(lines, "SQLite categories missing from mapping", category.get("sqlite_without_mapping", []))
    append_list(lines, "Mapping slugs absent from SQLite", category.get("mapping_without_sqlite", []))
    append_list(lines, "Mapped Discourse IDs absent from `discourse_categories.json`", category.get("mapped_discourse_ids_missing_from_discourse_categories", []))
    lines.append("")

    lines.append("## Attachment Reconciliation")
    lines.append("")
    lines.append(f"- SQLite attachment rows: **{attachments.get('sqlite_attachment_rows', 0)}**")
    lines.append(f"- JSON attachment references: **{attachments.get('json_attachment_references', 0)}**")
    lines.append(f"- JSON minus SQLite: **{attachments.get('json_minus_sqlite', 0)}**")
    lines.append(f"- Local output attachment/image files: **{attachments.get('local_output_attachment_or_image_files', 0)}**")
    lines.append(f"- SQLite rows missing local_path: **{attachments.get('sqlite_missing_local_path_count', 0)}**")
    lines.append(f"- SQLite rows with broken local_path: **{attachments.get('sqlite_broken_local_path_count', 0)}**")
    lines.append(f"- JSON references missing local_path: **{attachments.get('json_missing_local_path_count', 0)}**")
    lines.append("")

    missing = attachments.get("sqlite_missing_local_path", [])
    if missing:
        lines.append("### SQLite Attachments Missing Local Path")
        lines.append("")
        lines.append("| Post ID | Filename | Type | URL |")
        lines.append("|---|---|---|---|")
        for item in missing[:100]:
            lines.append(
                f"| `{item.get('post_id') or ''}` | `{item.get('filename') or ''}` | "
                f"{item.get('file_type') or ''} | {item.get('url') or ''} |"
            )
        lines.append("")

    lines.append("## Quality Checks")
    lines.append("")
    duplicates = quality.get("duplicate_counts", {})
    lines.append(f"- Duplicate thread ids: **{duplicates.get('thread_ids', 0)}**")
    lines.append(f"- Duplicate thread URLs: **{duplicates.get('thread_urls', 0)}**")
    lines.append(f"- Duplicate post ids: **{duplicates.get('post_ids', 0)}**")
    lines.append(f"- Duplicate attachment ids: **{duplicates.get('attachment_ids', 0)}**")
    lines.append(f"- Categories where declared `thread_count` is zero: **{quality.get('category_declared_thread_count_zero', 0)}**")
    lines.append(f"- Categories with at least one thread: **{quality.get('categories_with_threads', 0)}**")
    lines.append("")

    lines.append("## Recommendations")
    lines.append("")
    for rec in report.get("recommendations", []):
        lines.append(f"- {rec}")
    lines.append("")

    if report.get("warnings"):
        lines.append("## Warnings")
        lines.append("")
        for warning in report["warnings"]:
            lines.append(f"- {warning}")
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def append_list(lines: list[str], title: str, values: list[Any]) -> None:
    lines.append("")
    lines.append(f"### {title}")
    lines.append("")
    if values:
        for value in values:
            lines.append(f"- `{value}`")
    else:
        lines.append("_None._")
