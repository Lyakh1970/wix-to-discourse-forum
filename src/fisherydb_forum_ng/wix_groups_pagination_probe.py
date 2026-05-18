from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, Response, TimeoutError as PlaywrightTimeoutError, sync_playwright


DEFAULT_GROUPS = [
    "catsat",
    "ft-issues",
    "marport",
    "fs-issues",
    "km-issues",
    "marport-1",
    "trondheim-issues",
]

SLUG_ALIASES = {
    "ft-issues": "trondheim-issues",
}

NETWORK_KEYWORDS = (
    "wix",
    "groups",
    "forum",
    "discussion",
    "posts",
    "feed",
    "social",
    "communities",
    "_api",
    "graphql",
)


@dataclass(frozen=True)
class ProbeConfig:
    project_root: Path
    auth_state_path: Path
    reports_dir: Path
    december_db: Path
    headful: bool = False
    scroll_rounds: int = 14
    wait_ms: int = 1800
    direct_limit: int = 5
    base_url: str = "https://www.fisherydb.com"


def run_pagination_probe(config: ProbeConfig, groups: list[str] | None = None) -> dict[str, Any]:
    selected_groups = groups or DEFAULT_GROUPS
    expected = _load_expected_threads(config.december_db)
    results = []
    with sync_playwright() as p:
        browser = _launch_browser(p, headless=not config.headful)
        context = browser.new_context(storage_state=str(config.auth_state_path))
        for slug in selected_groups:
            page = context.new_page()
            network_events: list[dict[str, Any]] = []
            json_link_candidates: set[str] = set()
            page.on("response", lambda response, events=network_events, links=json_link_candidates: _capture_response(response, events, links))
            result = probe_group(page, config, slug, expected.get(_expected_slug(slug), []), network_events, json_link_candidates)
            results.append(result)
            page.close()
        browser.close()
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "auth_mode": "authenticated",
        "auth_state_used": config.auth_state_path.exists(),
        "groups": results,
        "recommendation": _recommendation(results),
    }
    write_probe_reports(report, config.reports_dir)
    return report


def probe_group(
    page: Page,
    config: ProbeConfig,
    slug: str,
    expected_threads: list[dict[str, Any]],
    network_events: list[dict[str, Any]],
    json_link_candidates: set[str],
) -> dict[str, Any]:
    url = f"{config.base_url}/group/{slug}/discussion"
    page.goto(url, wait_until="domcontentloaded", timeout=90000)
    _settle(page, config.wait_ms)
    initial_links = _discussion_links(page, slug, url)
    scroll_counts = [{"round": 0, "count": len(initial_links)}]
    for index in range(1, config.scroll_rounds + 1):
        page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(config.wait_ms)
        links = _discussion_links(page, slug, url)
        scroll_counts.append({"round": index, "count": len(links)})
        if len(scroll_counts) >= 4 and len({item["count"] for item in scroll_counts[-4:]}) == 1:
            break
    after_scroll_links = _discussion_links(page, slug, url)
    button_counts = _button_strategy(page, slug, url, config.wait_ms)
    after_buttons_links = _discussion_links(page, slug, url)
    hydration = _hydration_probe(page)
    direct = _direct_url_strategy(page, config, slug, expected_threads)
    network_summary = _network_summary(network_events)
    best_count = max(
        len(after_buttons_links),
        len(after_scroll_links),
        len(json_link_candidates),
        len(hydration["discussion_like_items"]),
    )
    expected_count = len(expected_threads)
    confidence = _confidence(best_count, expected_count, network_summary, direct)
    best_strategy = _best_strategy(
        {
            "dom_scroll": len(after_scroll_links),
            "buttons": len(after_buttons_links),
            "network_json": len(json_link_candidates),
            "hydration_state": len(hydration["discussion_like_items"]),
        }
    )
    notes = []
    if expected_count and best_count < expected_count:
        notes.append("Discovered count is lower than December expected count.")
    if direct["success_count"] and best_count < expected_count:
        notes.append("Direct known December URLs/slugs open while index remains incomplete.")
    if network_summary["json_response_count"] == 0:
        notes.append("No useful JSON/XHR pagination response captured.")
    if not notes:
        notes.append("Probe did not find an obvious gap for this group.")
    return {
        "slug": slug,
        "url": url,
        "expected_december_slug": _expected_slug(slug),
        "expected_december_threads": expected_count,
        "discovered_links_initial": len(initial_links),
        "discovered_links_after_scroll": len(after_scroll_links),
        "scroll_counts": scroll_counts,
        "button_counts": button_counts,
        "discovered_links_after_buttons": len(after_buttons_links),
        "discovered_links_from_network_json": len(json_link_candidates),
        "discovered_links_from_hydration_state": len(hydration["discussion_like_items"]),
        "direct_known_thread_open_success_count": direct["success_count"],
        "direct_known_thread_attempts": direct["attempts"],
        "best_strategy": best_strategy,
        "confidence": confidence,
        "network": network_summary,
        "hydration": hydration,
        "sample_links": sorted(after_buttons_links or after_scroll_links)[:10],
        "notes": notes,
    }


