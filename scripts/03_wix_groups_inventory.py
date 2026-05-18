from __future__ import annotations

import argparse
import json
import random
import re
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = Path(r"E:\OneDrive\Documents\Claude\projects\fisherydb-forum-parser")
DEFAULT_AUTH_STATE = PROJECT_ROOT / "data" / "working" / "wix_auth_state.json"
DEFAULT_BROWSER = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

LOGIN_MARKERS = [
    "log in",
    "login",
    "sign up",
    "members only",
    "join this group",
    "please log in",
]
BROKEN_MARKERS = [
    "page not found",
    "404",
    "something isn't working",
    "wix forum is no longer available",
    "this group can't be found",
    "this group can’t be found",
]
EMPTY_MARKERS = [
    "no posts",
    "nothing here",
    "no discussions",
    "start a discussion",
    "create the first post",
]
DATE_RE = re.compile(
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b"
    r"|\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b"
    r"|\b\d{4}-\d{2}-\d{2}\b",
    re.IGNORECASE,
)


@dataclass
class GroupSeed:
    slug: str
    tested_url: str
    source: str
    notes: str = ""


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only Wix Groups inventory. Uses SQLite slugs plus config/wix_groups.yaml "
            "seeds. Does not log in by itself, download files, or touch Discourse."
        )
    )
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--config", default=str(PROJECT_ROOT / "config" / "wix_groups.yaml"))
    parser.add_argument("--reports-dir", default=str(PROJECT_ROOT / "data" / "reports"))
    parser.add_argument("--auth-state", default=str(DEFAULT_AUTH_STATE))
    parser.add_argument("--browser", default=str(DEFAULT_BROWSER))
    parser.add_argument("--min-delay", type=float, default=2.0)
    parser.add_argument("--max-delay", type=float, default=5.0)
    parser.add_argument("--wait-ms", type=int, default=2000)
    parser.add_argument("--limit", type=int, default=0, help="Optional test limit.")
    args = parser.parse_args()

    root = Path(args.root)
    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    seeds = build_group_seed_list(root, Path(args.config))
    if args.limit:
        seeds = seeds[: args.limit]

    report = run_inventory(
        seeds=seeds,
        root=root,
        auth_state=Path(args.auth_state),
        browser=Path(args.browser),
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        wait_ms=args.wait_ms,
    )

    json_path = reports_dir / "wix_groups_inventory.json"
    md_path = reports_dir / "wix_groups_inventory.md"
    summary_path = reports_dir / "wix_groups_summary.md"
    write_json(report, json_path)
    write_markdown(report, md_path)
    write_summary(report, summary_path)

    summary = report["summary"]
    print("Wix Groups inventory completed.")
    print(f"Checked slugs: {summary['checked_slugs']}")
    print(f"Public/accessibly content: {summary['public_with_content']}")
    print(f"Public empty: {summary['public_empty']}")
    print(f"Private/login required: {summary['private_or_login_required']}")
    print(f"Broken/not found: {summary['not_found_or_broken']}")
    print(f"Unknown: {summary['unknown']}")
    print(f"Report JSON: {json_path}")
    print(f"Report Markdown: {md_path}")
    print(f"Summary Markdown: {summary_path}")
    return 0


def build_group_seed_list(root: Path, config_path: Path) -> list[GroupSeed]:
    seeds: dict[str, GroupSeed] = {}
    db_path = root / "output" / "forum_data.db"
    if db_path.exists():
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            for (slug,) in con.execute("select slug from categories order by slug"):
                url = f"https://www.fisherydb.com/group/{slug}/discussion"
                seeds.setdefault(slug, GroupSeed(slug=slug, tested_url=url, source="sqlite"))
        finally:
            con.close()

    if config_path.exists():
        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        for item in config.get("groups", []):
            if not isinstance(item, dict) or not item.get("slug"):
                continue
            slug = str(item["slug"])
            url = str(item.get("url") or f"https://www.fisherydb.com/group/{slug}/discussion")
            if slug in seeds:
                seeds[slug].tested_url = url
                seeds[slug].source = f"{seeds[slug].source}+seed"
                seeds[slug].notes = str(item.get("notes") or "")
            else:
                seeds[slug] = GroupSeed(
                    slug=slug,
                    tested_url=url,
                    source="seed",
                    notes=str(item.get("notes") or ""),
                )

    return [seeds[slug] for slug in sorted(seeds)]


