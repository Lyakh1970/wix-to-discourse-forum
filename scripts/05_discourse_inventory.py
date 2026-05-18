from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fisherydb_forum_ng.discourse_inventory import (
    DiscourseInventoryError,
    load_discourse_config_from_env,
    run_discourse_inventory,
    write_json_report,
    write_markdown_report,
    write_summary_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only Discourse inventory for migration audit Phase 3. "
            "This script only performs GET requests and writes reports."
        )
    )
    parser.add_argument(
        "--env-file",
        default=str(PROJECT_ROOT / ".env"),
        help="Path to local .env containing Discourse API credentials.",
    )
    parser.add_argument(
        "--reports-dir",
        default=str(PROJECT_ROOT / "data" / "reports"),
        help="Directory where reports will be written.",
    )
    parser.add_argument(
        "--page-limit",
        type=int,
        default=0,
        help="Limit /latest.json pages. 0 means continue until pagination is exhausted.",
    )
    parser.add_argument(
        "--topic-detail-limit",
        type=int,
        default=0,
        help=(
            "Limit topic detail requests. 0 means fetch details for every discovered "
            "topic; -1 skips topic detail requests."
        ),
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.25,
        help="Delay in seconds between topic detail requests.",
    )
    args = parser.parse_args()

    env_file = Path(args.env_file)
    if env_file.exists():
        load_dotenv(env_file)
    else:
        load_dotenv()

    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    try:
        config = load_discourse_config_from_env(dict(os.environ))
        report = run_discourse_inventory(
            config,
            page_limit=args.page_limit,
            topic_detail_limit=args.topic_detail_limit,
            delay_seconds=args.delay,
        )
    except DiscourseInventoryError as exc:
        print(f"Discourse inventory failed: {exc}", file=sys.stderr)
        return 1

    json_path = reports_dir / "discourse_inventory.json"
    md_path = reports_dir / "discourse_inventory.md"
    summary_path = reports_dir / "discourse_summary.md"

    write_json_report(report, json_path)
    write_markdown_report(report, md_path)
    write_summary_report(report, summary_path)

    summary = report["summary"]
    print("Discourse read-only inventory completed.")
    print(f"Base URL: {report['source']['base_url']}")
    print(f"Categories: {summary['categories']}")
    print(f"Topics discovered: {summary['topics_discovered']}")
    print(
        "Topic details fetched: "
        f"{summary['topics_detail_fetched']} / {summary['topics_detail_attempted']}"
    )
    print(f"Total topic posts_count: {summary['topic_posts_count_total']}")
    print(f"Upload references in included posts: {summary['upload_references_in_included_posts']}")
    print(f"Report JSON: {json_path}")
    print(f"Report Markdown: {md_path}")
    print(f"Summary Markdown: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
