from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


def normalize_text(text: str | None) -> str:
    text = (text or "").lower().replace("ё", "е")
    text = re.sub(r"[^\w\s\-/+.]+", " ", text, flags=re.U)
    return re.sub(r"\s+", " ", text).strip()


def normalize_filename(text: str | None) -> str:
    text = (text or "").replace("\\", "/").split("/")[-1].lower()
    return re.sub(r"\s+", " ", text).strip()


def body_hash(text: str | None) -> str | None:
    normalized = normalize_text(text)
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def similarity(a: str | None, b: str | None) -> float:
    na = normalize_text(a)
    nb = normalize_text(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def run_snapshot_vs_december(snapshot_db: Path, december_db: Path) -> dict[str, Any]:
    snap = sqlite3.connect(snapshot_db)
    snap.row_factory = sqlite3.Row
    dec = sqlite3.connect(december_db)
    dec.row_factory = sqlite3.Row
    snap_discussions = [dict(row) for row in snap.execute("SELECT * FROM discussions")]
    dec_threads = _load_december_threads(dec)
    discussion_results = []
    matched_thread_ids: set[str] = set()
    for discussion in snap_discussions:
        result = _match_discussion(discussion, dec_threads)
        discussion_results.append(result)
        if result.get("best_match"):
            matched_thread_ids.add(result["best_match"]["thread_id"])
    only_december = [thread for thread in dec_threads if thread["thread_id"] not in matched_thread_ids]

    comment_results = _compare_comments(snap, dec, discussion_results)
    attachment_results = _compare_attachments(snap, dec, discussion_results)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "read_only_wix_groups_snapshot_vs_december_archive",
        "inputs": {
            "snapshot_db": str(snapshot_db),
            "december_db": str(december_db),
        },
        "summary": {
            "groups_checked": snap.execute("SELECT COUNT(*) FROM groups").fetchone()[0],
            "public_groups": _count_group_status(snap, "PUBLIC"),
            "login_required_groups": _count_group_status(snap, "LOGIN_REQUIRED"),
            "broken_not_found_groups": _count_group_status(snap, "BROKEN") + _count_group_status(snap, "NOT_FOUND"),
            "discussions_in_wix_snapshot": len(snap_discussions),
            "discussions_in_december_archive": len(dec_threads),
            "discussions_missing_in_december": sum(1 for item in discussion_results if item["status"] == "MISSING_IN_DECEMBER"),
            "comments_in_wix_snapshot": snap.execute("SELECT COUNT(*) FROM comments").fetchone()[0],
            "comments_in_december_archive": dec.execute("SELECT COUNT(*) FROM posts WHERE is_comment = 1").fetchone()[0],
            "comments_missing_in_december": sum(1 for item in comment_results if item["status"] == "COMMENT_MISSING_IN_DECEMBER"),
            "attachments_in_wix_snapshot": snap.execute("SELECT COUNT(*) FROM attachments").fetchone()[0],
            "attachments_in_december_archive": dec.execute("SELECT COUNT(*) FROM attachments").fetchone()[0],
            "attachments_missing_in_december": sum(1 for item in attachment_results if item["status"] == "ATTACHMENT_MISSING_IN_DECEMBER"),
            "attachments_downloaded_during_snapshot": snap.execute("SELECT COUNT(*) FROM attachments WHERE status = 'DOWNLOADED'").fetchone()[0],
            "attachments_remote_only": snap.execute("SELECT COUNT(*) FROM attachments WHERE status = 'REMOTE_ONLY'").fetchone()[0],
            "discussion_status_counts": dict(Counter(item["status"] for item in discussion_results)),
            "comment_status_counts": dict(Counter(item["status"] for item in comment_results)),
            "attachment_status_counts": dict(Counter(item["status"] for item in attachment_results)),
            "groups_with_worst_coverage": _worst_groups(discussion_results),
            "topics_with_missing_comments": [item for item in comment_results if item["status"] == "COMMENT_MISSING_IN_DECEMBER"][:50],
            "topics_with_missing_attachments": [item for item in attachment_results if item["status"] == "ATTACHMENT_MISSING_IN_DECEMBER"][:50],
        },
        "limitations": [
            "Absence from current Wix Groups is not proof that the December archive is wrong; Groups may have changed.",
            "The snapshot parser is verification-oriented and may need selector tuning after authenticated test runs.",
            "Remote-only attachments are compared by URL/filename only unless media downloading is enabled later.",
        ],
        "discussion_results": discussion_results,
        "december_missing_in_wix_groups": only_december,
        "comment_results": comment_results,
        "attachment_results": attachment_results,
    }
    snap.close()
    dec.close()
    return report


