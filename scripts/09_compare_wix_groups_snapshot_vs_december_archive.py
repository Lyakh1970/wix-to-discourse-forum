from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fisherydb_forum_ng.compare_wix_snapshot_december import (
    run_snapshot_vs_december,
    write_compare_reports,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare authenticated Wix Groups snapshot against December local archive."
    )
    parser.add_argument(
        "--snapshot-db",
        default=str(PROJECT_ROOT / "data" / "wix_groups_snapshot" / "wix_groups_snapshot.sqlite3"),
    )
    parser.add_argument(
        "--december-db",
        default=r"E:\OneDrive\Documents\Claude\projects\fisherydb-forum-parser\output\forum_data.db",
    )
    parser.add_argument("--reports-dir", default=str(PROJECT_ROOT / "data" / "reports"))
    args = parser.parse_args()

    snapshot_db = Path(args.snapshot_db)
    december_db = Path(args.december_db)
    if not snapshot_db.exists():
        print(f"Missing snapshot DB: {snapshot_db}", file=sys.stderr)
        return 1
    if not december_db.exists():
        print(f"Missing December DB: {december_db}", file=sys.stderr)
        return 1

    report = run_snapshot_vs_december(snapshot_db, december_db)
    write_compare_reports(report, Path(args.reports_dir))
    s = report["summary"]
    print("Wix Groups snapshot vs December comparison completed.")
    print(f"groups_checked: {s['groups_checked']}")
    print(f"discussions_in_wix_snapshot: {s['discussions_in_wix_snapshot']}")
    print(f"discussions_missing_in_december: {s['discussions_missing_in_december']}")
    print(f"comments_missing_in_december: {s['comments_missing_in_december']}")
    print(f"attachments_missing_in_december: {s['attachments_missing_in_december']}")
    print(f"Reports dir: {args.reports_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