def write_probe_reports(report: dict[str, Any], reports_dir: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "wix_groups_pagination_probe.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    lines = [
        "# Wix Groups Pagination Probe",
        "",
        f"Generated at: `{report['generated_at']}`",
        f"auth_mode: `{report['auth_mode']}`",
        f"auth_state_used: `{report['auth_state_used']}`",
        "",
        "| slug | expected | initial | after scroll | after buttons | network JSON links | hydration links | direct success | best strategy | confidence | notes |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for item in report["groups"]:
        lines.append(
            f"| {_md(item['slug'])} | {item['expected_december_threads']} | {item['discovered_links_initial']} | "
            f"{item['discovered_links_after_scroll']} | {item['discovered_links_after_buttons']} | "
            f"{item['discovered_links_from_network_json']} | {item['discovered_links_from_hydration_state']} | "
            f"{item['direct_known_thread_open_success_count']} | {item['best_strategy']} | {item['confidence']} | "
            f"{_md('; '.join(item['notes']))} |"
        )
    lines.extend(["", "## Network/API Signals", ""])
    for item in report["groups"]:
        net = item["network"]
        lines.append(
            f"- `{item['slug']}`: relevant responses={net['relevant_response_count']}, "
            f"json responses={net['json_response_count']}, likely API endpoints={len(net['likely_api_endpoints'])}"
        )
        for endpoint in net["likely_api_endpoints"][:8]:
            lines.append(f"  - `{endpoint['method']} {endpoint['status']} {endpoint['url']}` ({endpoint['content_type']}, {endpoint['response_size']})")
    lines.extend(["", "## Recommendation", ""])
    lines.append(report["recommendation"]["summary"])
    for item in report["recommendation"]["actions"]:
        lines.append(f"- {item}")
    (reports_dir / "wix_groups_pagination_probe.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _load_expected_threads(db_path: Path) -> dict[str, list[dict[str, Any]]]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT id, category_slug, title, url FROM threads ORDER BY category_slug, created_at, id"
    ).fetchall()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["category_slug"], []).append(dict(row))
    con.close()
    return grouped


def _discussion_links(page: Page, slug: str, base_url: str) -> set[str]:
    links: set[str] = set()
    anchors = page.locator("a[href]")
    try:
        count = min(anchors.count(), 1500)
    except PlaywrightTimeoutError:
        return links
    for index in range(count):
        anchor = anchors.nth(index)
        try:
            href = anchor.get_attribute("href") or ""
        except PlaywrightTimeoutError:
            continue
        url = urljoin(base_url, href).split("?")[0]
        if _looks_like_discussion_url(url, slug):
            links.add(url)
    return links


def _button_strategy(page: Page, slug: str, base_url: str, wait_ms: int) -> list[dict[str, Any]]:
    labels = re.compile(r"(show more|load more|more posts|see more|показать больше|ещ[её])", re.I)
    counts = []
    for attempt in range(8):
        clicked = False
        buttons = page.get_by_role("button")
        try:
            count = min(buttons.count(), 150)
        except PlaywrightTimeoutError:
            break
        for index in range(count):
            button = buttons.nth(index)
            try:
                text = button.inner_text(timeout=600)
                if labels.search(text):
                    button.click(timeout=1500)
                    page.wait_for_timeout(wait_ms)
                    clicked = True
                    break
            except Exception:
                continue
        links = _discussion_links(page, slug, base_url)
        counts.append({"attempt": attempt + 1, "clicked": clicked, "count": len(links)})
        if not clicked:
            break
    return counts


