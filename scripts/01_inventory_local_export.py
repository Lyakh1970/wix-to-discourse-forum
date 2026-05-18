from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fisherydb_forum_ng.local_export import to_dict, walk_local_export, write_markdown_report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inventory the December 2025 local FisheryDB forum export."
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

    inventory = walk_local_export(root)

    json_path = reports_dir / "local_inventory.json"
    md_path = reports_dir / "local_inventory.md"

    json_path.write_text(
        json.dumps(to_dict(inventory), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_markdown_report(inventory, md_path)

    print("Local export inventory completed.")
    print(f"Root: {root}")
    print(f"Total files: {inventory.total_files}")
    print(f"JSON files: {len(inventory.json_files)}")
    print(f"HTML files: {len(inventory.html_files)}")
    print(f"Markdown files: {len(inventory.markdown_files)}")
    print(f"Attachment-like files: {len(inventory.attachment_like_files)}")
    print(f"Report JSON: {json_path}")
    print(f"Report Markdown: {md_path}")

    if inventory.warnings:
        print("Warnings:")
        for warning in inventory.warnings:
            print(f"- {warning}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
