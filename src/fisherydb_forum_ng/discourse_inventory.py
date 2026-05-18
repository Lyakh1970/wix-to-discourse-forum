from __future__ import annotations

import json
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


UPLOAD_RE = re.compile(r"""(?:href|src)=["']([^"']*/uploads/[^"']+)["']""", re.I)


@dataclass(frozen=True)
class DiscourseConfig:
    base_url: str
    api_username: str
    api_key: str
    user_agent: str = "FisheryDB migration audit read-only inventory/1.0"
    timeout_seconds: int = 30


class DiscourseInventoryError(RuntimeError):
    pass


class ReadOnlyDiscourseClient:
    def __init__(self, config: DiscourseConfig) -> None:
        self.config = config
        self.base_url = config.base_url.rstrip("/") + "/"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Api-Key": config.api_key,
                "Api-Username": config.api_username,
                "User-Agent": config.user_agent,
                "Accept": "application/json",
            }
        )

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = urljoin(self.base_url, path.lstrip("/"))
        response: requests.Response | None = None
        for attempt in range(8):
            response = self.session.get(url, params=params, timeout=self.config.timeout_seconds)
            if response.status_code != 429:
                break
            retry_after = response.headers.get("Retry-After")
            wait_seconds = int(retry_after) if retry_after and retry_after.isdigit() else 20 * (attempt + 1)
            time.sleep(min(wait_seconds, 120))
        assert response is not None
        if response.status_code >= 400:
            raise DiscourseInventoryError(f"GET {path} failed with HTTP {response.status_code}")
        try:
            data = response.json()
        except ValueError as exc:
            raise DiscourseInventoryError(f"GET {path} did not return JSON") from exc
        if not isinstance(data, dict):
            raise DiscourseInventoryError(f"GET {path} returned unexpected JSON type")
        return data


def load_discourse_config_from_env(env: dict[str, str]) -> DiscourseConfig:
    base_url = env.get("DISCOURSE_BASE_URL", "").strip()
    api_username = env.get("DISCOURSE_API_USERNAME", "").strip()
    api_key = env.get("DISCOURSE_API_KEY", "").strip()
    missing = [
        name
        for name, value in (
            ("DISCOURSE_BASE_URL", base_url),
            ("DISCOURSE_API_USERNAME", api_username),
            ("DISCOURSE_API_KEY", api_key),
        )
        if not value
    ]
    if missing:
        raise DiscourseInventoryError("Missing required .env values: " + ", ".join(missing))
    return DiscourseConfig(base_url=base_url, api_username=api_username, api_key=api_key)


def run_discourse_inventory(
    config: DiscourseConfig,
    *,
    page_limit: int = 0,
    topic_detail_limit: int = 0,
    delay_seconds: float = 0.25,
) -> dict[str, Any]:
    client = ReadOnlyDiscourseClient(config)
    generated_at = datetime.now(timezone.utc).isoformat()

    categories_payload = client.get_json("/categories.json")
    site_payload = client.get_json("/site.json")
    categories = _merge_categories(
        _extract_categories(categories_payload),
        _extract_categories(site_payload),
    )

    topics, latest_pages = _fetch_latest_topics(client, page_limit=page_limit)
    topic_details = _fetch_topic_details(
        client,
        topics,
        topic_detail_limit=topic_detail_limit,
        delay_seconds=delay_seconds,
    )

    report = _build_report(
        generated_at=generated_at,
        config=config,
        categories=categories,
        topics=topics,
        latest_pages=latest_pages,
        topic_details=topic_details,
        page_limit=page_limit,
        topic_detail_limit=topic_detail_limit,
        delay_seconds=delay_seconds,
    )
    return report


