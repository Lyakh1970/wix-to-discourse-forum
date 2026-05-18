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

from fisherydb_forum_ng.wix_groups_snapshot import (
    DEFAULT_AUTH_USER,
    WixSnapshotConfig,
    build_group_candidates,
    run_snapshot,
    write_candidates_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Authenticated read-only full verification snapshot of Wix Groups."
    )
    parser.add_argument("--limit-groups", type=int, default=None)
    parser.add_argument("--limit-discussions", type=int, default=None)
    parser.add_argument("--only-group", default=None)
    parser.add_argument("--resume", action="store_true", help="Skip groups already present in snapshot DB.")
    parser.add_argument("--full", action="store_true", help="Run all candidate groups.")
    parser.add_argument("--headful", action="store_true")
    parser.add_argument("--auth-user", default=DEFAULT_AUTH_USER)
    parser.add_argument("--auth-state-path", default=None)
    parser.add_argument("--download-media", action="store_true", help="Reserved; media download is disabled by default.")
    parser.add_argument("--throttle-min", type=float, default=5.0)
    parser.add_argument("--throttle-max", type=float, default=15.0)
    parser.add_argument(
        "--db",
        default=r"E:\OneDrive\Documents\Claude\projects\fisherydb-forum-parser\output\forum_data.db",
    )
    parser.add_argument(
        "--mapping",
        default=r"E:\OneDrive\Documents\Claude\projects\fisherydb-forum-parser\CATEGORY_MAPPING_REVIEW.md",
    )
    parser.add_argument("--wix-groups-config", default=str(PROJECT_ROOT / "config" / "wix_groups.yaml"))
    args = parser.parse_args()

    load_dotenv(PROJECT_ROOT / ".env")
    auth_state_path = Path(
        args.auth_state_path
        or os.getenv("WIX_AUTH_STATE_PATH")
        or PROJECT_ROOT / "data" / "private" / "wix_auth_state.json"
    )
    config = WixSnapshotConfig(
        project_root=PROJECT_ROOT,
        snapshot_dir=PROJECT_ROOT / "data" / "wix_groups_snapshot",
        reports_dir=PROJECT_ROOT / "data" / "reports",
        auth_state_path=auth_state_path,
        auth_user=args.auth_user,
        headful=args.headful,
        throttle_min=args.throttle_min,
        throttle_max=args.throttle_max,
        download_media=args.download_media,
    )
    candidates_doc = build_group_candidates(
        db_path=Path(args.db),
        mapping_path=Path(args.mapping),
        wix_groups_config=Path(args.wix_groups_config),
    )
    write_candidates_report(candidates_doc, PROJECT_ROOT / "data" / "reports" / "wix_groups_url_candidates.md")
    candidates = candidates_doc["candidates"]
    limit_groups = None if args.full else args.limit_groups
    if not args.full and not args.only_group and limit_groups is None:
        limit_groups = 3
    summary = run_snapshot(
        config,
        candidates=candidates,
        only_group=args.only_group,
        limit_groups=limit_groups,
        limit_discussions=args.limit_discussions,
        resume=args.resume,
    )
    print("Wix Groups snapshot completed.")
    print(f"groups_checked: {summary['groups_checked']}")
    print(f"public_groups: {summary['public_groups']}")
    print(f"login_required_groups: {summary['login_required_groups']}")
    print(f"discussions: {summary['discussions']}")
    print(f"comments: {summary['comments']}")
    print(f"attachments: {summary['attachments']}")
    print(f"snapshot_dir: {summary['snapshot_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
