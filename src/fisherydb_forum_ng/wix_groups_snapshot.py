from __future__ import annotations

import hashlib
import json
import random
import re
import shutil
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import yaml
from playwright.sync_api import BrowserContext, Page, TimeoutError as PlaywrightTimeoutError, sync_playwright
from playwright.sync_api import Error as PlaywrightError


DEFAULT_AUTH_USER = "hostmarine.office@gmail.com"
DEFAULT_BASE_URL = "https://www.fisherydb.com"
MEDIA_HOST_RE = re.compile(r"(usrfiles\.com|static\.wixstatic\.com|wixstatic\.com|dropbox\.com|drive\.google\.com)", re.I)


@dataclass(frozen=True)
class WixSnapshotConfig:
    project_root: Path
    snapshot_dir: Path
    reports_dir: Path
    auth_state_path: Path
    auth_user: str = DEFAULT_AUTH_USER
    base_url: str = DEFAULT_BASE_URL
    headful: bool = False
    throttle_min: float = 5.0
    throttle_max: float = 15.0
    save_raw_pages: bool = True
    download_media: bool = False
    max_scroll_rounds: int = 18


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_group_candidates(
    *,
    db_path: Path,
    mapping_path: Path | None,
    wix_groups_config: Path | None,
    base_url: str = DEFAULT_BASE_URL,
) -> dict[str, Any]:
    candidates: dict[str, dict[str, Any]] = {}
    if db_path.exists():
        con = sqlite3.connect(db_path)
        for slug, name, url in con.execute("SELECT slug, name, url FROM categories ORDER BY slug"):
            _add_candidate(candidates, slug, f"{base_url}/group/{slug}/discussion", "sqlite_categories", name)
            if url and "/group/" in url:
                _add_candidate(candidates, _slug_from_group_url(url) or slug, url, "sqlite_category_url", name)
    if mapping_path and mapping_path.exists():
        text = mapping_path.read_text(encoding="utf-8")
        for match in re.finditer(r"\|\s*([^|\s][^|]*?)\s*\|\s*(\d+)\s*\|", text):
            slug = match.group(1).strip()
            if slug and " " not in slug and not slug.lower().startswith("старый"):
                _add_candidate(candidates, slug, f"{base_url}/group/{slug}/discussion", "category_mapping_review", None)
        for url in sorted(set(re.findall(r"https?://[^\s)>\"]+/group/[^\s)>\"]+", text))):
            _add_candidate(candidates, _slug_from_group_url(url) or url, url, "category_mapping_review_url", None)
    if wix_groups_config and wix_groups_config.exists():
        data = yaml.safe_load(wix_groups_config.read_text(encoding="utf-8")) or {}
        for item in data.get("groups", []):
            if not isinstance(item, dict):
                continue
            slug = item.get("slug") or _slug_from_group_url(item.get("url", ""))
            url = item.get("url") or f"{base_url}/group/{slug}/discussion"
            _add_candidate(candidates, slug, url, "config_wix_groups_yaml", item.get("notes"))
    return {
        "generated_at": utc_now(),
        "count": len(candidates),
        "candidates": sorted(candidates.values(), key=lambda item: item["slug"].lower()),
    }


