from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fisherydb_forum_ng.archive_completeness import (
    run_archive_completeness_audit,
    write_json_report,
    write_markdown_report,
    write_summary_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit the December local archive as an independent source. "
            "This does not touch Discourse, does not scrape Wix, and does not "
            "treat Discourse category mapping differences as errors."
        )
    )
    parser.add_argument(
        "--root",
        required=True,
        help="Path to the local fisherydb-forum-parser export root.",
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

    report = run_archive_completeness_audit(root)
    json_path = reports_dir / "archive_completeness_audit.json"
    md_path = reports_dir / "archive_completeness_audit.md"
    summary_path = reports_dir / "archive_completeness_summary.md"

    write_json_report(report, json_path)
    write_markdown_report(report, md_path)
    write_summary_report(report, summary_path)

    self_containment = report.get("self_containment", {})
    quality = report.get("quality", {})
    conclusion = report.get("practical_conclusion", {})

    print("Archive completeness audit completed.")
    print(f"Root: {root}")
    print(f"SQLite categories: {self_containment.get('sqlite_categories', 0)}")
    print(f"SQLite threads: {self_containment.get('sqlite_threads', 0)}")
    print(f"SQLite posts: {self_containment.get('sqlite_posts', 0)}")
    print(f"SQLite comments: {self_containment.get('sqlite_comments', 0)}")
    print(f"Attachments without local_path: {quality.get('attachments_missing_local_path', 0)}")
    print(f"Attachments with broken local_path: {quality.get('attachments_broken_local_path', 0)}")
    print(
        "Can use archive as working source: "
        f"{conclusion.get('can_use_local_archive_as_working_source')}"
    )
    print(f"Report JSON: {json_path}")
    print(f"Report Markdown: {md_path}")
    print(f"Summary Markdown: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
