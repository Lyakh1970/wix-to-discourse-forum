from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fisherydb_forum_ng.local_dataset_analysis import (
    analyze_local_dataset,
    write_json_report,
    write_markdown_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze the already parsed FisheryDB forum dataset without scraping or importing."
    )
    parser.add_argument(
        "--root",
        required=True,
        help="Path to the primary local export, e.g. E:\\OneDrive\\Documents\\Claude\\projects\\fisherydb-forum-parser",
    )
    parser.add_argument(
        "--reports-dir",
        default=str(PROJECT_ROOT / "data" / "reports"),
        help="Directory where reports will be written.",
    )
    args = parser.parse_args()

    root = Path(args.root)
    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    report = analyze_local_dataset(root)
    json_path = reports_dir / "local_dataset_analysis.json"
    md_path = reports_dir / "local_dataset_analysis.md"

    write_json_report(report, json_path)
    write_markdown_report(report, md_path)

    sqlite_counts = report.get("sqlite", {}).get("counts", {})
    attachment = report.get("attachment_reconciliation", {})

    print("Local dataset analysis completed.")
    print(f"Root: {root}")
    print(f"SQLite categories: {sqlite_counts.get('categories', 0)}")
    print(f"SQLite threads: {sqlite_counts.get('threads', 0)}")
    print(f"SQLite posts: {sqlite_counts.get('posts', 0)}")
    print(f"SQLite comments: {sqlite_counts.get('comments', 0)}")
    print(f"SQLite attachments: {sqlite_counts.get('attachments', 0)}")
    print(f"JSON attachment references: {attachment.get('json_attachment_references', 0)}")
    print(f"Report JSON: {json_path}")
    print(f"Report Markdown: {md_path}")

    if report.get("warnings"):
        print("Warnings:")
        for warning in report["warnings"]:
            print(f"- {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