def write_candidates_report(candidates: dict[str, Any], path: Path) -> None:
    lines = [
        "# Wix Groups URL Candidates",
        "",
        f"Generated at: `{candidates['generated_at']}`",
        f"Candidates: {candidates['count']}",
        "",
        "| slug | url | sources | notes |",
        "|---|---|---|---|",
    ]
    for item in candidates["candidates"]:
        lines.append(
            f"| {_md(item['slug'])} | {_md(item['url'])} | {_md(', '.join(item['sources']))} | {_md(item.get('notes'))} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_auth_check(
    config: WixSnapshotConfig,
    *,
    seed_urls: list[str],
    force_login: bool = False,
    login_timeout_seconds: int = 600,
) -> dict[str, Any]:
    config.auth_state_path.parent.mkdir(parents=True, exist_ok=True)
    config.reports_dir.mkdir(parents=True, exist_ok=True)
    auth_state_used = config.auth_state_path.exists() and not force_login
    checks: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = _launch_browser(p, headless=False if force_login else not config.headful)
        context_kwargs: dict[str, Any] = {}
        if auth_state_used:
            context_kwargs["storage_state"] = str(config.auth_state_path)
        context = browser.new_context(**context_kwargs)
        page = context.new_page()
        if not auth_state_used:
            page.goto(seed_urls[0] if seed_urls else config.base_url, wait_until="domcontentloaded", timeout=60000)
            _wait_for_manual_login(page, config.auth_user, login_timeout_seconds)
            context.storage_state(path=str(config.auth_state_path))
            auth_state_used = True
        for url in seed_urls[:3]:
            checks.append(_check_seed_url(page, url, config.auth_user))
            _polite_delay(1.0, 2.5)
        context.storage_state(path=str(config.auth_state_path))
        browser.close()
    report = {
        "generated_at": utc_now(),
        "auth_mode": "authenticated",
        "auth_user": config.auth_user,
        "auth_state_path": str(config.auth_state_path),
        "auth_state_used": auth_state_used,
        "seed_checks": checks,
        "login_required_groups": sum(1 for item in checks if item["visibility_status"] == "LOGIN_REQUIRED"),
    }
    _write_json(report, config.reports_dir / "wix_auth_check.json")
    _write_auth_check_md(report, config.reports_dir / "wix_auth_check.md")
    return report


def run_snapshot(
    config: WixSnapshotConfig,
    *,
    candidates: list[dict[str, Any]],
    only_group: str | None = None,
    limit_groups: int | None = None,
    limit_discussions: int | None = None,
    resume: bool = True,
) -> dict[str, Any]:
    config.snapshot_dir.mkdir(parents=True, exist_ok=True)
    for sub in ("media", "raw_pages"):
        (config.snapshot_dir / sub).mkdir(parents=True, exist_ok=True)
    db_path = config.snapshot_dir / "wix_groups_snapshot.sqlite3"
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    _init_snapshot_db(con)
    selected = _select_candidates(candidates, only_group=only_group, limit_groups=limit_groups)
    network_urls: set[str] = set()
    with sync_playwright() as p:
        if not config.auth_state_path.exists():
            raise RuntimeError(f"Missing Wix auth state: {config.auth_state_path}. Run scripts/08a_wix_auth_check.py first.")
        browser = _launch_browser(p, headless=not config.headful)
        context = browser.new_context(storage_state=str(config.auth_state_path), accept_downloads=False)
        page = context.new_page()
        page.on("request", lambda request: _capture_network_url(network_urls, request.url))
        for group in selected:
            slug = group["slug"]
            if resume and _group_done(con, slug):
                continue
            group_result = scrape_group(page, config, group, network_urls, limit_discussions=limit_discussions)
            _save_group(con, group_result)
            for discussion in group_result.get("discussions", []):
                _save_discussion(con, discussion)
                for comment in discussion.get("comments", []):
                    _save_comment(con, comment)
                for attachment in discussion.get("attachments", []):
                    _save_attachment(con, attachment)
                con.commit()
            con.commit()
            _export_snapshot_json(con, config.snapshot_dir)
            _polite_delay(config.throttle_min, config.throttle_max)
        browser.close()
    _export_snapshot_json(con, config.snapshot_dir)
    summary = _snapshot_summary(con, config, selected)
    _write_json(summary, config.reports_dir / "wix_groups_full_snapshot.json")
    _write_snapshot_md(summary, config.reports_dir / "wix_groups_full_snapshot.md")
    _write_snapshot_summary(summary, config.reports_dir / "wix_groups_snapshot_summary.md")
    con.close()
    return summary


def scrape_group(
    page: Page,
    config: WixSnapshotConfig,
    group: dict[str, Any],
    network_urls: set[str],
    *,
    limit_discussions: int | None = None,
) -> dict[str, Any]:
    slug = group["slug"]
    url = group["url"]
    started = utc_now()
    network_urls.clear()
    page.goto(url, wait_until="domcontentloaded", timeout=90000)
    _settle(page)
    _click_show_more(page)
    _scroll_to_end(page, config.max_scroll_rounds)
    _click_show_more(page)
    _scroll_to_end(page, config.max_scroll_rounds)
    html = page.content()
    raw_path = _save_raw(config, slug, "discussion_index", html)
    visible_text = _visible_text(page)
    status = _detect_visibility(page, html, visible_text)
    discussion_links = _extract_discussion_links(page, slug, url)
    if limit_discussions is not None:
        discussion_links = discussion_links[:limit_discussions]
    discussions = []
    if status in {"PUBLIC", "EMPTY"}:
        for item in discussion_links:
            discussion = scrape_discussion(page, config, group, item, network_urls)
            discussions.append(discussion)
            _polite_delay(config.throttle_min, config.throttle_max)
    if not discussion_links and status == "PUBLIC":
        status = "EMPTY"
    return {
        "group_id": _stable_id("group", slug),
        "slug": slug,
        "url": url,
        "final_url": page.url,
        "title": _page_title(page),
        "description": None,
        "visibility_status": status,
        "discussions_count_detected": len(discussion_links),
        "scraped_at_utc": started,
        "raw_page_path": str(raw_path) if raw_path else None,
        "discussions": discussions,
    }


