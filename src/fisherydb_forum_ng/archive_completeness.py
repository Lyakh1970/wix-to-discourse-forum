from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ERROR_MARKERS = [
    "Something Isn't Working",
    "Please verify you are a human",
    "Security check",
    "Wix Forum is no longer available",
]

SHORT_BODY_CHARS = 20


def read_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def body_text(row: sqlite3.Row | dict[str, Any]) -> str:
    content_text = row["content_text"] if row["content_text"] is not None else ""
    content_html = row["content_html"] if row["content_html"] is not None else ""
    return str(content_text or content_html or "")


def normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def run_archive_completeness_audit(root: Path) -> dict[str, Any]:
    report: dict[str, Any] = {
        "root": str(root),
        "audit_scope": {
            "uses_discourse_api": False,
            "checks_discourse_category_mapping_as_error": False,
            "primary_source": "output/forum_data.db",
            "secondary_source": "output/*/threads.json",
        },
        "warnings": [],
        "self_containment": {},
        "quality": {},
        "sqlite_json_consistency": {},
        "category_coverage": [],
        "practical_conclusion": {},
    }

    if not root.exists():
        report["warnings"].append(f"Root does not exist: {root}")
        return report

    db_path = root / "output" / "forum_data.db"
    if not db_path.exists():
        report["warnings"].append(f"SQLite database not found: {db_path}")
        return report

    db = load_sqlite_archive(db_path, root)
    thread_json = load_thread_json_archive(root)

    report["self_containment"] = build_self_containment(root, db, thread_json)
    report["quality"] = build_quality(db)
    report["sqlite_json_consistency"] = build_sqlite_json_consistency(db, thread_json)
    report["category_coverage"] = build_category_coverage(db, thread_json)
    report["practical_conclusion"] = build_practical_conclusion(report)
    return report


def load_sqlite_archive(db_path: Path, root: Path) -> dict[str, Any]:
    data: dict[str, Any] = {
        "path": str(db_path.relative_to(root)),
        "counts": {},
        "categories": {},
        "quality": {},
        "attachments": {},
    }
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        data["counts"] = {
            "categories": scalar(con, "select count(*) from categories"),
            "categories_with_threads": scalar(
                con,
                "select count(*) from (select category_slug from threads group by category_slug)",
            ),
            "threads": scalar(con, "select count(*) from threads"),
            "posts": scalar(con, "select count(*) from posts"),
            "original_posts": scalar(con, "select count(*) from posts where coalesce(is_comment, 0) = 0"),
            "comments": scalar(con, "select count(*) from posts where is_comment = 1"),
            "attachments": scalar(con, "select count(*) from attachments"),
            "images": scalar(con, "select count(*) from attachments where is_image = 1"),
        }

        data["categories"] = load_sqlite_categories(con)
        data["quality"] = load_sqlite_quality(con)
        data["attachments"] = load_sqlite_attachment_details(con, root)
        return data
    finally:
        con.close()


def scalar(con: sqlite3.Connection, query: str, params: tuple[Any, ...] = ()) -> int:
    return int(con.execute(query, params).fetchone()[0])


