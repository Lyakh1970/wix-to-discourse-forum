from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = Path(r"E:\OneDrive\Documents\Claude\projects\fisherydb-forum-parser")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply known vessel rename context to Wix Groups inventory reports."
    )
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--reports-dir", default=str(PROJECT_ROOT / "data" / "reports"))
    parser.add_argument("--rename-map", default=str(PROJECT_ROOT / "config" / "vessel_rename_map.yaml"))
    args = parser.parse_args()

    root = Path(args.root)
    reports_dir = Path(args.reports_dir)
    rename_map_path = Path(args.rename_map)
    inventory_path = reports_dir / "wix_groups_inventory.json"

    if not inventory_path.exists():
        raise SystemExit(f"Missing inventory report: {inventory_path}")
    if not rename_map_path.exists():
        raise SystemExit(f"Missing rename map: {rename_map_path}")

    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    rename_map = yaml.safe_load(rename_map_path.read_text(encoding="utf-8")) or {}
    local_counts = load_local_counts(root)
    report = apply_context(inventory, rename_map, local_counts)

    json_path = reports_dir / "known_rename_context.json"
    md_path = reports_dir / "known_rename_notes.md"
    corrected_summary_path = reports_dir / "wix_groups_summary_corrected.md"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_notes_md(report, md_path)
    write_corrected_summary_md(report, corrected_summary_path)

    print("Known rename context applied.")
    print(f"Covered suspected gaps: {len(report['covered_suspected_gaps'])}")
    print(f"Remaining suspected gaps: {len(report['remaining_suspected_gaps'])}")
    print(f"Report JSON: {json_path}")
    print(f"Notes Markdown: {md_path}")
    print(f"Corrected summary Markdown: {corrected_summary_path}")
    return 0


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


def apply_context(
    inventory: dict[str, Any],
    rename_map: dict[str, Any],
    local_counts: dict[str, dict[str, int]],
) -> dict[str, Any]:
    groups_by_slug = {item["slug"]: item for item in inventory.get("groups", [])}
    important = inventory.get("summary", {}).get("important_for_manual_review", [])
    covered = []
    remaining = []
    applied_context = []

    for item in important:
        slug = item["slug"]
        context = find_rename_for_slug(rename_map, slug)
        if not context:
            remaining.append(item)
            continue

        canonical_slug = context.get("canonical_archive_slug")
        canonical_counts = local_counts.get(canonical_slug or "", {})
        current_group = groups_by_slug.get(slug, {})
        canonical_group = groups_by_slug.get(canonical_slug or "", {})

        covered.append(
            {
                **item,
                "resolution": "KNOWN_RENAME_MAPPING",
                "old_name": context.get("old_name"),
                "new_name": context.get("new_name"),
                "canonical_archive_slug": canonical_slug,
                "current_wix_slug": context.get("current_wix_slug"),
                "canonical_archive_threads": canonical_counts.get("threads", 0),
                "canonical_archive_posts": canonical_counts.get("posts", 0),
                "current_wix_topic_sample": current_group.get("visible_topic_titles_sample", []),
                "canonical_wix_status": canonical_group.get("status"),
                "notes": [
                    "Known vessel rename explains old/new slug mismatch.",
                    context.get("notes", "").strip(),
                ],
            }
        )

    for context in rename_map.get("renames", []):
        applied_context.append(
            {
                "old_name": context.get("old_name"),
                "new_name": context.get("new_name"),
                "related_slugs": context.get("related_slugs", []),
                "canonical_archive_slug": context.get("canonical_archive_slug"),
                "current_wix_slug": context.get("current_wix_slug"),
                "canonical_archive_counts": local_counts.get(context.get("canonical_archive_slug", ""), {}),
            }
        )

    corrected = dict(inventory.get("summary", {}))
    corrected["important_for_manual_review_original"] = important
    corrected["covered_by_known_rename_context"] = covered
    corrected["important_for_manual_review"] = remaining
    corrected["evidence_of_substantial_content_missing_locally"] = (
        "NO_CLEAR_EVIDENCE_AFTER_KNOWN_RENAME_CONTEXT"
        if not remaining
        else "UNKNOWN_PENDING_MANUAL_REVIEW"
    )
    corrected["notes"] = list(corrected.get("notes", [])) + [
        "Known vessel rename map applied after Phase 2 inventory.",
        "Trondheim -> Fishing Tide and Forsa -> Fishing Force are treated as expected historical context, not gaps.",
    ]

    return {
        "source_inventory": "data/reports/wix_groups_inventory.json",
        "rename_map": "config/vessel_rename_map.yaml",
        "corrected_summary": corrected,
        "covered_suspected_gaps": covered,
        "remaining_suspected_gaps": remaining,
        "applied_context": applied_context,
    }