def scrape_discussion(
    page: Page,
    config: WixSnapshotConfig,
    group: dict[str, Any],
    link: dict[str, str],
    network_urls: set[str],
) -> dict[str, Any]:
    network_urls.clear()
    page.goto(link["url"], wait_until="domcontentloaded", timeout=90000)
    _settle(page)
    _click_show_more(page)
    _scroll_to_end(page, config.max_scroll_rounds)
    _click_show_more(page)
    html = page.content()
    text = page.locator("body").inner_text(timeout=10000)
    discussion_id = _stable_id("discussion", page.url)
    raw_path = _save_raw(config, group["slug"], discussion_id, html)
    attachments = _extract_attachments(html, network_urls, group["slug"], discussion_id, "discussion", discussion_id)
    comments = _extract_comments_from_dom(page, group["slug"], discussion_id)
    for comment in comments:
        comment["attachments_count_detected"] = 0
        comment["images_count_detected"] = 0
    title = _extract_discussion_title_from_text(text) or _best_heading(page) or link.get("title")
    return {
        "discussion_id": discussion_id,
        "group_slug": group["slug"],
        "group_url": group["url"],
        "discussion_url": page.url,
        "title": title,
        "author": _detect_author(text),
        "created_at_local": _detect_date(text),
        "created_at_utc": None,
        "updated_at_local": None,
        "body_text": text[:20000],
        "body_html": html[:500000],
        "comments_count_detected": len(comments),
        "attachments_count_detected": len([a for a in attachments if a["source_context"] != "image"]),
        "images_count_detected": len([a for a in attachments if a["source_context"] == "image"]),
        "raw_page_path": str(raw_path) if raw_path else None,
        "source_hash": _sha256_text(html),
        "comments": comments,
        "attachments": attachments,
    }