def load_sqlite_categories(con: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    categories: dict[str, dict[str, Any]] = {}
    for row in con.execute(
        """
        select
            c.slug,
            c.name,
            coalesce(t_stats.threads, 0) as threads,
            coalesce(p_stats.posts, 0) as posts,
            coalesce(p_stats.comments, 0) as comments,
            coalesce(a_stats.attachments, 0) as attachments,
            coalesce(a_stats.images, 0) as images
        from categories c
        left join (
            select category_slug, count(*) as threads
            from threads
            group by category_slug
        ) t_stats on t_stats.category_slug = c.slug
        left join (
            select
                t.category_slug,
                count(p.id) as posts,
                sum(case when p.is_comment = 1 then 1 else 0 end) as comments
            from threads t
            left join posts p on p.thread_id = t.id
            group by t.category_slug
        ) p_stats on p_stats.category_slug = c.slug
        left join (
            select
                t.category_slug,
                count(a.id) as attachments,
                sum(case when a.is_image = 1 then 1 else 0 end) as images
            from threads t
            left join posts p on p.thread_id = t.id
            left join attachments a on a.post_id = p.id
            group by t.category_slug
        ) a_stats on a_stats.category_slug = c.slug
        order by c.slug
        """
    ):
        posts = int(row["posts"] or 0)
        comments = int(row["comments"] or 0)
        categories[row["slug"]] = {
            "slug": row["slug"],
            "name": row["name"],
            "threads": int(row["threads"] or 0),
            "posts": posts,
            "original_posts": posts - comments,
            "comments": comments,
            "attachments": int(row["attachments"] or 0),
            "images": int(row["images"] or 0),
        }
    return categories


def load_sqlite_quality(con: sqlite3.Connection) -> dict[str, Any]:
    suspicious_posts = []
    error_marker_posts = []
    for row in con.execute(
        """
        select
            p.id,
            p.thread_id,
            p.author_username,
            p.created_at,
            p.content_text,
            p.content_html,
            p.is_comment,
            t.title,
            t.category_slug
        from posts p
        left join threads t on t.id = p.thread_id
        order by p.thread_id, p.id
        """
    ):
        text = normalize_spaces(body_text(row))
        if 0 < len(text) < SHORT_BODY_CHARS:
            suspicious_posts.append(
                {
                    "post_id": row["id"],
                    "thread_id": row["thread_id"],
                    "category_slug": row["category_slug"],
                    "is_comment": bool(row["is_comment"]),
                    "body_length": len(text),
                    "body_preview": text[:120],
                }
            )
        hits = [marker for marker in ERROR_MARKERS if marker.lower() in text.lower()]
        if hits:
            error_marker_posts.append(
                {
                    "post_id": row["id"],
                    "thread_id": row["thread_id"],
                    "category_slug": row["category_slug"],
                    "is_comment": bool(row["is_comment"]),
                    "markers": hits,
                    "body_preview": text[:180],
                }
            )

    return {
        "threads_missing_title": scalar(
            con, "select count(*) from threads where coalesce(trim(title), '') = ''"
        ),
        "threads_missing_author": scalar(
            con, "select count(*) from threads where coalesce(trim(author_username), '') = ''"
        ),
        "threads_missing_date": scalar(
            con, "select count(*) from threads where coalesce(trim(created_at), '') = ''"
        ),
        "threads_missing_category": scalar(
            con, "select count(*) from threads where coalesce(trim(category_slug), '') = ''"
        ),
        "posts_missing_body": scalar(
            con,
            "select count(*) from posts where coalesce(trim(content_text), '') = '' "
            "and coalesce(trim(content_html), '') = ''",
        ),
        "posts_missing_author": scalar(
            con, "select count(*) from posts where coalesce(trim(author_username), '') = ''"
        ),
        "posts_missing_date": scalar(
            con, "select count(*) from posts where coalesce(trim(created_at), '') = ''"
        ),
        "suspicious_short_body_count": len(suspicious_posts),
        "suspicious_short_body_sample": suspicious_posts[:100],
        "error_marker_post_count": len(error_marker_posts),
        "error_marker_post_sample": error_marker_posts[:100],
    }


def load_sqlite_attachment_details(con: sqlite3.Connection, root: Path) -> dict[str, Any]:
    missing_local_path = []
    broken_local_path = []
    existing_local_paths = set()
    referenced_local_paths = set()

    for row in con.execute(
        """
        select id, post_id, url, filename, file_type, local_path, is_image
        from attachments
        order by post_id, filename
        """
    ):
        item = dict(row)
        local_path = item.get("local_path")
        if is_blank(local_path):
            missing_local_path.append(item)
            continue
        referenced_local_paths.add(local_path)
        if (root / local_path).exists():
            existing_local_paths.add(local_path)
        else:
            broken_local_path.append(item)

    return {
        "referenced_local_path_count": len(referenced_local_paths),
        "existing_referenced_local_file_count": len(existing_local_paths),
        "missing_local_path_count": len(missing_local_path),
        "missing_local_path": missing_local_path,
        "broken_local_path_count": len(broken_local_path),
        "broken_local_path": broken_local_path,
    }


def load_thread_json_archive(root: Path) -> dict[str, Any]:
    data: dict[str, Any] = {
        "file_count": 0,
        "categories": {},
        "counts": Counter(),
        "attachment_references": [],
    }

    for path in sorted((root / "output").glob("*/threads.json")):
        raw = read_json(path)
        if not isinstance(raw, dict) or not isinstance(raw.get("threads"), list):
            continue

        category = raw.get("category") or path.parent.name
        category_counts = Counter()
        data["file_count"] += 1

        for thread in raw["threads"]:
            if not isinstance(thread, dict):
                continue
            category_counts["threads"] += 1
            data["counts"]["threads"] += 1
            posts = thread.get("posts") if isinstance(thread.get("posts"), list) else []
            for post in posts:
                if not isinstance(post, dict):
                    continue
                category_counts["posts"] += 1
                data["counts"]["posts"] += 1
                if post.get("is_comment"):
                    category_counts["comments"] += 1
                    data["counts"]["comments"] += 1
                else:
                    category_counts["original_posts"] += 1
                    data["counts"]["original_posts"] += 1

                for key in ["attachments", "images"]:
                    values = post.get(key) if isinstance(post.get(key), list) else []
                    category_counts["attachments"] += len(values)
                    data["counts"]["attachments"] += len(values)
                    if key == "images":
                        category_counts["images"] += len(values)
                        data["counts"]["images"] += len(values)
                    for attachment in values:
                        if not isinstance(attachment, dict):
                            continue
                        data["attachment_references"].append(
                            {
                                "category_slug": category,
                                "thread_id": thread.get("id"),
                                "post_id": post.get("id"),
                                "filename": attachment.get("filename"),
                                "url": attachment.get("url"),
                                "local_path": attachment.get("local_path"),
                                "is_image": key == "images",
                            }
                        )

        data["categories"][category] = {
            "slug": category,
            "path": str(path.relative_to(root)),
            **dict(category_counts),
        }

    data["counts"] = dict(data["counts"])
    return data


def build_self_containment(root: Path, db: dict[str, Any], thread_json: dict[str, Any]) -> dict[str, Any]:
    physical_files = []
    for folder in (root / "output").glob("*"):
        if not folder.is_dir():
            continue
        for child_name in ["attachments", "images"]:
            child = folder / child_name
            if child.exists():
                physical_files.extend(path for path in child.glob("*") if path.is_file())

    by_extension = Counter(path.suffix.lower() or "<no extension>" for path in physical_files)
    counts = db["counts"]
    return {
        "sqlite_categories": counts.get("categories", 0),
        "sqlite_categories_with_threads": counts.get("categories_with_threads", 0),
        "thread_json_categories": len(thread_json.get("categories", {})),
        "sqlite_threads": counts.get("threads", 0),
        "sqlite_posts": counts.get("posts", 0),
        "sqlite_original_posts": counts.get("original_posts", 0),
        "sqlite_comments": counts.get("comments", 0),
        "sqlite_attachments": counts.get("attachments", 0),
        "sqlite_images": counts.get("images", 0),
        "referenced_local_files_present": db.get("attachments", {}).get("existing_referenced_local_file_count", 0),
        "physical_local_attachment_or_image_files": len(physical_files),
        "physical_local_files_by_extension": dict(sorted(by_extension.items())),
    }


def build_quality(db: dict[str, Any]) -> dict[str, Any]:
    quality = dict(db.get("quality", {}))
    attachment = db.get("attachments", {})
    quality.update(
        {
            "attachments_missing_local_path": attachment.get("missing_local_path_count", 0),
            "attachments_broken_local_path": attachment.get("broken_local_path_count", 0),
            "attachments_missing_local_path_sample": attachment.get("missing_local_path", [])[:100],
            "attachments_broken_local_path_sample": attachment.get("broken_local_path", [])[:100],
        }
    )
    blocking = []
    review = []
    if quality["threads_missing_title"] or quality["threads_missing_category"]:
        blocking.append("Some threads miss title or category.")
    if quality["posts_missing_body"]:
        blocking.append("Some posts/comments have no body.")
    if quality["attachments_broken_local_path"]:
        blocking.append("Some attachment local_path values point to missing files.")
    if quality["attachments_missing_local_path"]:
        review.append("Some attachment records have no local_path and may be remote-only embeds/previews.")
    if quality["suspicious_short_body_count"]:
        review.append("Some posts/comments have suspiciously short bodies.")
    if quality["error_marker_post_count"]:
        review.append("Some posts/comments contain known Wix/security error markers.")
    quality["blocking_issues"] = blocking
    quality["review_issues"] = review
    return quality


def build_sqlite_json_consistency(db: dict[str, Any], thread_json: dict[str, Any]) -> dict[str, Any]:
    db_counts = db["counts"]
    json_counts = thread_json["counts"]
    db_categories = db["categories"]
    json_categories = thread_json["categories"]
    sqlite_slugs = set(db_categories)
    json_slugs = set(json_categories)
    db_with_threads = {
        slug
        for slug, item in db_categories.items()
        if item.get("threads", 0) > 0
    }

    return {
        "sqlite_threads": db_counts.get("threads", 0),
        "json_threads": json_counts.get("threads", 0),
        "sqlite_posts": db_counts.get("posts", 0),
        "json_posts": json_counts.get("posts", 0),
        "sqlite_comments": db_counts.get("comments", 0),
        "json_comments": json_counts.get("comments", 0),
        "sqlite_attachment_references": db_counts.get("attachments", 0),
        "json_attachment_references": json_counts.get("attachments", 0),
        "thread_delta_json_minus_sqlite": json_counts.get("threads", 0) - db_counts.get("threads", 0),
        "post_delta_json_minus_sqlite": json_counts.get("posts", 0) - db_counts.get("posts", 0),
        "comment_delta_json_minus_sqlite": json_counts.get("comments", 0) - db_counts.get("comments", 0),
        "attachment_delta_json_minus_sqlite": json_counts.get("attachments", 0) - db_counts.get("attachments", 0),
        "sqlite_categories_without_threads_json": sorted(sqlite_slugs - json_slugs),
        "sqlite_categories_with_threads_without_threads_json": sorted(db_with_threads - json_slugs),
        "thread_json_categories_missing_from_sqlite": sorted(json_slugs - sqlite_slugs),
    }


def build_category_coverage(db: dict[str, Any], thread_json: dict[str, Any]) -> list[dict[str, Any]]:
    db_categories = db["categories"]
    json_categories = thread_json["categories"]
    all_slugs = sorted(set(db_categories) | set(json_categories))
    coverage = []

    for slug in all_slugs:
        db_item = db_categories.get(slug)
        json_item = json_categories.get(slug)
        has_db = db_item is not None
        has_json = json_item is not None
        db_threads = int((db_item or {}).get("threads", 0))
        json_threads = int((json_item or {}).get("threads", 0))

        status = "OK"
        reasons = []
        if has_json and not has_db:
            status = "JSON_ONLY"
            reasons.append("threads.json category is absent from SQLite")
        elif has_db and db_threads == 0 and not has_json:
            status = "DB_ONLY_EMPTY"
            reasons.append("SQLite category is empty and has no threads.json")
        elif has_db and db_threads == 0 and has_json:
            status = "EMPTY_CATEGORY"
            reasons.append("SQLite category has no threads")
        elif has_db and db_threads > 0 and not has_json:
            status = "DB_HAS_THREADS_NO_JSON"
            reasons.append("SQLite has threads but category threads.json is missing")
        elif has_db and has_json:
            if db_threads != json_threads:
                status = "NEEDS_REVIEW"
                reasons.append("SQLite and JSON thread counts differ")
            else:
                db_posts = int((db_item or {}).get("posts", 0))
                json_posts = int((json_item or {}).get("posts", 0))
                db_comments = int((db_item or {}).get("comments", 0))
                json_comments = int((json_item or {}).get("comments", 0))
                if db_posts != json_posts or db_comments != json_comments:
                    status = "NEEDS_REVIEW"
                    reasons.append("SQLite and JSON post/comment counts differ")

        source = db_item or json_item or {"slug": slug}
        coverage.append(
            {
                "slug": slug,
                "name": (db_item or {}).get("name") or (json_item or {}).get("slug") or slug,
                "threads": db_threads if has_db else json_threads,
                "posts": int((db_item or {}).get("posts", (json_item or {}).get("posts", 0))),
                "comments": int((db_item or {}).get("comments", (json_item or {}).get("comments", 0))),
                "attachments": int((db_item or {}).get("attachments", (json_item or {}).get("attachments", 0))),
                "images": int((db_item or {}).get("images", (json_item or {}).get("images", 0))),
                "has_threads_json": has_json,
                "status": status,
                "status_reasons": reasons,
            }
        )

    return coverage


def build_practical_conclusion(report: dict[str, Any]) -> dict[str, Any]:
    quality = report["quality"]
    consistency = report["sqlite_json_consistency"]
    category_coverage = report["category_coverage"]

    db_has_threads_no_json = [
        item for item in category_coverage if item["status"] == "DB_HAS_THREADS_NO_JSON"
    ]
    json_only = [item for item in category_coverage if item["status"] == "JSON_ONLY"]
    needs_review = [item for item in category_coverage if item["status"] == "NEEDS_REVIEW"]

    blocking = list(quality.get("blocking_issues", []))
    if db_has_threads_no_json:
        blocking.append("Some SQLite categories with threads have no corresponding threads.json.")
    if json_only:
        blocking.append("Some threads.json categories are absent from SQLite.")

    non_blocking = list(quality.get("review_issues", []))
    if consistency.get("attachment_delta_json_minus_sqlite"):
        non_blocking.append("SQLite and JSON attachment reference counts differ.")
    empty_db_only = [
        item["slug"]
        for item in category_coverage
        if item["status"] == "DB_ONLY_EMPTY"
    ]
    if empty_db_only:
        non_blocking.append("Some SQLite-only categories are empty and can be treated as structural remnants.")
    if needs_review:
        non_blocking.append("Some categories have SQLite/JSON count mismatches and need manual review.")

    usable = not blocking
    wix_next = usable
    wix_checks = [
        "Categories or topics involved in attachment count mismatches.",
        "Posts with missing local_path attachments that may be remote-only embeds.",
    ]
    if db_has_threads_no_json or json_only or needs_review:
        wix_checks.append("Any category marked DB_HAS_THREADS_NO_JSON, JSON_ONLY, or NEEDS_REVIEW.")
    else:
        wix_checks.append("Representative high-volume categories to validate archive completeness against visible Wix Groups.")

    return {
        "can_use_local_archive_as_working_source": usable,
        "blocking_import_issues": blocking,
        "non_blocking_review_issues": non_blocking,
        "can_proceed_to_read_only_wix_groups_check": wix_next,
        "wix_groups_should_check": wix_checks,
        "summary": (
            "The local archive is a usable working source for recovery/re-import planning."
            if usable
            else "The local archive needs blocking issues resolved before recovery/re-import planning."
        ),
    }


def write_json_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def write_markdown_report(report: dict[str, Any], path: Path) -> None:
    lines = []
    self_containment = report.get("self_containment", {})
    quality = report.get("quality", {})
    consistency = report.get("sqlite_json_consistency", {})
    conclusion = report.get("practical_conclusion", {})

    lines.append("# Archive Completeness Audit")
    lines.append("")
    lines.append(f"Root: `{report.get('root')}`")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("- Discourse API: not used")
    lines.append("- Discourse category mapping correctness: not checked as an error")
    lines.append("- Primary source: `output/forum_data.db`")
    lines.append("- Secondary source: `output/*/threads.json`")
    lines.append("")

    lines.append("## A. Archive Self-Containment")
    lines.append("")
    rows = [
        ("SQLite categories", self_containment.get("sqlite_categories", 0)),
        ("SQLite categories with threads", self_containment.get("sqlite_categories_with_threads", 0)),
        ("Categories with threads.json", self_containment.get("thread_json_categories", 0)),
        ("Threads", self_containment.get("sqlite_threads", 0)),
        ("Posts", self_containment.get("sqlite_posts", 0)),
        ("Original posts", self_containment.get("sqlite_original_posts", 0)),
        ("Comments", self_containment.get("sqlite_comments", 0)),
        ("Attachments", self_containment.get("sqlite_attachments", 0)),
        ("Images", self_containment.get("sqlite_images", 0)),
        ("Referenced local files present", self_containment.get("referenced_local_files_present", 0)),
        ("Physical local attachment/image files", self_containment.get("physical_local_attachment_or_image_files", 0)),
    ]
    append_kv_table(lines, rows)

    lines.append("## B. Data Quality")
    lines.append("")
    quality_rows = [
        ("Threads without title", quality.get("threads_missing_title", 0)),
        ("Threads without author", quality.get("threads_missing_author", 0)),
        ("Threads without date", quality.get("threads_missing_date", 0)),
        ("Threads without category", quality.get("threads_missing_category", 0)),
        ("Posts/comments without body", quality.get("posts_missing_body", 0)),
        ("Posts/comments without author", quality.get("posts_missing_author", 0)),
        ("Posts/comments without date", quality.get("posts_missing_date", 0)),
        ("Attachments without local_path", quality.get("attachments_missing_local_path", 0)),
        ("Attachments with broken local_path", quality.get("attachments_broken_local_path", 0)),
        (f"Suspicious short bodies (<{SHORT_BODY_CHARS} chars)", quality.get("suspicious_short_body_count", 0)),
        ("Bodies containing Wix/security error markers", quality.get("error_marker_post_count", 0)),
    ]
    append_kv_table(lines, quality_rows)
    append_sample_table(
        lines,
        "Attachments Without Local Path",
        quality.get("attachments_missing_local_path_sample", []),
        ["post_id", "filename", "file_type", "url"],
    )
    append_sample_table(
        lines,
        "Suspicious Short Body Sample",
        quality.get("suspicious_short_body_sample", []),
        ["post_id", "thread_id", "category_slug", "body_length", "body_preview"],
    )
    append_sample_table(
        lines,
        "Error Marker Body Sample",
        quality.get("error_marker_post_sample", []),
        ["post_id", "thread_id", "category_slug", "markers", "body_preview"],
    )

    lines.append("## C. SQLite vs JSON Consistency")
    lines.append("")
    consistency_rows = [
        ("Threads SQLite / JSON", f"{consistency.get('sqlite_threads', 0)} / {consistency.get('json_threads', 0)}"),
        ("Posts SQLite / JSON", f"{consistency.get('sqlite_posts', 0)} / {consistency.get('json_posts', 0)}"),
        ("Comments SQLite / JSON", f"{consistency.get('sqlite_comments', 0)} / {consistency.get('json_comments', 0)}"),
        ("Attachment refs SQLite / JSON", f"{consistency.get('sqlite_attachment_references', 0)} / {consistency.get('json_attachment_references', 0)}"),
        ("Attachment delta JSON - SQLite", consistency.get("attachment_delta_json_minus_sqlite", 0)),
    ]
    append_kv_table(lines, consistency_rows)
    append_list(lines, "SQLite categories without threads.json", consistency.get("sqlite_categories_without_threads_json", []))
    append_list(lines, "SQLite categories with threads but without threads.json", consistency.get("sqlite_categories_with_threads_without_threads_json", []))
    append_list(lines, "threads.json categories missing from SQLite", consistency.get("thread_json_categories_missing_from_sqlite", []))

    lines.append("## D. Category Coverage")
    lines.append("")
    lines.append("| Slug | Name | Threads | Posts | Comments | Attachments | threads.json | Status |")
    lines.append("|---|---|---:|---:|---:|---:|---|---|")
    for item in report.get("category_coverage", []):
        lines.append(
            f"| `{item['slug']}` | {escape_cell(item.get('name', ''))} | "
            f"{item.get('threads', 0)} | {item.get('posts', 0)} | {item.get('comments', 0)} | "
            f"{item.get('attachments', 0)} | {'yes' if item.get('has_threads_json') else 'no'} | "
            f"{item.get('status')} |"
        )
    lines.append("")

    lines.append("## E. Practical Conclusion")
    lines.append("")
    lines.append(f"- Can use local archive as working source: **{yes_no(conclusion.get('can_use_local_archive_as_working_source'))}**")
    append_list(lines, "Blocking import issues", conclusion.get("blocking_import_issues", []))
    append_list(lines, "Non-blocking review issues", conclusion.get("non_blocking_review_issues", []))
    lines.append(f"- Can proceed to read-only Wix Groups check: **{yes_no(conclusion.get('can_proceed_to_read_only_wix_groups_check'))}**")
    append_list(lines, "Data to additionally verify via Wix Groups", conclusion.get("wix_groups_should_check", []))
    lines.append("")

    if report.get("warnings"):
        lines.append("## Warnings")
        lines.append("")
        for warning in report["warnings"]:
            lines.append(f"- {warning}")
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_summary_report(report: dict[str, Any], path: Path) -> None:
    self_containment = report.get("self_containment", {})
    quality = report.get("quality", {})
    consistency = report.get("sqlite_json_consistency", {})
    conclusion = report.get("practical_conclusion", {})

    lines = [
        "# Archive Completeness Summary",
        "",
        f"Archive usable as working source: **{yes_no(conclusion.get('can_use_local_archive_as_working_source'))}**",
        "",
        "The audit treats the local December archive as an independent source. It does not use Discourse and does not treat old-to-new category mapping differences as primary errors.",
        "",
        "## Core Counts",
        "",
        f"- Categories: **{self_containment.get('sqlite_categories', 0)}**",
        f"- Categories with threads: **{self_containment.get('sqlite_categories_with_threads', 0)}**",
        f"- Categories with threads.json: **{self_containment.get('thread_json_categories', 0)}**",
        f"- Threads: **{self_containment.get('sqlite_threads', 0)}**",
        f"- Posts: **{self_containment.get('sqlite_posts', 0)}**",
        f"- Original posts: **{self_containment.get('sqlite_original_posts', 0)}**",
        f"- Comments: **{self_containment.get('sqlite_comments', 0)}**",
        f"- Attachments/images rows: **{self_containment.get('sqlite_attachments', 0)} / {self_containment.get('sqlite_images', 0)}**",
        f"- Referenced local files present: **{self_containment.get('referenced_local_files_present', 0)}**",
        "",
        "## Blocking Issues",
        "",
    ]
    append_plain_list(lines, conclusion.get("blocking_import_issues", []))
    lines.extend(
        [
            "",
            "## Non-Blocking Review Items",
            "",
        ]
    )
    append_plain_list(lines, conclusion.get("non_blocking_review_issues", []))
    lines.extend(
        [
            "",
            "## Important Quality Signals",
            "",
            f"- Posts/comments without body: **{quality.get('posts_missing_body', 0)}**",
            f"- Attachments without local_path: **{quality.get('attachments_missing_local_path', 0)}**",
            f"- Attachments with broken local_path: **{quality.get('attachments_broken_local_path', 0)}**",
            f"- Suspicious short bodies: **{quality.get('suspicious_short_body_count', 0)}**",
            f"- Error-marker bodies: **{quality.get('error_marker_post_count', 0)}**",
            f"- SQLite/JSON attachment delta: **{consistency.get('attachment_delta_json_minus_sqlite', 0)}**",
            "",
            "## Wix Groups Next",
            "",
            f"Proceed to read-only Wix Groups verification: **{yes_no(conclusion.get('can_proceed_to_read_only_wix_groups_check'))}**",
            "",
        ]
    )
    append_plain_list(lines, conclusion.get("wix_groups_should_check", []))
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def append_kv_table(lines: list[str], rows: list[tuple[str, Any]]) -> None:
    lines.append("| Check | Value |")
    lines.append("|---|---:|")
    for key, value in rows:
        lines.append(f"| {escape_cell(key)} | {value} |")
    lines.append("")


def append_sample_table(
    lines: list[str],
    title: str,
    rows: list[dict[str, Any]],
    columns: list[str],
) -> None:
    if not rows:
        return
    lines.append(f"### {title}")
    lines.append("")
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("|" + "|".join("---" for _ in columns) + "|")
    for row in rows[:25]:
        values = [escape_cell(row.get(column, "")) for column in columns]
        lines.append("| " + " | ".join(values) + " |")
    lines.append("")


def append_list(lines: list[str], title: str, values: list[Any]) -> None:
    lines.append("")
    lines.append(f"### {title}")
    lines.append("")
    append_plain_list(lines, values)


def append_plain_list(lines: list[str], values: list[Any]) -> None:
    if not values:
        lines.append("_None._")
        return
    for value in values:
        lines.append(f"- `{value}`" if isinstance(value, str) else f"- `{json.dumps(value, ensure_ascii=False)}`")


def escape_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ")


def yes_no(value: Any) -> str:
    return "yes" if bool(value) else "no"
