from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fisherydb_forum_ng.old_new_comparison import (
    compare_old_vs_discourse,
    load_discourse_inventory,
    load_old_threads,
    parse_category_mapping,
    write_all_reports,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only comparison of the old local Wix forum archive against "
            "the current Discourse inventory using CATEGORY_MAPPING_REVIEW.md."
        )
    )
    parser.add_argument(
        "--db",
        default=r"E:\OneDrive\Documents\Claude\projects\fisherydb-forum-parser\output\forum_data.db",
        help="Path to local forum_data.db.",
    )
    parser.add_argument(
        "--json-root",
        default=r"E:\OneDrive\Documents\Claude\projects\fisherydb-forum-parser\output",
        help="Path to local output root containing */threads.json.",
    )
    parser.add_argument(
        "--mapping",
        default=r"E:\OneDrive\Documents\Claude\projects\fisherydb-forum-parser\CATEGORY_MAPPING_REVIEW.md",
        help="Path to CATEGORY_MAPPING_REVIEW.md.",
    )
    parser.add_argument(
        "--discourse-inventory",
        default=str(PROJECT_ROOT / "data" / "reports" / "discourse_inventory.json"),
        help="Path to Phase 3 discourse_inventory.json.",
    )
    parser.add_argument(
        "--discourse-base-url",
        default="https://fisherydb.forum",
        help="Discourse base URL for report links.",
    )
    parser.add_argument(
        "--reports-dir",
        default=str(PROJECT_ROOT / "data" / "reports"),
        help="Directory where reports will be written.",
    )
    parser.add_argument(
        "--expand-discourse-details",
        action="store_true",
        help=(
            "Reserved read-only mode for a later run that refreshes inventory "
            "with full topic details. The default comparison does not call Discourse API."
        ),
    )
    args = parser.parse_args()

    if args.expand_discourse_details:
        print(
            "--expand-discourse-details is intentionally not performed by this comparison script yet. "
            "Run Phase 3 inventory expansion first, then rerun this comparison.",
            file=sys.stderr,
        )
        return 2

    db_path = Path(args.db)
    json_root = Path(args.json_root)
    mapping_path = Path(args.mapping)
    discourse_inventory_path = Path(args.discourse_inventory)
    reports_dir = Path(args.reports_dir)

    for path, label in (
        (db_path, "SQLite archive"),
        (mapping_path, "CATEGORY_MAPPING_REVIEW.md"),
        (discourse_inventory_path, "Discourse inventory"),
    ):
        if not path.exists():
            print(f"Missing {label}: {path}", file=sys.stderr)
            return 1

    mapping = parse_category_mapping(mapping_path)
    old_threads, old_meta = load_old_threads(db_path, json_root=json_root)
    discourse = load_discourse_inventory(discourse_inventory_path, args.discourse_base_url)
    report = compare_old_vs_discourse(old_threads, mapping, discourse)
    report["inputs"]["old_archive"] = old_meta
    write_all_reports(report, reports_dir)

    summary = report["summary"]
    counts = summary["status_counts"]
    print("Old forum vs Discourse read-only comparison completed.")
    print(f"Old threads: {summary['old_threads_total']}")
    print(f"Old slugs: {summary['old_slugs_total']}")
    print(f"Slugs with mapping: {summary['slugs_with_mapping']}")
    print(f"Discourse topics: {summary['discourse_topics_total']}")
    for status in ["IMPORTED_EXACT", "IMPORTED_PROBABLE", "POSSIBLE_MATCH", "NOT_FOUND", "MANUAL_REVIEW", "MAPPING_MISSING"]:
        print(f"{status}: {counts.get(status, 0)}")
    print(f"Reports dir: {reports_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