def write_compare_reports(report: dict[str, Any], reports_dir: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "wix_groups_vs_december_comparison.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_summary(report, reports_dir / "wix_groups_vs_december_summary.md")
    _write_comparison(report, reports_dir / "wix_groups_vs_december_comparison.md")
    _write_missing_in_december(report, reports_dir / "wix_groups_missing_in_december.md")
    _write_december_only(report, reports_dir / "december_missing_in_wix_groups.md")
    _write_comment_coverage(report, reports_dir / "comment_coverage_check.md")
    _write_attachment_coverage(report, reports_dir / "attachment_coverage_check.md")


def _load_december_threads(con: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = con.execute(
        """
        SELECT t.id AS thread_id, t.category_slug, c.name AS category_name, t.title, t.author_username,
               t.created_at, t.url, p.content_text AS body_text
        FROM threads t
        LEFT JOIN categories c ON c.slug = t.category_slug
        LEFT JOIN posts p ON p.thread_id = t.id AND p.is_comment = 0
        ORDER BY t.category_slug, t.id
        """
    ).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        item["normalized_title"] = normalize_text(item.get("title"))
        item["body_hash"] = body_hash(item.get("body_text"))
        out.append(item)
    return out


def _match_discussion(discussion: dict[str, Any], dec_threads: list[dict[str, Any]]) -> dict[str, Any]:
    title_norm = normalize_text(discussion.get("title"))
    group_slug = discussion.get("group_slug")
    candidates = []
    for thread in dec_threads:
        title_sim = similarity(title_norm, thread.get("normalized_title"))
        slug_bonus = 0.18 if group_slug and group_slug == thread.get("category_slug") else 0.0
        body_sim = similarity(discussion.get("body_text"), thread.get("body_text"))
        score = max(title_sim, (title_sim * 0.75) + (body_sim * 0.25)) + slug_bonus
        if score >= 0.45:
            candidates.append(
                {
                    "thread_id": thread["thread_id"],
                    "title": thread["title"],
                    "category_slug": thread["category_slug"],
                    "score": round(score, 3),
                    "title_similarity": round(title_sim, 3),
                    "body_similarity": round(body_sim, 3),
                }
            )
    candidates.sort(key=lambda item: item["score"], reverse=True)
    best = candidates[0] if candidates else None
    if best and (best["score"] >= 1.0 or best["title_similarity"] >= 0.96):
        status = "FOUND_IN_DECEMBER"
    elif best and best["score"] >= 0.74:
        status = "PROBABLY_FOUND_IN_DECEMBER"
    elif best:
        status = "NEEDS_REVIEW"
    else:
        status = "MISSING_IN_DECEMBER"
    return {
        "discussion_id": discussion["discussion_id"],
        "group_slug": group_slug,
        "title": discussion.get("title"),
        "discussion_url": discussion.get("discussion_url"),
        "status": status,
        "best_match": best,
        "top_candidates": candidates[:3],
    }


def _compare_comments(snap: sqlite3.Connection, dec: sqlite3.Connection, discussion_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    match_by_discussion = {item["discussion_id"]: item.get("best_match") for item in discussion_results if item.get("best_match")}
    results = []
    for comment in snap.execute("SELECT * FROM comments"):
        match = match_by_discussion.get(comment["discussion_id"])
        if not match:
            results.append(_comment_result(comment, "COMMENT_MISSING_IN_DECEMBER", None, "parent discussion not matched"))
            continue
        dec_comments = dec.execute(
            "SELECT id, author_username, created_at, content_text FROM posts WHERE thread_id = ? AND is_comment = 1",
            (match["thread_id"],),
        ).fetchall()
        best = None
        for dec_comment in dec_comments:
            sim = similarity(comment["body_text"], dec_comment["content_text"])
            if best is None or sim > best["body_similarity"]:
                best = {"post_id": dec_comment["id"], "body_similarity": round(sim, 3), "author": dec_comment["author_username"]}
        if best and best["body_similarity"] >= 0.92:
            status = "COMMENT_FOUND"
        elif best and best["body_similarity"] >= 0.72:
            status = "COMMENT_PROBABLY_FOUND"
        elif best:
            status = "COMMENT_NEEDS_REVIEW"
        else:
            status = "COMMENT_MISSING_IN_DECEMBER"
        results.append(_comment_result(comment, status, best, "matched by parent discussion/body similarity"))
    return results


def _compare_attachments(snap: sqlite3.Connection, dec: sqlite3.Connection, discussion_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    match_by_discussion = {item["discussion_id"]: item.get("best_match") for item in discussion_results if item.get("best_match")}
    results = []
    for att in snap.execute("SELECT * FROM attachments"):
        match = match_by_discussion.get(att["discussion_id"])
        if att["status"] == "REMOTE_ONLY" and not att["filename"]:
            results.append(_attachment_result(att, "REMOTE_ONLY_UNVERIFIED", None, "remote URL without filename"))
            continue
        if not match:
            results.append(_attachment_result(att, "ATTACHMENT_MISSING_IN_DECEMBER", None, "parent discussion not matched"))
            continue
        dec_attachments = dec.execute(
            """
            SELECT a.id, a.filename, a.url, a.local_path
            FROM attachments a
            JOIN posts p ON p.id = a.post_id
            WHERE p.thread_id = ?
            """,
            (match["thread_id"],),
        ).fetchall()
        filename = normalize_filename(att["filename"] or att["url"])
        best = None
        for dec_att in dec_attachments:
            dec_name = normalize_filename(dec_att["filename"] or dec_att["local_path"] or dec_att["url"])
            score = 1.0 if filename and filename == dec_name else similarity(filename, dec_name)
            if best is None or score > best["score"]:
                best = {"attachment_id": dec_att["id"], "filename": dec_name, "score": round(score, 3)}
        if best and best["score"] >= 0.98:
            status = "ATTACHMENT_FOUND"
        elif best and best["score"] >= 0.72:
            status = "ATTACHMENT_PROBABLY_FOUND"
        elif att["status"] == "REMOTE_ONLY":
            status = "REMOTE_ONLY_UNVERIFIED"
        elif best:
            status = "NEEDS_REVIEW"
        else:
            status = "ATTACHMENT_MISSING_IN_DECEMBER"
        results.append(_attachment_result(att, status, best, "matched by parent discussion/filename"))
    return results


def _comment_result(comment: sqlite3.Row, status: str, best: dict[str, Any] | None, reason: str) -> dict[str, Any]:
    return {
        "comment_id": comment["comment_id"],
        "discussion_id": comment["discussion_id"],
        "group_slug": comment["group_slug"],
        "status": status,
        "best_match": best,
        "reason": reason,
    }


def _attachment_result(att: sqlite3.Row, status: str, best: dict[str, Any] | None, reason: str) -> dict[str, Any]:
    return {
        "attachment_id": att["attachment_id"],
        "discussion_id": att["discussion_id"],
        "group_slug": att["group_slug"],
        "filename": att["filename"],
        "url": att["url"],
        "status": status,
        "best_match": best,
        "reason": reason,
    }


def _count_group_status(con: sqlite3.Connection, status: str) -> int:
    return con.execute("SELECT COUNT(*) FROM groups WHERE visibility_status = ?", (status,)).fetchone()[0]


def _worst_groups(results: list[dict[str, Any]]) -> list[tuple[str, int]]:
    counts: dict[str, int] = defaultdict(int)
    for item in results:
        if item["status"] == "MISSING_IN_DECEMBER":
            counts[item["group_slug"]] += 1
    return sorted(counts.items(), key=lambda item: item[1], reverse=True)[:20]


def _write_summary(report: dict[str, Any], path: Path) -> None:
    s = report["summary"]
    lines = [
        "# Wix Groups Snapshot vs December Archive Summary",
        "",
        "- This is a read-only verification report.",
        "- `MISSING_IN_DECEMBER` is not an automatic import instruction.",
        "",
        "## Counts",
        "",
    ]
    for key, value in s.items():
        if not isinstance(value, (list, dict)):
            lines.append(f"- {key}: {value}")
    lines.extend(["", "## Status Counts", ""])
    lines.append(f"- discussions: {s['discussion_status_counts']}")
    lines.append(f"- comments: {s['comment_status_counts']}")
    lines.append(f"- attachments: {s['attachment_status_counts']}")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in report["limitations"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_comparison(report: dict[str, Any], path: Path) -> None:
    lines = ["# Wix Groups vs December Comparison", ""]
    lines.append("## Discussion Results")
    lines.append("")
    lines.append("| group | Wix discussion | status | best December match | score |")
    lines.append("|---|---|---|---|---:|")
    for item in report["discussion_results"]:
        best = item.get("best_match") or {}
        lines.append(
            f"| {_md(item['group_slug'])} | [{_md(item.get('title'))}]({item.get('discussion_url')}) | {item['status']} | "
            f"{_md(best.get('title'))} | {best.get('score', '')} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_missing_in_december(report: dict[str, Any], path: Path) -> None:
    rows = [item for item in report["discussion_results"] if item["status"] == "MISSING_IN_DECEMBER"]
    lines = ["# Wix Groups Discussions Missing In December", "", "| group | title | url | reason |", "|---|---|---|---|"]
    for item in rows:
        lines.append(f"| {_md(item['group_slug'])} | {_md(item.get('title'))} | {item.get('discussion_url')} | no candidate match |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_december_only(report: dict[str, Any], path: Path) -> None:
    rows = report["december_missing_in_wix_groups"]
    lines = ["# December Threads Not Visible In Wix Groups Snapshot", "", "| slug | thread_id | title |", "|---|---|---|"]
    for item in rows[:1000]:
        lines.append(f"| {_md(item.get('category_slug'))} | `{_md(item.get('thread_id'))}` | {_md(item.get('title'))} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_comment_coverage(report: dict[str, Any], path: Path) -> None:
    lines = ["# Comment Coverage Check", "", "| group | discussion_id | status | best match | reason |", "|---|---|---|---|---|"]
    for item in report["comment_results"]:
        best = item.get("best_match") or {}
        lines.append(f"| {_md(item['group_slug'])} | `{item['discussion_id']}` | {item['status']} | {_md(best)} | {_md(item['reason'])} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_attachment_coverage(report: dict[str, Any], path: Path) -> None:
    lines = ["# Attachment Coverage Check", "", "| group | filename | status | best match | reason |", "|---|---|---|---|---|"]
    for item in report["attachment_results"]:
        best = item.get("best_match") or {}
        lines.append(f"| {_md(item['group_slug'])} | {_md(item.get('filename'))} | {item['status']} | {_md(best)} | {_md(item['reason'])} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _md(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")