def find_rename_for_slug(rename_map: dict[str, Any], slug: str) -> dict[str, Any] | None:
    for item in rename_map.get("renames", []):
        related = set(item.get("related_slugs", []))
        if slug in related or slug == item.get("current_wix_slug") or slug == item.get("canonical_archive_slug"):
            return item
    return None


def write_notes_md(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Known Rename Notes",
        "",
        "These notes explain historical vessel/category naming differences. They are audit context, not a Discourse import mapping.",
        "",
        "## Applied Context",
        "",
    ]
    for item in report["applied_context"]:
        lines.append(f"- **{item['old_name']} -> {item['new_name']}**")
        lines.append(f"  - Related slugs: `{', '.join(item.get('related_slugs', []))}`")
        lines.append(f"  - Canonical archive slug: `{item.get('canonical_archive_slug')}`")
        lines.append(f"  - Current Wix slug: `{item.get('current_wix_slug')}`")
        counts = item.get("canonical_archive_counts", {})
        lines.append(f"  - Local archive coverage: {counts.get('threads', 0)} threads, {counts.get('posts', 0)} posts")
    lines.append("")
    lines.append("## Covered Suspected Gaps")
    lines.append("")
    if report["covered_suspected_gaps"]:
        for item in report["covered_suspected_gaps"]:
            lines.append(
                f"- `{item['slug']}` -> `{item['canonical_archive_slug']}`: "
                f"{item['resolution']}; local archive has "
                f"{item['canonical_archive_threads']} threads / {item['canonical_archive_posts']} posts."
            )
    else:
        lines.append("_None._")
    lines.append("")
    lines.append("## Remaining Suspected Gaps")
    lines.append("")
    if report["remaining_suspected_gaps"]:
        for item in report["remaining_suspected_gaps"]:
            lines.append(f"- `{item['slug']}`: {item.get('status')}")
    else:
        lines.append("_None._")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_corrected_summary_md(report: dict[str, Any], path: Path) -> None:
    summary = report["corrected_summary"]
    lines = [
        "# Wix Groups Summary Corrected",
        "",
        "Known vessel rename context has been applied. Discourse is not evaluated here.",
        "",
        f"- Slugs checked: **{summary['checked_slugs']}**",
        f"- Public/accessibly with content: **{summary['public_with_content']}**",
        f"- Public empty: **{summary['public_empty']}**",
        f"- Private/login required: **{summary['private_or_login_required']}**",
        f"- Broken/not found: **{summary['not_found_or_broken']}**",
        f"- Unknown: **{summary['unknown']}**",
        "",
        "## Covered By Known Rename Context",
        "",
    ]
    if report["covered_suspected_gaps"]:
        for item in report["covered_suspected_gaps"]:
            lines.append(
                f"- `{item['slug']}` is covered by `{item['canonical_archive_slug']}` "
                f"({item['old_name']} -> {item['new_name']}), "
                f"{item['canonical_archive_threads']} local threads."
            )
    else:
        lines.append("_None._")
    lines.extend(
        [
            "",
            "## Remaining Important For Manual Review",
            "",
        ]
    )
    if report["remaining_suspected_gaps"]:
        for item in report["remaining_suspected_gaps"]:
            lines.append(f"- `{item['slug']}`: {item.get('status')}")
    else:
        lines.append("_None._")
    lines.extend(
        [
            "",
            "## Missing Local Content Signal",
            "",
            f"Evidence of substantial Wix Groups content absent locally: **{summary['evidence_of_substantial_content_missing_locally']}**",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