def _capture_response(response: Response, events: list[dict[str, Any]], json_link_candidates: set[str]) -> None:
    url = response.url
    lowered = url.lower()
    if not any(keyword in lowered for keyword in NETWORK_KEYWORDS):
        return
    headers = response.headers
    content_type = headers.get("content-type", "")
    event = {
        "url": _sanitize_url(url),
        "method": response.request.method,
        "status": response.status,
        "content_type": content_type.split(";")[0],
        "response_size": _parse_int(headers.get("content-length")),
        "sample": None,
        "extracted_discussion_links": 0,
    }
    if _is_sensitive_endpoint(url):
        event["sample"] = "<redacted sensitive endpoint>"
        events.append(event)
        return
    if "json" in content_type.lower():
        try:
            text = response.text()
            event["response_size"] = len(text)
            sample = _sanitize_json_text(text[:4000])
            event["sample"] = sample[:1500]
            links = _extract_discussion_urls_from_text(text, response.url)
            json_link_candidates.update(links)
            event["extracted_discussion_links"] = len(links)
        except Exception as exc:
            event["sample"] = f"<unreadable json/text: {type(exc).__name__}>"
    events.append(event)


def _network_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    likely = [
        item
        for item in events
        if item["status"] < 400
        and (
            "json" in item.get("content_type", "").lower()
            or any(part in item["url"].lower() for part in ("/_api", "graphql", "discussion", "feed", "posts"))
        )
    ]
    return {
        "relevant_response_count": len(events),
        "json_response_count": sum(1 for item in events if "json" in item.get("content_type", "").lower()),
        "likely_api_endpoints": likely[:25],
    }


def _hydration_probe(page: Page) -> dict[str, Any]:
    result = page.evaluate(
        """
        () => {
          const out = [];
          const scan = (name, value) => {
            try {
              const text = JSON.stringify(value);
              if (text && /discussion|post|group/i.test(text)) {
                out.push({name, size: text.length, sample: text.slice(0, 1200)});
              }
            } catch (e) {}
          };
          ['__INITIAL_STATE__','__WIX_DATA__','viewerModel','warmupData','wixBiSession'].forEach(k => scan('window.' + k, window[k]));
          document.querySelectorAll('script[type="application/json"],script[type="application/ld+json"]').forEach((el, idx) => {
            const text = el.textContent || '';
            if (/discussion|post|group/i.test(text)) out.push({name: 'script_json_' + idx, size: text.length, sample: text.slice(0, 1200)});
          });
          return out.slice(0, 20);
        }
        """
    )
    discussion_like = set()
    for item in result:
        sample = item.get("sample") or ""
        discussion_like.update(_extract_discussion_urls_from_text(sample, page.url))
    return {
        "state_blob_count": len(result),
        "state_blobs": [_sanitize_state_blob(item) for item in result],
        "discussion_like_items": sorted(discussion_like),
    }


def _direct_url_strategy(
    page: Page,
    config: ProbeConfig,
    slug: str,
    expected_threads: list[dict[str, Any]],
) -> dict[str, Any]:
    attempts = []
    for thread in expected_threads[: config.direct_limit]:
        candidates = []
        if thread.get("url"):
            candidates.append(thread["url"])
        candidates.append(f"{config.base_url}/group/{slug}/discussion/{thread['id']}")
        success = False
        final_url = None
        status = None
        for url in candidates:
            try:
                response = page.goto(url, wait_until="domcontentloaded", timeout=45000)
                _settle(page, 1000)
                status = response.status if response else None
                final_url = page.url
                text = _visible_text(page)
                if status and status < 400 and not _login_required_text(text) and "page not found" not in text.lower():
                    success = True
                    break
            except Exception:
                continue
        attempts.append(
            {
                "thread_id": thread["id"],
                "title": thread["title"],
                "success": success,
                "final_url": _sanitize_url(final_url) if final_url else None,
                "status": status,
            }
        )
    return {"success_count": sum(1 for item in attempts if item["success"]), "attempts": attempts}