def _extract_categories(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_categories = payload.get("category_list", {}).get("categories")
    if raw_categories is None:
        raw_categories = payload.get("categories", [])
    categories: list[dict[str, Any]] = []
    stack = list(raw_categories) if isinstance(raw_categories, list) else []
    while stack:
        category = stack.pop(0)
        if not isinstance(category, dict):
            continue
        categories.append(
            {
                "id": category.get("id"),
                "name": category.get("name"),
                "slug": category.get("slug"),
                "topic_count": _as_int(category.get("topic_count")),
                "post_count": _as_int(category.get("post_count")),
                "topics_year": _as_int(category.get("topics_year")),
                "topics_month": _as_int(category.get("topics_month")),
                "topics_week": _as_int(category.get("topics_week")),
                "read_restricted": bool(category.get("read_restricted")),
                "permission": category.get("permission"),
                "parent_category_id": category.get("parent_category_id"),
            }
        )
        subcategories = category.get("subcategory_list") or category.get("subcategories") or []
        if isinstance(subcategories, list):
            stack.extend(subcategories)
    return categories


def _merge_categories(*category_lists: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[int, dict[str, Any]] = {}
    for categories in category_lists:
        for category in categories:
            category_id = _as_int(category.get("id"))
            if category_id <= 0:
                continue
            current = merged.get(category_id, {})
            merged[category_id] = {**current, **{key: value for key, value in category.items() if value is not None}}
    return sorted(merged.values(), key=lambda item: (_as_int(item.get("parent_category_id")), _as_int(item.get("id"))))


def _fetch_latest_topics(
    client: ReadOnlyDiscourseClient,
    *,
    page_limit: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    topics_by_id: dict[int, dict[str, Any]] = {}
    pages: list[dict[str, Any]] = []
    page = 0
    empty_pages = 0
    while True:
        if page_limit and page >= page_limit:
            break
        payload = client.get_json("/latest.json", params={"page": page})
        raw_topics = payload.get("topic_list", {}).get("topics", [])
        if not isinstance(raw_topics, list):
            raw_topics = []
        new_count = 0
        for topic in raw_topics:
            if not isinstance(topic, dict):
                continue
            topic_id = _as_int(topic.get("id"))
            if topic_id <= 0:
                continue
            if topic_id not in topics_by_id:
                topics_by_id[topic_id] = _summarize_topic(topic)
                new_count += 1
        pages.append({"page": page, "topics_seen": len(raw_topics), "new_topics": new_count})
        if not raw_topics or new_count == 0:
            empty_pages += 1
        else:
            empty_pages = 0
        if empty_pages >= 2:
            break
        page += 1
    topics = sorted(topics_by_id.values(), key=lambda item: item["id"])
    return topics, pages


def _summarize_topic(topic: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _as_int(topic.get("id")),
        "title": topic.get("title"),
        "slug": topic.get("slug"),
        "category_id": topic.get("category_id"),
        "posts_count": _as_int(topic.get("posts_count")),
        "reply_count": _as_int(topic.get("reply_count")),
        "created_at": topic.get("created_at"),
        "last_posted_at": topic.get("last_posted_at"),
        "last_poster_username": topic.get("last_poster_username"),
        "pinned": bool(topic.get("pinned")),
        "closed": bool(topic.get("closed")),
        "archived": bool(topic.get("archived")),
        "visible": topic.get("visible"),
    }


def _fetch_topic_details(
    client: ReadOnlyDiscourseClient,
    topics: list[dict[str, Any]],
    *,
    topic_detail_limit: int,
    delay_seconds: float,
) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    if topic_detail_limit < 0:
        return details
    selected_topics = topics[:topic_detail_limit] if topic_detail_limit else topics
    for index, topic in enumerate(selected_topics, start=1):
        if delay_seconds and index > 1:
            time.sleep(delay_seconds)
        topic_id = topic["id"]
        try:
            payload = client.get_json(f"/t/{topic_id}.json")
        except DiscourseInventoryError as exc:
            details.append({"id": topic_id, "fetch_error": str(exc)})
            continue
        details.append(_summarize_topic_detail(payload))
    return details


def _summarize_topic_detail(payload: dict[str, Any]) -> dict[str, Any]:
    posts = payload.get("post_stream", {}).get("posts", [])
    stream = payload.get("post_stream", {}).get("stream", [])
    if not isinstance(posts, list):
        posts = []
    if not isinstance(stream, list):
        stream = []

    post_summaries: list[dict[str, Any]] = []
    upload_refs: list[str] = []
    for post in posts:
        if not isinstance(post, dict):
            continue
        cooked = post.get("cooked") or ""
        post_uploads = _extract_upload_refs(cooked)
        upload_refs.extend(post_uploads)
        post_summaries.append(
            {
                "id": post.get("id"),
                "post_number": post.get("post_number"),
                "username": post.get("username"),
                "created_at": post.get("created_at"),
                "updated_at": post.get("updated_at"),
                "cooked_length": len(cooked),
                "upload_ref_count": len(post_uploads),
                "has_body": bool(_plain_text(cooked).strip()),
            }
        )

    return {
        "id": _as_int(payload.get("id")),
        "title": payload.get("title"),
        "slug": payload.get("slug"),
        "category_id": payload.get("category_id"),
        "created_at": payload.get("created_at"),
        "posts_count": _as_int(payload.get("posts_count")),
        "reply_count": _as_int(payload.get("reply_count")),
        "views": _as_int(payload.get("views")),
        "stream_post_ids_count": len(stream),
        "included_posts_count": len(post_summaries),
        "missing_included_posts_count": max(len(stream) - len(post_summaries), 0),
        "post_summaries": post_summaries,
        "upload_ref_count": len(upload_refs),
        "upload_ref_sample": sorted(set(upload_refs))[:20],
    }


def _extract_upload_refs(cooked: str) -> list[str]:
    refs = []
    for match in UPLOAD_RE.finditer(cooked):
        refs.append(match.group(1))
    return refs


def _plain_text(cooked: str) -> str:
    if not cooked:
        return ""
    return BeautifulSoup(cooked, "html.parser").get_text(" ", strip=True)


def _build_report(
    *,
    generated_at: str,
    config: DiscourseConfig,
    categories: list[dict[str, Any]],
    topics: list[dict[str, Any]],
    latest_pages: list[dict[str, Any]],
    topic_details: list[dict[str, Any]],
    page_limit: int,
    topic_detail_limit: int,
    delay_seconds: float,
) -> dict[str, Any]:
    category_by_id = {category["id"]: category for category in categories}
    topics_by_category: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for topic in topics:
        topics_by_category[topic.get("category_id")].append(topic)

    detail_by_id = {detail.get("id"): detail for detail in topic_details if not detail.get("fetch_error")}
    detail_errors = [detail for detail in topic_details if detail.get("fetch_error")]
    included_posts_total = sum(_as_int(detail.get("included_posts_count")) for detail in topic_details)
    post_stream_ids_total = sum(_as_int(detail.get("stream_post_ids_count")) for detail in topic_details)
    topic_posts_count_total = sum(_as_int(topic.get("posts_count")) for topic in topics)
    upload_ref_count = sum(_as_int(detail.get("upload_ref_count")) for detail in topic_details)

    missing_titles = [topic["id"] for topic in topics if not (topic.get("title") or "").strip()]
    missing_categories = [topic["id"] for topic in topics if topic.get("category_id") not in category_by_id]
    missing_post_bodies = [
        {"topic_id": detail.get("id"), "post_id": post.get("id")}
        for detail in topic_details
        for post in detail.get("post_summaries", [])
        if not post.get("has_body")
    ]
    missing_post_authors = [
        {"topic_id": detail.get("id"), "post_id": post.get("id")}
        for detail in topic_details
        for post in detail.get("post_summaries", [])
        if not post.get("username")
    ]
    missing_post_dates = [
        {"topic_id": detail.get("id"), "post_id": post.get("id")}
        for detail in topic_details
        for post in detail.get("post_summaries", [])
        if not post.get("created_at")
    ]

    categories_report = []
    for category in categories:
        category_topics = topics_by_category.get(category["id"], [])
        detail_ids = {topic["id"] for topic in category_topics}
        category_details = [detail_by_id[topic_id] for topic_id in detail_ids if topic_id in detail_by_id]
        categories_report.append(
            {
                **category,
                "latest_topics_seen": len(category_topics),
                "latest_posts_count_sum": sum(_as_int(topic.get("posts_count")) for topic in category_topics),
                "detail_posts_seen": sum(_as_int(detail.get("included_posts_count")) for detail in category_details),
                "upload_ref_count": sum(_as_int(detail.get("upload_ref_count")) for detail in category_details),
            }
        )

    return {
        "generated_at": generated_at,
        "mode": "read_only_discourse_inventory",
        "source": {
            "base_url": config.base_url.rstrip("/"),
            "api_username": config.api_username,
            "api_key_recorded": False,
        },
        "limits": {
            "latest_page_limit": page_limit,
            "topic_detail_limit": topic_detail_limit,
            "topic_detail_delay_seconds": delay_seconds,
        },
        "summary": {
            "categories": len(categories),
            "read_restricted_categories": sum(1 for item in categories if item.get("read_restricted")),
            "latest_pages_checked": len(latest_pages),
            "topics_discovered": len(topics),
            "topics_detail_attempted": len(topic_details),
            "topics_detail_fetched": len(detail_by_id),
            "topic_detail_errors": len(detail_errors),
            "topic_posts_count_total": topic_posts_count_total,
            "post_stream_ids_total": post_stream_ids_total,
            "included_posts_metadata_total": included_posts_total,
            "upload_references_in_included_posts": upload_ref_count,
            "topics_without_title": len(missing_titles),
            "topics_with_unknown_category": len(missing_categories),
            "included_posts_without_body": len(missing_post_bodies),
            "included_posts_without_author": len(missing_post_authors),
            "included_posts_without_date": len(missing_post_dates),
        },
        "quality": {
            "topics_without_title": missing_titles[:200],
            "topics_with_unknown_category": missing_categories[:200],
            "included_posts_without_body": missing_post_bodies[:200],
            "included_posts_without_author": missing_post_authors[:200],
            "included_posts_without_date": missing_post_dates[:200],
            "topic_detail_errors": detail_errors[:50],
        },
        "latest_pages": latest_pages,
        "categories": categories_report,
        "topics": topics,
        "topic_details": topic_details,
        "practical_conclusion": _practical_conclusion(
            categories=categories,
            topics=topics,
            detail_errors=detail_errors,
            missing_titles=missing_titles,
            missing_categories=missing_categories,
            missing_post_bodies=missing_post_bodies,
            missing_post_authors=missing_post_authors,
            missing_post_dates=missing_post_dates,
        ),
    }


def _practical_conclusion(
    *,
    categories: list[dict[str, Any]],
    topics: list[dict[str, Any]],
    detail_errors: list[dict[str, Any]],
    missing_titles: list[int],
    missing_categories: list[int],
    missing_post_bodies: list[dict[str, Any]],
    missing_post_authors: list[dict[str, Any]],
    missing_post_dates: list[dict[str, Any]],
) -> dict[str, Any]:
    blockers = []
    review = []
    if not categories:
        blockers.append("No categories were returned by Discourse API.")
    if not topics:
        review.append("No topics were discovered through /latest.json pagination.")
    if detail_errors:
        review.append("Some topic detail API requests failed; rerun or inspect before comparison.")
    if missing_titles or missing_categories:
        review.append("Some topic metadata is incomplete.")
    if missing_post_bodies or missing_post_authors or missing_post_dates:
        review.append("Some included post metadata is incomplete.")
    return {
        "can_use_for_read_only_comparison": not blockers,
        "blocking_issues": blockers,
        "review_notes": review,
        "next_step": (
            "Use this inventory as the current Discourse-side baseline for a read-only "
            "local archive vs Discourse comparison."
        ),
    }


def write_json_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def write_markdown_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = report["summary"]
    categories = sorted(report["categories"], key=lambda item: item.get("topic_count") or 0, reverse=True)
    lines = [
        "# Discourse Read-Only Inventory",
        "",
        f"Generated at: `{report['generated_at']}`",
        f"Base URL: `{report['source']['base_url']}`",
        "",
        "## Summary",
        "",
        f"- Categories: {summary['categories']}",
        f"- Read-restricted categories: {summary['read_restricted_categories']}",
        f"- Latest pages checked: {summary['latest_pages_checked']}",
        f"- Topics discovered: {summary['topics_discovered']}",
        f"- Topic details fetched: {summary['topics_detail_fetched']} / {summary['topics_detail_attempted']}",
        f"- Topic posts_count total: {summary['topic_posts_count_total']}",
        f"- Post stream IDs total: {summary['post_stream_ids_total']}",
        f"- Included post metadata total: {summary['included_posts_metadata_total']}",
        f"- Upload references in included posts: {summary['upload_references_in_included_posts']}",
        "",
        "## Quality Signals",
        "",
        f"- Topics without title: {summary['topics_without_title']}",
        f"- Topics with unknown category: {summary['topics_with_unknown_category']}",
        f"- Included posts without body: {summary['included_posts_without_body']}",
        f"- Included posts without author: {summary['included_posts_without_author']}",
        f"- Included posts without date: {summary['included_posts_without_date']}",
        f"- Topic detail errors: {summary['topic_detail_errors']}",
        "",
        "## Categories",
        "",
        "| id | slug | name | API topic_count | API post_count | latest topics seen | upload refs | read restricted |",
        "|---:|---|---|---:|---:|---:|---:|---|",
    ]
    for category in categories:
        lines.append(
            "| {id} | {slug} | {name} | {topic_count} | {post_count} | {latest_topics_seen} | {upload_ref_count} | {read_restricted} |".format(
                id=category.get("id") or "",
                slug=_md_cell(category.get("slug")),
                name=_md_cell(category.get("name")),
                topic_count=category.get("topic_count") or 0,
                post_count=category.get("post_count") or 0,
                latest_topics_seen=category.get("latest_topics_seen") or 0,
                upload_ref_count=category.get("upload_ref_count") or 0,
                read_restricted=category.get("read_restricted"),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = report["summary"]
    conclusion = report["practical_conclusion"]
    lines = [
        "# Discourse Inventory Summary",
        "",
        "Phase 3 used the Discourse API in read-only mode. It did not create, update, delete, or import anything.",
        "",
        "## Counts",
        "",
        f"- Categories: {summary['categories']}",
        f"- Topics discovered via `/latest.json`: {summary['topics_discovered']}",
        f"- Topic details fetched: {summary['topics_detail_fetched']} / {summary['topics_detail_attempted']}",
        f"- Total topic `posts_count`: {summary['topic_posts_count_total']}",
        f"- Post stream IDs seen in topic details: {summary['post_stream_ids_total']}",
        f"- Included post metadata records: {summary['included_posts_metadata_total']}",
        f"- Upload references found in included posts: {summary['upload_references_in_included_posts']}",
        "",
        "## Quality",
        "",
        f"- Topics without title: {summary['topics_without_title']}",
        f"- Topics with unknown category: {summary['topics_with_unknown_category']}",
        f"- Included posts without body: {summary['included_posts_without_body']}",
        f"- Included posts without author: {summary['included_posts_without_author']}",
        f"- Included posts without date: {summary['included_posts_without_date']}",
        f"- Topic detail fetch errors: {summary['topic_detail_errors']}",
        "",
        "## Practical Conclusion",
        "",
        f"- Can use for read-only comparison: {conclusion['can_use_for_read_only_comparison']}",
        f"- Blocking issues: {', '.join(conclusion['blocking_issues']) if conclusion['blocking_issues'] else 'none'}",
        f"- Review notes: {', '.join(conclusion['review_notes']) if conclusion['review_notes'] else 'none'}",
        f"- Next step: {conclusion['next_step']}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _as_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return 0


def _md_cell(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")
