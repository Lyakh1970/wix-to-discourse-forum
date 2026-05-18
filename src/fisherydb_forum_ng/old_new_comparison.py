from __future__ import annotations

import json
import math
import re
import sqlite3
import string
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


TECH_TOKEN_RE = re.compile(
    r"\b(?:[a-z]{1,8}[-/]?\d{1,5}[a-z]?|\d{1,5}[-/][a-z0-9-]{1,12}|"
    r"far-?\d{3,5}[a-z]?|fs-?\d{2,4}|ds-?\d{1,4}|opnsense|starlink|flir|"
    r"marport|furuno|simrad|jotron|triton|olex|transas|hikvision|dahua|cat-?sat|"
    r"inmarsat|iridium|raritan|honeywell|px4i|px45|px65|garmin|nmea|ais)\b",
    re.I,
)


@dataclass(frozen=True)
class CategoryMappingRow:
    old_slug: str
    expected_count: int | None
    target_discourse_path: str | None
    sample_titles: list[str]
    notes: str | None = None


def normalize_title(text: str | None) -> str:
    text = (text or "").lower()
    text = text.replace("ё", "е")
    text = re.sub(r"[_]+", " ", text)
    text = re.sub(r"[^\w\s\-/+.]+", " ", text, flags=re.U)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_category_path(text: str | None) -> str:
    text = normalize_title(text)
    text = re.sub(r"\s*>\s*", " > ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_filename(text: str | None) -> str:
    text = (text or "").lower().replace("\\", "/").split("/")[-1]
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize_title(text: str | None) -> set[str]:
    normalized = normalize_title(text)
    tokens = set(re.findall(r"[\w][\w\-/+.]{1,}", normalized, flags=re.U))
    return {token for token in tokens if token not in _STOPWORDS and len(token) > 1}


def text_similarity(a: str | None, b: str | None) -> float:
    na = normalize_title(a)
    nb = normalize_title(b)
    if not na or not nb:
        return 0.0
    seq = SequenceMatcher(None, na, nb).ratio()
    ta = tokenize_title(na)
    tb = tokenize_title(nb)
    if not ta or not tb:
        return seq
    jaccard = len(ta & tb) / len(ta | tb)
    return max(seq, (seq * 0.55) + (jaccard * 0.45))


def parse_category_mapping(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    rows: dict[str, CategoryMappingRow] = {}
    raw_rows: list[str] = []
    unparsed_rows: list[str] = []
    overrides: dict[str, str] = {}
    section = "mapping"

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            section = "overrides" if "переопредел" in stripped.lower() else "other"
            continue
        if not stripped.startswith("|") or "---" in stripped:
            continue
        cells = _split_md_row(stripped)
        if not cells:
            continue
        if section == "mapping":
            if _looks_like_header(cells, "Старый форум"):
                continue
            raw_rows.append(stripped)
            if len(cells) < 4:
                unparsed_rows.append(stripped)
                continue
            old_slug = _clean_cell(cells[0])
            expected_count = _parse_int(_clean_cell(cells[1]))
            target = _clean_cell(cells[2]) or None
            samples = [_clean_cell(item) for item in re.split(r";|\n", _clean_cell(cells[3])) if _clean_cell(item)]
            if not old_slug or not target:
                unparsed_rows.append(stripped)
                continue
            rows[old_slug] = CategoryMappingRow(
                old_slug=old_slug,
                expected_count=expected_count,
                target_discourse_path=target,
                sample_titles=samples,
            )
        elif section == "overrides":
            if _looks_like_header(cells, "Thread ID"):
                continue
            if len(cells) < 2:
                unparsed_rows.append(stripped)
                continue
            thread_id = _clean_cell(cells[0])
            target = _clean_cell(cells[1])
            if thread_id and target:
                overrides[thread_id] = target
            else:
                unparsed_rows.append(stripped)

    return {
        "path": str(path),
        "rows": {slug: row.__dict__ for slug, row in rows.items()},
        "overrides": overrides,
        "raw_mapping_rows": raw_rows,
        "unparsed_rows": unparsed_rows,
    }


def load_old_threads(db_path: Path, json_root: Path | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    json_threads = _load_json_threads(json_root) if json_root else {}
    rows = con.execute(
        """
        SELECT
            t.id AS thread_id,
            t.category_slug AS old_slug,
            c.name AS old_category_name,
            t.title,
            t.author_username AS author,
            t.created_at AS date,
            t.url,
            t.post_count
        FROM threads t
        LEFT JOIN categories c ON c.slug = t.category_slug
        ORDER BY t.category_slug, t.created_at, t.id
        """
    ).fetchall()
    threads: list[dict[str, Any]] = []
    for row in rows:
        thread_id = row["thread_id"]
        posts = con.execute(
            "SELECT id, content_text, content_html, is_comment FROM posts WHERE thread_id = ? ORDER BY is_comment, created_at, id",
            (thread_id,),
        ).fetchall()
        post_ids = [post["id"] for post in posts]
        placeholders = ",".join("?" for _ in post_ids)
        attachments: list[sqlite3.Row] = []
        if post_ids:
            attachments = con.execute(
                f"SELECT filename, local_path, is_image FROM attachments WHERE post_id IN ({placeholders})",
                post_ids,
            ).fetchall()
        first_post = next((post for post in posts if not post["is_comment"]), posts[0] if posts else None)
        json_thread = json_threads.get(thread_id, {})
        filenames = sorted(
            {
                normalize_filename(att["filename"] or att["local_path"])
                for att in attachments
                if normalize_filename(att["filename"] or att["local_path"])
            }
        )
        threads.append(
            {
                "thread_id": thread_id,
                "old_slug": row["old_slug"],
                "old_category_name": row["old_category_name"],
                "title": row["title"],
                "author": row["author"] or _json_author(json_thread),
                "date": row["date"] or json_thread.get("created_at"),
                "url": row["url"] or json_thread.get("url"),
                "first_post_body_text": first_post["content_text"] if first_post else None,
                "comments_count": sum(1 for post in posts if post["is_comment"]),
                "attachments_filenames": filenames,
                "attachments_count": len(attachments),
                "post_count": row["post_count"],
                "json_present": bool(json_thread),
            }
        )
    meta = {
        "db_path": str(db_path),
        "json_root": str(json_root) if json_root else None,
        "json_threads_loaded": len(json_threads),
    }
    return threads, meta


def load_discourse_inventory(path: Path, base_url: str) -> dict[str, Any]:
    inventory = json.loads(path.read_text(encoding="utf-8"))
    categories = inventory.get("categories", [])
    category_by_id = {cat.get("id"): cat for cat in categories}
    category_paths = {cat.get("id"): _category_path(cat, category_by_id) for cat in categories}
    topics = []
    detail_by_id = {detail.get("id"): detail for detail in inventory.get("topic_details", [])}
    for topic in inventory.get("topics", []):
        category_id = topic.get("category_id")
        detail = detail_by_id.get(topic.get("id"), {})
        title = topic.get("title") or detail.get("title")
        topics.append(
            {
                **topic,
                "title": title,
                "normalized_title": normalize_title(title),
                "tokens": sorted(tokenize_title(title)),
                "category_path": category_paths.get(category_id),
                "normalized_category_path": normalize_category_path(category_paths.get(category_id)),
                "url": _topic_url(base_url, topic),
                "detail_available": bool(detail),
                "upload_ref_count": detail.get("upload_ref_count"),
                "upload_ref_sample": detail.get("upload_ref_sample", []),
            }
        )
    return {
        "path": str(path),
        "base_url": base_url.rstrip("/"),
        "categories": categories,
        "category_paths": category_paths,
        "topics": topics,
        "details_available": len(detail_by_id),
        "summary": inventory.get("summary", {}),
    }


def compare_old_vs_discourse(
    old_threads: list[dict[str, Any]],
    mapping: dict[str, Any],
    discourse: dict[str, Any],
) -> dict[str, Any]:
    mapping_rows = mapping["rows"]
    overrides = mapping["overrides"]
    discourse_topics = discourse["topics"]
    results = []
    duplicate_matches: dict[int, list[str]] = defaultdict(list)
    for old in old_threads:
        result = _match_one(old, mapping_rows, overrides, discourse_topics, discourse["base_url"])
        results.append(result)
        match = result.get("best_match")
        if match and match.get("topic_id"):
            duplicate_matches[int(match["topic_id"])].append(old["thread_id"])

    status_counts = Counter(result["match_status"] for result in results)
    old_slugs = sorted({thread["old_slug"] for thread in old_threads})
    mapped_slugs = sorted(set(mapping_rows))
    missing_slugs = sorted(set(old_slugs) - set(mapped_slugs))
    target_imported = Counter(
        result.get("expected_target_discourse_path")
        for result in results
        if result["match_status"] in {"IMPORTED_EXACT", "IMPORTED_PROBABLE"} and result.get("expected_target_discourse_path")
    )
    target_not_found = Counter(
        result.get("expected_target_discourse_path")
        for result in results
        if result["match_status"] == "NOT_FOUND" and result.get("expected_target_discourse_path")
    )
    slug_not_found = Counter(result["old_slug"] for result in results if result["match_status"] == "NOT_FOUND")

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "mode": "read_only_old_forum_vs_discourse_comparison",
        "summary": {
            "old_threads_total": len(old_threads),
            "old_slugs_total": len(old_slugs),
            "mapping_rows": len(mapping_rows),
            "slugs_with_mapping": len(set(old_slugs) & set(mapped_slugs)),
            "slugs_missing_mapping": len(missing_slugs),
            "discourse_topics_total": len(discourse_topics),
            "discourse_topic_details_available": discourse["details_available"],
            "status_counts": dict(status_counts),
            "top_old_slugs_by_not_found": slug_not_found.most_common(20),
            "top_target_paths_by_imported": target_imported.most_common(20),
            "top_target_paths_by_not_found": target_not_found.most_common(20),
        },
        "inputs": {
            "mapping_path": mapping["path"],
            "discourse_inventory_path": discourse["path"],
            "discourse_base_url": discourse["base_url"],
        },
        "mapping": {
            "missing_old_slugs": missing_slugs,
            "unparsed_rows": mapping.get("unparsed_rows", []),
            "overrides": overrides,
        },
        "limitations": [
            "Primary run uses Discourse inventory only; full cooked/raw post bodies are available only for the sampled topic_details in that inventory.",
            "Attachment comparison is limited because Discourse inventory stores upload references only for sampled topic details and does not download files.",
            "NOT_FOUND means no confident match with current data and scoring, not an instruction to import.",
            "Date mismatches are weak evidence because imported Discourse topics may have migration-era timestamps.",
        ],
        "results": results,
        "possible_duplicates_or_repeated_imports": [
            {"discourse_topic_id": topic_id, "old_thread_ids": thread_ids}
            for topic_id, thread_ids in sorted(duplicate_matches.items())
            if len(thread_ids) > 1
        ],
    }


def write_all_reports(report: dict[str, Any], reports_dir: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    _write_json(report, reports_dir / "old_vs_new_forum_comparison.json")
    _write_summary(report, reports_dir / "old_vs_new_forum_summary.md")
    _write_comparison_md(report, reports_dir / "old_vs_new_forum_comparison.md")
    _write_not_found(report, reports_dir / "old_threads_not_found_in_discourse.md")
    _write_probably_imported(report, reports_dir / "old_threads_probably_imported.md")
    _write_manual_review(report, reports_dir / "old_threads_manual_review.md")


def _match_one(
    old: dict[str, Any],
    mapping_rows: dict[str, Any],
    overrides: dict[str, str],
    discourse_topics: list[dict[str, Any]],
    base_url: str,
) -> dict[str, Any]:
    mapping = mapping_rows.get(old["old_slug"])
    override_path = overrides.get(old["thread_id"])
    expected_path = override_path or (mapping or {}).get("target_discourse_path")
    old_tokens = tokenize_title(old["title"])
    old_tech_tokens = _technical_tokens(old["title"])
    candidates = []
    for topic in discourse_topics:
        score, evidence = _score_candidate(old, old_tokens, old_tech_tokens, expected_path, override_path, topic)
        if score >= 35:
            candidates.append(
                {
                    "topic_id": topic.get("id"),
                    "title": topic.get("title"),
                    "url": topic.get("url") or _topic_url(base_url, topic),
                    "category_path": topic.get("category_path"),
                    "score": round(score, 2),
                    "evidence": evidence,
                }
            )
    candidates.sort(key=lambda item: item["score"], reverse=True)
    best = candidates[0] if candidates else None
    status, reason = _status_for(old, mapping, best, candidates)
    return {
        "thread_id": old["thread_id"],
        "old_slug": old["old_slug"],
        "old_category_name": old.get("old_category_name"),
        "title": old.get("title"),
        "date": old.get("date"),
        "author": old.get("author"),
        "url": old.get("url"),
        "comments_count": old.get("comments_count"),
        "attachments_count": old.get("attachments_count"),
        "attachments_filenames": old.get("attachments_filenames", []),
        "expected_target_discourse_path": expected_path,
        "override_target_discourse_path": override_path,
        "match_status": status,
        "reason": reason,
        "best_match": best,
        "top_candidates": candidates[:3],
    }


def _score_candidate(
    old: dict[str, Any],
    old_tokens: set[str],
    old_tech_tokens: set[str],
    expected_path: str | None,
    override_path: str | None,
    topic: dict[str, Any],
) -> tuple[float, dict[str, Any]]:
    old_title_norm = normalize_title(old.get("title"))
    topic_title_norm = topic.get("normalized_title") or normalize_title(topic.get("title"))
    exact = bool(old_title_norm and old_title_norm == topic_title_norm)
    sim = text_similarity(old_title_norm, topic_title_norm)
    topic_tokens = set(topic.get("tokens") or tokenize_title(topic.get("title")))
    token_overlap = len(old_tokens & topic_tokens) / max(len(old_tokens | topic_tokens), 1)
    tech_overlap = sorted(old_tech_tokens & _technical_tokens(topic.get("title")))
    score = 0.0
    if exact:
        score += 72
    else:
        score += sim * 48
        score += token_overlap * 24
    if tech_overlap:
        score += min(12, 4 + len(tech_overlap) * 2)
    category_match = False
    if expected_path:
        category_match = normalize_category_path(expected_path) == topic.get("normalized_category_path")
        if category_match:
            score += 14 if not override_path else 20
    date_bonus = _date_bonus(old.get("date"), topic.get("created_at"))
    score += date_bonus
    attachment_evidence = "unavailable"
    if topic.get("upload_ref_count") is not None:
        if old.get("attachments_count") and topic.get("upload_ref_count"):
            score += min(6, math.log1p(min(old["attachments_count"], topic["upload_ref_count"])) * 2)
            attachment_evidence = "both_have_uploads"
        elif old.get("attachments_count") == 0 and topic.get("upload_ref_count") == 0:
            score += 1
            attachment_evidence = "both_zero_in_sample"
        else:
            attachment_evidence = "count_diff_or_sample_limited"
    return score, {
        "title": {
            "exact_normalized": exact,
            "similarity": round(sim, 3),
            "token_overlap": round(token_overlap, 3),
            "shared_technical_tokens": tech_overlap,
        },
        "category": {
            "expected_path": expected_path,
            "candidate_path": topic.get("category_path"),
            "matches_expected": category_match,
        },
        "date": {"bonus": date_bonus},
        "attachment": attachment_evidence,
        "body": "unavailable_without_expanded_discourse_details",
        "override": bool(override_path),
    }


def _status_for(
    old: dict[str, Any],
    mapping: dict[str, Any] | None,
    best: dict[str, Any] | None,
    candidates: list[dict[str, Any]],
) -> tuple[str, str]:
    if not mapping:
        return "MAPPING_MISSING", "old_slug is absent from CATEGORY_MAPPING_REVIEW.md"
    if not best:
        return "NOT_FOUND", "no candidate above minimal score"
    score = best["score"]
    title_exact = best["evidence"]["title"]["exact_normalized"]
    category_match = best["evidence"]["category"]["matches_expected"]
    ambiguous = len(candidates) > 1 and (score - candidates[1]["score"]) < 6
    if title_exact and score >= 80:
        return "IMPORTED_EXACT", "exact normalized title match with supporting evidence"
    if score >= 74 and (category_match or best["evidence"]["title"]["shared_technical_tokens"]):
        return "IMPORTED_PROBABLE", "strong title/category/token evidence"
    if score >= 58:
        if ambiguous:
            return "MANUAL_REVIEW", "multiple close candidates"
        return "POSSIBLE_MATCH", "candidate is plausible but evidence is not strong enough"
    if score >= 45:
        return "MANUAL_REVIEW", "weak candidate above minimal score"
    return "NOT_FOUND", "best candidate score is below confidence threshold"


def _load_json_threads(json_root: Path | None) -> dict[str, dict[str, Any]]:
    if not json_root or not json_root.exists():
        return {}
    threads: dict[str, dict[str, Any]] = {}
    for path in json_root.glob("*/threads.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for thread in data.get("threads", []):
            if isinstance(thread, dict) and thread.get("id"):
                threads[thread["id"]] = thread
    return threads


def _category_path(category: dict[str, Any], category_by_id: dict[Any, dict[str, Any]]) -> str:
    names = []
    seen = set()
    current = category
    while current and current.get("id") not in seen:
        seen.add(current.get("id"))
        if current.get("name"):
            names.append(current["name"])
        parent_id = current.get("parent_category_id")
        current = category_by_id.get(parent_id)
    return " > ".join(reversed(names))


def _topic_url(base_url: str, topic: dict[str, Any]) -> str | None:
    topic_id = topic.get("id")
    slug = topic.get("slug")
    if not topic_id:
        return None
    if slug:
        return f"{base_url.rstrip('/')}/t/{slug}/{topic_id}"
    return f"{base_url.rstrip('/')}/t/{topic_id}"


def _date_bonus(old_date: str | None, new_date: str | None) -> float:
    old_dt = _parse_date(old_date)
    new_dt = _parse_date(new_date)
    if not old_dt or not new_dt:
        return 0.0
    delta = abs((new_dt - old_dt).days)
    if delta <= 7:
        return 5.0
    if delta <= 45:
        return 2.5
    return 0.0


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%b %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _technical_tokens(text: str | None) -> set[str]:
    return {match.group(0).lower().replace(" ", "") for match in TECH_TOKEN_RE.finditer(text or "")}


def _split_md_row(line: str) -> list[str]:
    cells = []
    current = []
    escaped = False
    for char in line.strip().strip("|"):
        if char == "\\" and not escaped:
            escaped = True
            current.append(char)
            continue
        if char == "|" and not escaped:
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        escaped = False
    cells.append("".join(current).strip())
    return cells


def _looks_like_header(cells: list[str], text: str) -> bool:
    return bool(cells and text.lower() in cells[0].lower())


def _clean_cell(text: str) -> str:
    text = re.sub(r"<br\s*/?>", "; ", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_int(text: str) -> int | None:
    match = re.search(r"\d+", text or "")
    return int(match.group(0)) if match else None


def _json_author(thread: dict[str, Any]) -> str | None:
    author = thread.get("author")
    if isinstance(author, dict):
        return author.get("username") or author.get("display_name")
    return None


def _write_json(report: dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_summary(report: dict[str, Any], path: Path) -> None:
    summary = report["summary"]
    counts = summary["status_counts"]
    lines = [
        "# Old Forum vs New Discourse Summary",
        "",
        "Read-only comparison only. `NOT_FOUND` means no match under current data and scoring, not an import instruction.",
        "",
        "## Counts",
        "",
        f"- Old threads total: {summary['old_threads_total']}",
        f"- Old categories/slugs total: {summary['old_slugs_total']}",
        f"- Mapping rows: {summary['mapping_rows']}",
        f"- Slugs with mapping: {summary['slugs_with_mapping']}",
        f"- Slugs missing mapping: {summary['slugs_missing_mapping']}",
        f"- Discourse topics total: {summary['discourse_topics_total']}",
        f"- Discourse topic details available: {summary['discourse_topic_details_available']}",
        "",
        "## Match Status",
        "",
    ]
    for status in ["IMPORTED_EXACT", "IMPORTED_PROBABLE", "POSSIBLE_MATCH", "NOT_FOUND", "MANUAL_REVIEW", "MAPPING_MISSING"]:
        lines.append(f"- {status}: {counts.get(status, 0)}")
    lines.extend(["", "## Top Old Slugs By NOT_FOUND", ""])
    lines.extend(_counter_lines(summary["top_old_slugs_by_not_found"]))
    lines.extend(["", "## Top Target Discourse Paths By Found Imports", ""])
    lines.extend(_counter_lines(summary["top_target_paths_by_imported"]))
    lines.extend(["", "## Top Target Discourse Paths By NOT_FOUND", ""])
    lines.extend(_counter_lines(summary["top_target_paths_by_not_found"]))
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in report["limitations"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_comparison_md(report: dict[str, Any], path: Path) -> None:
    results = report["results"]
    per_slug: dict[str, Counter[str]] = defaultdict(Counter)
    for result in results:
        per_slug[result["old_slug"]][result["match_status"]] += 1
    lines = [
        "# Old Local Forum vs New Discourse Comparison",
        "",
        "This report uses `CATEGORY_MAPPING_REVIEW.md` as the human-approved old category to target Discourse path mapping.",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        if not isinstance(value, (list, dict)):
            lines.append(f"- {key}: {value}")
    lines.extend(["", "## Mapping Coverage", ""])
    lines.append(f"- Missing old slugs in mapping: {', '.join(report['mapping']['missing_old_slugs']) or 'none'}")
    lines.append(f"- Unparsed mapping rows: {len(report['mapping']['unparsed_rows'])}")
    lines.extend(["", "## Per-Category Results", ""])
    lines.append("| old_slug | total | exact | probable | possible | manual | not found | mapping missing |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for slug in sorted(per_slug):
        counter = per_slug[slug]
        total = sum(counter.values())
        lines.append(
            f"| {_md(slug)} | {total} | {counter['IMPORTED_EXACT']} | {counter['IMPORTED_PROBABLE']} | "
            f"{counter['POSSIBLE_MATCH']} | {counter['MANUAL_REVIEW']} | {counter['NOT_FOUND']} | {counter['MAPPING_MISSING']} |"
        )
    lines.extend(["", "## Not Found List", ""])
    for result in [item for item in results if item["match_status"] == "NOT_FOUND"][:100]:
        lines.append(f"- `{result['old_slug']}` `{result['thread_id']}`: {result['title']}")
    lines.extend(["", "## Possible Duplicates / Repeated Imports", ""])
    duplicates = report["possible_duplicates_or_repeated_imports"]
    if duplicates:
        for item in duplicates[:100]:
            lines.append(f"- Discourse topic `{item['discourse_topic_id']}` matched old threads: {', '.join(item['old_thread_ids'])}")
    else:
        lines.append("- none detected")
    lines.extend(["", "## Recommendations", ""])
    lines.append("- Review `old_threads_manual_review.md` before any import decision.")
    lines.append("- Treat `NOT_FOUND` as a candidate backlog, not as automatic import scope.")
    lines.append("- If manual review remains large, rerun with expanded Discourse details before deciding on do-import strategy.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_not_found(report: dict[str, Any], path: Path) -> None:
    rows = [item for item in report["results"] if item["match_status"] == "NOT_FOUND"]
    lines = [
        "# Old Threads Not Found In Discourse",
        "",
        "| old_slug | old_category_name | thread_id | title | date | author | attachments_count | expected_target_discourse_path | reason |",
        "|---|---|---|---|---|---|---:|---|---|",
    ]
    for item in rows:
        lines.append(
            f"| {_md(item['old_slug'])} | {_md(item.get('old_category_name'))} | `{_md(item['thread_id'])}` | {_md(item['title'])} | "
            f"{_md(item.get('date'))} | {_md(item.get('author'))} | {item.get('attachments_count') or 0} | "
            f"{_md(item.get('expected_target_discourse_path'))} | {_md(item.get('reason'))} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_probably_imported(report: dict[str, Any], path: Path) -> None:
    rows = [item for item in report["results"] if item["match_status"] in {"IMPORTED_EXACT", "IMPORTED_PROBABLE"}]
    lines = [
        "# Old Threads Probably Imported",
        "",
        "| old_slug | old title | matched Discourse title | topic id/url | status | score | evidence |",
        "|---|---|---|---|---|---:|---|",
    ]
    for item in rows:
        match = item["best_match"] or {}
        lines.append(
            f"| {_md(item['old_slug'])} | {_md(item['title'])} | {_md(match.get('title'))} | "
            f"[{match.get('topic_id')}]({match.get('url')}) | {item['match_status']} | {match.get('score', '')} | "
            f"{_md(_evidence_summary(match.get('evidence', {})))} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_manual_review(report: dict[str, Any], path: Path) -> None:
    rows = [item for item in report["results"] if item["match_status"] in {"MANUAL_REVIEW", "POSSIBLE_MATCH", "MAPPING_MISSING"}]
    lines = [
        "# Old Threads Manual Review",
        "",
        "| old thread | top 3 candidate Discourse topics | scores | why manual review is needed |",
        "|---|---|---|---|",
    ]
    for item in rows:
        candidates = item.get("top_candidates", [])
        candidate_text = "<br>".join(
            f"[{cand.get('topic_id')}]({cand.get('url')}) {_md(cand.get('title'))}" for cand in candidates
        )
        scores = ", ".join(str(cand.get("score")) for cand in candidates)
        old_thread = f"`{_md(item['old_slug'])}` `{_md(item['thread_id'])}`<br>{_md(item['title'])}"
        lines.append(f"| {old_thread} | {candidate_text or 'none'} | {_md(scores)} | {_md(item.get('reason'))} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _counter_lines(items: list[list[Any]] | list[tuple[Any, Any]]) -> list[str]:
    if not items:
        return ["- none"]
    return [f"- {name}: {count}" for name, count in items]


def _evidence_summary(evidence: dict[str, Any]) -> str:
    title = evidence.get("title", {})
    category = evidence.get("category", {})
    return (
        f"title exact={title.get('exact_normalized')} sim={title.get('similarity')} "
        f"tokens={','.join(title.get('shared_technical_tokens') or [])}; "
        f"category={category.get('matches_expected')}; "
        f"attachment={evidence.get('attachment')}; body={evidence.get('body')}; "
        f"override={evidence.get('override')}"
    )


def _md(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ").strip()


_STOPWORDS = {
    "and",
    "the",
    "for",
    "with",
    "from",
    "это",
    "для",
    "как",
    "что",
    "или",
    "при",
    "на",
    "по",
    "в",
    "и",
    "с",
    "к",
    "от",
}