def _recommendation(results: list[dict[str, Any]]) -> dict[str, Any]:
    low = [item for item in results if item["confidence"] == "LOW"]
    any_gap = any(
        item["expected_december_threads"] and item["discovered_links_after_buttons"] < item["expected_december_threads"]
        for item in results
    )
    if low or any_gap:
        return {
            "summary": (
                "Do not run full snapshot yet. Index pagination is not proven complete; use a hybrid strategy or continue "
                "Wix internal API/network investigation."
            ),
            "actions": [
                "Use December archive thread list as the seed for direct-open verification where current group index is incomplete.",
                "Promote any captured JSON/API endpoint with discussion IDs into the snapshot list builder after manual review.",
                "Keep network response samples sanitized and small; do not store cookies or auth headers.",
            ],
        }
    return {
        "summary": "Full snapshot can proceed with the best discovered strategy, but keep resume/checkpoint enabled.",
        "actions": ["Run a limited multi-group snapshot before full run.", "Keep comparison reports read-only."],
    }


def _confidence(best_count: int, expected_count: int, network_summary: dict[str, Any], direct: dict[str, Any]) -> str:
    if expected_count and best_count >= expected_count:
        return "HIGH"
    if network_summary["json_response_count"] > 0 and best_count > 0:
        return "MEDIUM"
    if direct["success_count"] > 0 and expected_count and best_count < expected_count:
        return "LOW"
    return "LOW" if expected_count and best_count < expected_count else "MEDIUM"


def _best_strategy(counts: dict[str, int]) -> str:
    return max(counts.items(), key=lambda item: item[1])[0]


def _expected_slug(slug: str) -> str:
    return SLUG_ALIASES.get(slug, slug)


def _looks_like_discussion_url(url: str, slug: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    return "fisherydb.com" in parsed.netloc and f"/group/{slug}/discussion/" in path


def _extract_discussion_urls_from_text(text: str, base_url: str) -> set[str]:
    urls = set()
    for raw in re.findall(r"https?://[^\"'\\\s<>]+|/group/[^\"'\\\s<>]+", text or ""):
        url = urljoin(base_url, raw).split("?")[0]
        if "/group/" in url and "/discussion/" in url:
            urls.add(_sanitize_url(url))
    return urls


def _sanitize_url(url: str | None) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def _sanitize_json_text(text: str) -> str:
    text = re.sub(r"(?i)(api[-_]?key|authorization|cookie|token|session)[\"'\s:=]+[^,\"'\s}]+", r"\1=<redacted>", text)
    text = re.sub(r"https?://[^\"'\s<>]+", lambda match: _sanitize_url(match.group(0)), text)
    return text


def _is_sensitive_endpoint(url: str) -> bool:
    lowered = url.lower()
    return any(marker in lowered for marker in ("access-tokens", "session", "oauth", "login", "token"))


def _sanitize_state_blob(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": item.get("name"),
        "size": item.get("size"),
        "sample": _sanitize_json_text(item.get("sample") or "")[:1000],
    }


def _settle(page: Page, wait_ms: int) -> None:
    page.wait_for_timeout(wait_ms)
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except PlaywrightTimeoutError:
        pass


def _visible_text(page: Page) -> str:
    try:
        return page.locator("body").inner_text(timeout=10000)
    except Exception:
        return ""


def _login_required_text(text: str) -> bool:
    text = text.lower()
    return any(marker in text for marker in ("log in", "sign up", "members only", "please login", "войдите"))


def _launch_browser(playwright: Any, *, headless: bool):
    try:
        return playwright.chromium.launch(headless=headless)
    except PlaywrightError:
        return playwright.chromium.launch(channel="msedge", headless=headless)


def _parse_int(value: str | None) -> int | None:
    try:
        return int(value) if value else None
    except ValueError:
        return None


def _md(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")