def run_inventory(
    seeds: list[GroupSeed],
    root: Path,
    auth_state: Path,
    browser: Path,
    min_delay: float,
    max_delay: float,
    wait_ms: int,
) -> dict[str, Any]:
    local_titles = load_local_titles(root)
    local_counts = load_local_counts(root)
    started_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    results = []
    warnings = []

    if not browser.exists():
        raise SystemExit(f"Browser executable not found: {browser}")
    if not auth_state.exists():
        warnings.append(f"Auth state not found; inventory will run without stored login: {auth_state}")

    with sync_playwright() as p:
        browser_obj = p.chromium.launch(
            executable_path=str(browser),
            headless=True,
            args=["--disable-dev-shm-usage"],
        )
        context_kwargs: dict[str, Any] = {
            "user_agent": USER_AGENT,
            "viewport": {"width": 1365, "height": 900},
            "accept_downloads": False,
        }
        if auth_state.exists():
            context_kwargs["storage_state"] = str(auth_state)
        context = browser_obj.new_context(**context_kwargs)
        context.route("**/*", route_request_lightly)

        page = context.new_page()
        for index, seed in enumerate(seeds, start=1):
            print(f"[{index}/{len(seeds)}] {seed.slug} -> {seed.tested_url}")
            result = check_group(
                page,
                seed,
                local_titles.get(seed.slug, []),
                local_counts.get(seed.slug, {}),
                wait_ms,
            )
            results.append(result)
            if index < len(seeds):
                delay = random.uniform(min_delay, max_delay)
                time.sleep(delay)

        context.close()
        browser_obj.close()

    summary = summarize_results(results)
    return {
        "started_at": started_at,
        "root": str(root),
        "auth_state_used": auth_state.exists(),
        "auth_state_path": str(auth_state),
        "scope": {
            "read_only": True,
            "discourse_touched": False,
            "downloads_enabled": False,
            "mass_post_parsing": False,
            "deep_scrolling": False,
        },
        "warnings": warnings,
        "summary": summary,
        "groups": results,
    }


def route_request_lightly(route: Any) -> None:
    request = route.request
    try:
        if request.resource_type in {"image", "media", "font"}:
            route.abort()
            return
        if re.search(r"\.(pdf|zip|rar|7z|docx?|xlsx?)(\?|$)", request.url, re.IGNORECASE):
            route.abort()
            return
        route.continue_()
    except Exception:
        return


def load_local_titles(root: Path) -> dict[str, list[str]]:
    db_path = root / "output" / "forum_data.db"
    titles: dict[str, list[str]] = defaultdict(list)
    if not db_path.exists():
        return titles
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        for slug, title in con.execute(
            "select category_slug, title from threads where coalesce(trim(title), '') <> '' order by category_slug, title"
        ):
            titles[slug].append(title)
    finally:
        con.close()
    return titles


def load_local_counts(root: Path) -> dict[str, dict[str, int]]:
    db_path = root / "output" / "forum_data.db"
    counts: dict[str, dict[str, int]] = {}
    if not db_path.exists():
        return counts
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        for slug, threads, posts in con.execute(
            """
            select c.slug, count(distinct t.id) as threads, count(p.id) as posts
            from categories c
            left join threads t on t.category_slug = c.slug
            left join posts p on p.thread_id = t.id
            group by c.slug
            """
        ):
            counts[slug] = {"threads": int(threads or 0), "posts": int(posts or 0)}
    finally:
        con.close()
    return counts


def check_group(
    page: Any,
    seed: GroupSeed,
    local_titles: list[str],
    local_count: dict[str, int],
    wait_ms: int,
) -> dict[str, Any]:
    notes = []
    http_status = None
    final_url = None
    page_title = ""
    detected_group_title = ""
    visible_topic_titles_sample: list[str] = []
    visible_dates_sample: list[str] = []

    try:
        response = page.goto(seed.tested_url, wait_until="domcontentloaded", timeout=45000)
        if response is not None:
            http_status = response.status
        page.wait_for_timeout(wait_ms)
        final_url = page.url
        page_title = safe_page_title(page)
        html = page.content()
        text = visible_text_from_html(html)
        detected_group_title = detect_group_title(html, page_title, seed.slug)
        visible_topic_titles_sample = detect_visible_titles(html, text, local_titles)
        visible_dates_sample = valid_date_candidates(text)[:10]
        status = classify_group(
            http_status,
            final_url,
            page_title,
            text,
            visible_topic_titles_sample,
            visible_dates_sample,
        )
    except PlaywrightTimeoutError as exc:
        status = "UNKNOWN"
        notes.append(f"Timeout: {exc}")
    except Exception as exc:  # noqa: BLE001 - inventory should keep moving.
        status = "UNKNOWN"
        notes.append(f"Error: {type(exc).__name__}: {exc}")

    if seed.notes:
        notes.append(seed.notes)
    if seed.source:
        notes.append(f"source={seed.source}")

    return {
        "slug": seed.slug,
        "tested_url": seed.tested_url,
        "http_status": http_status,
        "final_url": final_url,
        "page_title": page_title,
        "detected_group_title": detected_group_title,
        "status": status,
        "visible_topic_titles_sample": visible_topic_titles_sample[:10],
        "visible_dates_sample": visible_dates_sample[:10],
        "local_thread_count": local_count.get("threads", 0),
        "local_post_count": local_count.get("posts", 0),
        "notes": notes,
    }