def _init_snapshot_db(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS groups (
            group_id TEXT PRIMARY KEY,
            slug TEXT,
            url TEXT,
            final_url TEXT,
            title TEXT,
            description TEXT,
            visibility_status TEXT,
            discussions_count_detected INTEGER,
            scraped_at_utc TEXT,
            raw_page_path TEXT
        );
        CREATE TABLE IF NOT EXISTS discussions (
            discussion_id TEXT PRIMARY KEY,
            group_slug TEXT,
            group_url TEXT,
            discussion_url TEXT,
            title TEXT,
            author TEXT,
            created_at_local TEXT,
            created_at_utc TEXT,
            updated_at_local TEXT,
            body_text TEXT,
            body_html TEXT,
            comments_count_detected INTEGER,
            attachments_count_detected INTEGER,
            images_count_detected INTEGER,
            raw_page_path TEXT,
            source_hash TEXT
        );
        CREATE TABLE IF NOT EXISTS comments (
            comment_id TEXT PRIMARY KEY,
            discussion_id TEXT,
            group_slug TEXT,
            author TEXT,
            created_at_local TEXT,
            created_at_utc TEXT,
            body_text TEXT,
            body_html TEXT,
            attachments_count_detected INTEGER,
            images_count_detected INTEGER,
            source_hash TEXT
        );
        CREATE TABLE IF NOT EXISTS attachments (
            attachment_id TEXT PRIMARY KEY,
            parent_type TEXT,
            parent_id TEXT,
            group_slug TEXT,
            discussion_id TEXT,
            filename TEXT,
            url TEXT,
            final_url TEXT,
            local_path TEXT,
            file_type TEXT,
            mime_type TEXT,
            size_bytes INTEGER,
            sha256 TEXT,
            status TEXT,
            source_context TEXT
        );
        """
    )
    con.commit()


def _launch_browser(playwright: Any, *, headless: bool):
    try:
        return playwright.chromium.launch(headless=headless)
    except PlaywrightError:
        return playwright.chromium.launch(channel="msedge", headless=headless)


def _save_group(con: sqlite3.Connection, group: dict[str, Any]) -> None:
    keys = [
        "group_id",
        "slug",
        "url",
        "final_url",
        "title",
        "description",
        "visibility_status",
        "discussions_count_detected",
        "scraped_at_utc",
        "raw_page_path",
    ]
    con.execute(
        f"INSERT OR REPLACE INTO groups ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)})",
        [group.get(key) for key in keys],
    )


def _save_discussion(con: sqlite3.Connection, item: dict[str, Any]) -> None:
    keys = [
        "discussion_id",
        "group_slug",
        "group_url",
        "discussion_url",
        "title",
        "author",
        "created_at_local",
        "created_at_utc",
        "updated_at_local",
        "body_text",
        "body_html",
        "comments_count_detected",
        "attachments_count_detected",
        "images_count_detected",
        "raw_page_path",
        "source_hash",
    ]
    con.execute(
        f"INSERT OR REPLACE INTO discussions ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)})",
        [item.get(key) for key in keys],
    )


def _save_comment(con: sqlite3.Connection, item: dict[str, Any]) -> None:
    keys = [
        "comment_id",
        "discussion_id",
        "group_slug",
        "author",
        "created_at_local",
        "created_at_utc",
        "body_text",
        "body_html",
        "attachments_count_detected",
        "images_count_detected",
        "source_hash",
    ]
    con.execute(
        f"INSERT OR REPLACE INTO comments ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)})",
        [item.get(key) for key in keys],
    )


def _save_attachment(con: sqlite3.Connection, item: dict[str, Any]) -> None:
    keys = [
        "attachment_id",
        "parent_type",
        "parent_id",
        "group_slug",
        "discussion_id",
        "filename",
        "url",
        "final_url",
        "local_path",
        "file_type",
        "mime_type",
        "size_bytes",
        "sha256",
        "status",
        "source_context",
    ]
    con.execute(
        f"INSERT OR REPLACE INTO attachments ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)})",
        [item.get(key) for key in keys],
    )


def _export_snapshot_json(con: sqlite3.Connection, snapshot_dir: Path) -> None:
    for table in ("groups", "discussions", "comments", "attachments"):
        rows = [dict(row) for row in con.execute(f"SELECT * FROM {table}")]
        (snapshot_dir / f"{table}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def _snapshot_summary(con: sqlite3.Connection, config: WixSnapshotConfig, selected: list[dict[str, Any]]) -> dict[str, Any]:
    group_status = CounterLike(dict(con.execute("SELECT visibility_status, COUNT(*) FROM groups GROUP BY visibility_status").fetchall()))
    attachment_status = CounterLike(dict(con.execute("SELECT status, COUNT(*) FROM attachments GROUP BY status").fetchall()))
    return {
        "generated_at": utc_now(),
        "auth_mode": "authenticated",
        "auth_user": config.auth_user,
        "auth_state_used": config.auth_state_path.exists(),
        "snapshot_dir": str(config.snapshot_dir),
        "groups_requested": len(selected),
        "groups_checked": con.execute("SELECT COUNT(*) FROM groups").fetchone()[0],
        "public_groups": group_status.get("PUBLIC", 0),
        "empty_groups": group_status.get("EMPTY", 0),
        "login_required_groups": group_status.get("LOGIN_REQUIRED", 0),
        "broken_or_not_found_groups": group_status.get("BROKEN", 0) + group_status.get("NOT_FOUND", 0),
        "discussions": con.execute("SELECT COUNT(*) FROM discussions").fetchone()[0],
        "comments": con.execute("SELECT COUNT(*) FROM comments").fetchone()[0],
        "attachments": con.execute("SELECT COUNT(*) FROM attachments").fetchone()[0],
        "attachments_downloaded": attachment_status.get("DOWNLOADED", 0),
        "attachments_remote_only": attachment_status.get("REMOTE_ONLY", 0),
        "limitations": [
            "Selectors are generic Wix Groups verification selectors and may require tuning after test run.",
            "Media downloading is disabled by default; URLs are recorded as REMOTE_ONLY unless enabled later.",
            "Current snapshot is read-only and authenticated; no comments, likes, edits, or Discourse actions are performed.",
        ],
    }


def _write_snapshot_md(summary: dict[str, Any], path: Path) -> None:
    lines = [
        "# Wix Groups Full Snapshot",
        "",
        f"- auth_mode: {summary['auth_mode']}",
        f"- auth_user: {summary['auth_user']}",
        f"- auth_state_used: {summary['auth_state_used']}",
        f"- groups checked: {summary['groups_checked']}",
        f"- public groups: {summary['public_groups']}",
        f"- empty groups: {summary['empty_groups']}",
        f"- login-required groups: {summary['login_required_groups']}",
        f"- broken/not found groups: {summary['broken_or_not_found_groups']}",
        f"- discussions: {summary['discussions']}",
        f"- comments: {summary['comments']}",
        f"- attachments/media refs: {summary['attachments']}",
        f"- attachments downloaded: {summary['attachments_downloaded']}",
        f"- attachments remote-only: {summary['attachments_remote_only']}",
        "",
        "## Limitations",
        "",
    ]
    lines.extend(f"- {item}" for item in summary["limitations"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_snapshot_summary(summary: dict[str, Any], path: Path) -> None:
    _write_snapshot_md(summary, path)


def _check_seed_url(page: Page, url: str, auth_user: str) -> dict[str, Any]:
    page.goto(url, wait_until="domcontentloaded", timeout=90000)
    _settle(page)
    html = page.content()
    text = _visible_text(page)
    return {
        "url": url,
        "final_url": page.url,
        "page_title": _page_title(page),
        "visibility_status": _detect_visibility(page, html, text),
        "auth_user_expected": auth_user,
        "auth_user_visible": auth_user.lower() in (html + text).lower(),
        "has_session_cookie": _has_session_cookie(page.context),
        "visible_discussion_link_count": len(_extract_discussion_links(page, _slug_from_group_url(url) or "", url)),
        "notes": _auth_notes(text),
    }


def _wait_for_manual_login(page: Page, auth_user: str, timeout_seconds: int) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        html = page.content()
        text = _visible_text(page)
        if _has_session_cookie(page.context) and not _login_required_text(text):
            return
        page.wait_for_timeout(3000)
    raise TimeoutError(f"Manual Wix login was not detected within {timeout_seconds} seconds for {auth_user}.")


def _detect_visibility(page: Page, html: str, visible_text: str | None = None) -> str:
    text = re.sub(r"\s+", " ", html).lower()
    visible = re.sub(r"\s+", " ", visible_text or "").lower()
    if page.url.endswith("/404") or "404" in page.title().lower() or "page not found" in text:
        return "NOT_FOUND"
    if _login_required_text(visible) and not _extract_discussion_links(page, _slug_from_group_url(page.url) or "", page.url):
        return "LOGIN_REQUIRED"
    if "something isn't working" in text or "security check" in text:
        return "BROKEN"
    if "discussion" in text or "/discussion" in text:
        return "PUBLIC"
    return "UNKNOWN"


def _login_required_text(text: str) -> bool:
    text = text.lower()
    return any(marker in text for marker in ("log in", "sign up", "members only", "please login", "войдите"))


def _extract_discussion_links(page: Page, slug: str, group_url: str) -> list[dict[str, str]]:
    anchors = page.locator("a[href]")
    links: dict[str, str] = {}
    try:
        count = min(anchors.count(), 1000)
    except PlaywrightTimeoutError:
        return []
    for index in range(count):
        anchor = anchors.nth(index)
        try:
            href = anchor.get_attribute("href") or ""
            text = re.sub(r"\s+", " ", anchor.inner_text(timeout=1000)).strip()
        except PlaywrightTimeoutError:
            continue
        url = urljoin(group_url, href)
        if _looks_like_discussion_url(url, slug) and text:
            links[url.split("?")[0]] = text[:300]
    return [{"url": url, "title": title} for url, title in sorted(links.items())]


def _looks_like_discussion_url(url: str, slug: str) -> bool:
    parsed = urlparse(url)
    if "fisherydb.com" not in parsed.netloc:
        return False
    path = parsed.path
    if f"/group/{slug}/discussion" not in path and "/group/" not in path:
        return False
    return path.rstrip("/").count("/") >= 4 and not path.rstrip("/").endswith("/discussion")


def _extract_comments_from_dom(page: Page, group_slug: str, discussion_id: str) -> list[dict[str, Any]]:
    text = page.locator("body").inner_text(timeout=10000)
    # Wix comments are highly dynamic; this conservative fallback records likely comment blocks
    # only when the DOM exposes repeated comment-like containers.
    candidates = []
    for selector in ("[data-hook*='comment']", "[class*='comment']", "[aria-label*='comment' i]"):
        loc = page.locator(selector)
        try:
            count = min(loc.count(), 200)
        except PlaywrightTimeoutError:
            continue
        for index in range(count):
            try:
                body = re.sub(r"\s+", " ", loc.nth(index).inner_text(timeout=1000)).strip()
            except PlaywrightTimeoutError:
                continue
            if len(body) < 20 or body in text[:500]:
                continue
            comment_id = _stable_id("comment", discussion_id, body)
            candidates.append(
                {
                    "comment_id": comment_id,
                    "discussion_id": discussion_id,
                    "group_slug": group_slug,
                    "author": _detect_author(body),
                    "created_at_local": _detect_date(body),
                    "created_at_utc": None,
                    "body_text": body,
                    "body_html": None,
                    "source_hash": _sha256_text(body),
                }
            )
    unique = {item["comment_id"]: item for item in candidates}
    return list(unique.values())


def _extract_attachments(
    html: str,
    network_urls: set[str],
    group_slug: str,
    discussion_id: str,
    parent_type: str,
    parent_id: str,
) -> list[dict[str, Any]]:
    urls = set(re.findall(r"https?://[^\"'\s<>]+", html))
    urls.update(network_urls)
    attachments = []
    for url in sorted(urls):
        if not MEDIA_HOST_RE.search(url) and not _has_file_extension(url):
            continue
        filename = _filename_from_url(url)
        source_context = "image" if re.search(r"\.(jpg|jpeg|png|gif|webp)(?:[?#]|$)", url, re.I) or "wixstatic" in url else "embedded_media"
        attachments.append(
            {
                "attachment_id": _stable_id("attachment", parent_id, url),
                "parent_type": parent_type,
                "parent_id": parent_id,
                "group_slug": group_slug,
                "discussion_id": discussion_id,
                "filename": filename,
                "url": url,
                "final_url": None,
                "local_path": None,
                "file_type": (filename.rsplit(".", 1)[-1].lower() if "." in filename else None),
                "mime_type": None,
                "size_bytes": None,
                "sha256": None,
                "status": "REMOTE_ONLY",
                "source_context": source_context,
            }
        )
    return attachments


def _click_show_more(page: Page) -> None:
    labels = re.compile(r"(show more|load more|view more|more comments|ещ[её]|показать)", re.I)
    for _ in range(6):
        clicked = False
        buttons = page.get_by_role("button")
        try:
            count = min(buttons.count(), 100)
        except PlaywrightTimeoutError:
            break
        for index in range(count):
            button = buttons.nth(index)
            try:
                text = button.inner_text(timeout=500)
                if labels.search(text):
                    button.click(timeout=1000)
                    page.wait_for_timeout(1500)
                    clicked = True
            except Exception:
                continue
        if not clicked:
            break


def _scroll_to_end(page: Page, max_rounds: int) -> None:
    last_height = 0
    stable = 0
    for _ in range(max_rounds):
        height = page.evaluate("() => document.body.scrollHeight")
        page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1800)
        if height == last_height:
            stable += 1
        else:
            stable = 0
        if stable >= 3:
            break
        last_height = height


def _settle(page: Page) -> None:
    page.wait_for_timeout(2500)
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except PlaywrightTimeoutError:
        pass


def _save_raw(config: WixSnapshotConfig, slug: str, name: str, html: str) -> Path | None:
    if not config.save_raw_pages:
        return None
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", name)[:120]
    path = config.snapshot_dir / "raw_pages" / slug / f"{safe}.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path


def _group_done(con: sqlite3.Connection, slug: str) -> bool:
    row = con.execute("SELECT 1 FROM groups WHERE slug = ?", (slug,)).fetchone()
    return bool(row)


def _select_candidates(candidates: list[dict[str, Any]], only_group: str | None, limit_groups: int | None) -> list[dict[str, Any]]:
    selected = candidates
    if only_group:
        selected = [item for item in selected if item["slug"].lower() == only_group.lower()]
    if limit_groups is not None:
        selected = selected[:limit_groups]
    return selected


def _capture_network_url(network_urls: set[str], url: str) -> None:
    if MEDIA_HOST_RE.search(url):
        network_urls.add(url)


def _add_candidate(candidates: dict[str, dict[str, Any]], slug: str | None, url: str, source: str, notes: str | None) -> None:
    if not slug:
        return
    item = candidates.setdefault(slug, {"slug": slug, "url": url, "sources": [], "notes": notes})
    if source not in item["sources"]:
        item["sources"].append(source)
    if notes and not item.get("notes"):
        item["notes"] = notes


def _slug_from_group_url(url: str) -> str | None:
    match = re.search(r"/group/([^/?#]+)/", url or "")
    return match.group(1) if match else None


def _stable_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:24]


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def _filename_from_url(url: str) -> str:
    path = urlparse(url).path
    name = path.rstrip("/").split("/")[-1] or _stable_id("file", url)
    return name.split("?")[0]


def _has_file_extension(url: str) -> bool:
    return bool(re.search(r"\.(pdf|docx?|xlsx?|zip|rar|jpg|jpeg|png|gif|webp|mp4|mov)(?:[?#]|$)", url, re.I))


def _page_title(page: Page) -> str | None:
    try:
        return page.title()
    except Exception:
        return None


def _best_heading(page: Page) -> str | None:
    for selector in ("h1", "h2", "[role='heading']"):
        loc = page.locator(selector)
        try:
            count = min(loc.count(), 20)
            for index in range(count):
                text = re.sub(r"\s+", " ", loc.nth(index).inner_text(timeout=1000)).strip()
                if _looks_like_real_title(text):
                    return text
        except PlaywrightTimeoutError:
            continue
    return _page_title(page)


def _looks_like_real_title(text: str | None) -> bool:
    if not text:
        return False
    text = text.strip()
    if len(text) < 4:
        return False
    if re.fullmatch(r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}", text, re.I):
        return False
    if text.lower() in {"discussion", "comments", "log in", "sign up"}:
        return False
    return True


def _detect_author(text: str) -> str | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[1] if len(lines) > 1 and len(lines[1]) < 80 else None


def _detect_date(text: str) -> str | None:
    match = re.search(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b|\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b", text, re.I)
    return match.group(0) if match else None


def _extract_discussion_title_from_text(text: str) -> str | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if _detect_date(line):
            for candidate in lines[index + 1 : index + 8]:
                if _looks_like_real_title(candidate) and candidate.lower() not in {"like", "reply", "write a comment..."}:
                    return candidate
    return None


def _has_session_cookie(context: BrowserContext) -> bool:
    session_names = {"smsession", "svsession", "wixsession2", "wixclient", "hs", "ssr-caching"}
    return any(cookie.get("name", "").lower() in session_names for cookie in context.cookies())


def _visible_text(page: Page) -> str:
    try:
        return page.locator("body").inner_text(timeout=10000)
    except Exception:
        return ""


def _auth_notes(text: str) -> str:
    if _login_required_text(text):
        return "Login-required text is visible."
    return "Session cookie/page access detected; user email may not be visible in DOM."


def _polite_delay(low: float, high: float) -> None:
    time.sleep(random.uniform(low, high))


def _write_json(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_auth_check_md(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Wix Auth Check",
        "",
        f"- auth_mode: {report['auth_mode']}",
        f"- auth_user: {report['auth_user']}",
        f"- auth_state_used: {report['auth_state_used']}",
        f"- login_required_groups: {report['login_required_groups']}",
        "",
        "| url | final_url | status | title | session cookie | user visible | notes |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in report["seed_checks"]:
        lines.append(
            f"| {_md(item['url'])} | {_md(item['final_url'])} | {item['visibility_status']} | {_md(item['page_title'])} | "
            f"{item['has_session_cookie']} | {item['auth_user_visible']} | {_md(item['notes'])} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _md(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


class CounterLike(dict):
    def get(self, key: str, default: int = 0) -> int:
        return int(super().get(key, default) or 0)