def safe_page_title(page: Any) -> str:
    try:
        return page.title()
    except Exception:
        return ""


def visible_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())


def detect_group_title(html: str, page_title: str, slug: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    candidates = []
    for selector in ["h1", "h2", "[role='heading']"]:
        for node in soup.select(selector):
            text = clean_text(node.get_text(" ", strip=True))
            if is_title_like(text):
                candidates.append(text)
    candidates = unique(candidates)
    if candidates:
        return candidates[0]
    if page_title and page_title.lower() not in {"fisherydb"}:
        return page_title
    return slug


def detect_visible_titles(html: str, text: str, local_titles: list[str]) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    candidates = []
    for selector in ["a", "h2", "h3", "h4", "[role='heading']"]:
        for node in soup.select(selector):
            item = clean_text(node.get_text(" ", strip=True))
            if is_topic_candidate(item):
                candidates.append(item)

    lower_text = text.lower()
    for title in local_titles:
        if title and title.lower() in lower_text:
            candidates.append(title)

    return unique(candidates)[:10]


def classify_group(
    http_status: int | None,
    final_url: str | None,
    page_title: str,
    text: str,
    title_sample: list[str],
    date_sample: list[str],
) -> str:
    combined = " ".join([final_url or "", page_title or "", text or ""]).lower()
    if http_status in {404, 410} or any(marker in combined for marker in BROKEN_MARKERS):
        return "NOT_FOUND_OR_BROKEN"
    if any(marker in combined for marker in LOGIN_MARKERS):
        if not title_sample:
            return "PRIVATE_OR_LOGIN_REQUIRED"
    if title_sample or len(date_sample) >= 2:
        return "PUBLIC_WITH_CONTENT"
    if any(marker in combined for marker in EMPTY_MARKERS):
        return "PUBLIC_EMPTY"
    if http_status and 200 <= http_status < 400:
        return "PUBLIC_EMPTY"
    return "NOT_FOUND_OR_BROKEN" if http_status and http_status >= 400 else "UNKNOWN"


def is_title_like(text: str) -> bool:
    return 2 <= len(text) <= 160 and not is_boilerplate(text)


def is_topic_candidate(text: str) -> bool:
    if not (6 <= len(text) <= 180):
        return False
    if is_boilerplate(text):
        return False
    if DATE_RE.fullmatch(text.strip()):
        return False
    if text.lower().startswith(("http://", "https://")):
        return False
    if "@" in text and "." in text:
        return False
    return True


def is_boilerplate(text: str) -> bool:
    value = clean_text(text).lower()
    boilerplate = {
        "database",
        "home",
        "about",
        "contact",
        "members",
        "groups",
        "see all members",
        "discussion",
        "discussions",
        "log in",
        "login",
        "sign up",
        "share",
        "follow",
        "notifications",
        "create post",
        "create the first post",
        "write a post",
        "go to group list",
        "request to join this group",
        "wix.com",
        "search",
        "menu",
        "fisherydb",
        "fishery group",
        "openai",
        "hostmarineoffice",
    }
    return (
        value in boilerplate
        or value.startswith("©")
        or value.startswith("see all members")
    )


def valid_date_candidates(text: str) -> list[str]:
    candidates = []
    for value in DATE_RE.findall(text):
        clean = clean_text(value)
        if re.match(r"^\d{1,2}[./-]\d{1,2}[./-]\d{2,4}$", clean):
            parts = [int(part) for part in re.split(r"[./-]", clean)]
            if len(parts) == 3 and 1 <= parts[0] <= 31 and 1 <= parts[1] <= 12:
                candidates.append(clean)
        else:
            candidates.append(clean)
    return unique(candidates)


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        item = clean_text(str(value))
        key = item.lower()
        if item and key not in seen:
            seen.add(key)
            result.append(item)
    return result


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(item["status"] for item in results)
    important = [
        item
        for item in results
        if (
            item["status"] == "PUBLIC_WITH_CONTENT"
            and item.get("local_thread_count", 0) == 0
        )
        or item["status"] == "UNKNOWN"
    ]
    missing_content_signals = [
        {
            "slug": item["slug"],
            "tested_url": item["tested_url"],
            "status": item["status"],
            "topic_sample_count": len(item.get("visible_topic_titles_sample", [])),
            "notes": item.get("notes", []),
        }
        for item in important[:50]
    ]
    return {
        "checked_slugs": len(results),
        "public_with_content": counts.get("PUBLIC_WITH_CONTENT", 0),
        "public_empty": counts.get("PUBLIC_EMPTY", 0),
        "private_or_login_required": counts.get("PRIVATE_OR_LOGIN_REQUIRED", 0),
        "not_found_or_broken": counts.get("NOT_FOUND_OR_BROKEN", 0),
        "unknown": counts.get("UNKNOWN", 0),
        "important_for_manual_review": missing_content_signals,
        "evidence_of_substantial_content_missing_locally": "UNKNOWN_PENDING_MANUAL_REVIEW",
        "notes": [
            "This inventory is authenticated read-only if auth_state_used=true.",
            "It does not compare Discourse and does not parse full post bodies.",
            "Visible title samples are heuristic because Wix Groups are JavaScript-rendered.",
        ],
    }


def write_json(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Wix Groups Inventory",
        "",
        f"Auth state used: **{report.get('auth_state_used')}**",
        "",
        "## Summary",
        "",
    ]
    summary = report["summary"]
    rows = [
        ("Checked slugs", summary["checked_slugs"]),
        ("PUBLIC_WITH_CONTENT", summary["public_with_content"]),
        ("PUBLIC_EMPTY", summary["public_empty"]),
        ("PRIVATE_OR_LOGIN_REQUIRED", summary["private_or_login_required"]),
        ("NOT_FOUND_OR_BROKEN", summary["not_found_or_broken"]),
        ("UNKNOWN", summary["unknown"]),
    ]
    append_kv_table(lines, rows)
    lines.extend(["## Groups", ""])
    lines.append("| Slug | HTTP | Status | Title | Topics sample | URL |")
    lines.append("|---|---:|---|---|---|---|")
    for item in report["groups"]:
        sample = "; ".join(item.get("visible_topic_titles_sample", [])[:3])
        lines.append(
            f"| `{item['slug']}` | {item.get('http_status') or ''} | {item['status']} | "
            f"{escape_cell(item.get('detected_group_title') or item.get('page_title') or '')} | "
            f"{escape_cell(sample)} | {item.get('final_url') or item.get('tested_url')} |"
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_summary(report: dict[str, Any], path: Path) -> None:
    summary = report["summary"]
    lines = [
        "# Wix Groups Summary",
        "",
        "Phase 2 read-only Wix Groups verification. No Discourse operations were performed.",
        "",
        f"- Slugs checked: **{summary['checked_slugs']}**",
        f"- Public/accessibly with content: **{summary['public_with_content']}**",
        f"- Public empty: **{summary['public_empty']}**",
        f"- Private/login required: **{summary['private_or_login_required']}**",
        f"- Broken/not found: **{summary['not_found_or_broken']}**",
        f"- Unknown: **{summary['unknown']}**",
        "",
        "## Important For Manual Review",
        "",
    ]
    important = summary.get("important_for_manual_review", [])
    if important:
        for item in important:
            lines.append(
                f"- `{item['slug']}`: {item['status']}, "
                f"topic sample count={item['topic_sample_count']}, {item['tested_url']}"
            )
    else:
        lines.append("_None._")
    lines.extend(
        [
            "",
            "## Missing Local Content Signal",
            "",
            f"Evidence of substantial Wix Groups content absent locally: **{summary['evidence_of_substantial_content_missing_locally']}**",
            "",
            "This pass is a lightweight inventory. It can flag groups for manual review, but it does not prove full content equivalence.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def append_kv_table(lines: list[str], rows: list[tuple[str, Any]]) -> None:
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    for key, value in rows:
        lines.append(f"| {key} | {value} |")
    lines.append("")


def escape_cell(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    raise SystemExit(main())
