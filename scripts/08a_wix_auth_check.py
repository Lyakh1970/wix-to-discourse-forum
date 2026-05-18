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
    run_auth_check,
    write_candidates_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Authenticated read-only Wix Groups auth/session check for Phase 5."
    )
    parser.add_argument("--headful", action="store_true", help="Run browser visibly.")
    parser.add_argument("--force-login", action="store_true", help="Ignore existing auth state and wait for manual login.")
    parser.add_argument("--auth-user", default=DEFAULT_AUTH_USER)
    parser.add_argument("--auth-state-path", default=None)
    parser.add_argument("--login-timeout", type=int, default=900)
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
        headful=True if args.force_login else args.headful,
    )
    candidates = build_group_candidates(
        db_path=Path(args.db),
        mapping_path=Path(args.mapping),
        wix_groups_config=Path(args.wix_groups_config),
    )
    write_candidates_report(candidates, PROJECT_ROOT / "data" / "reports" / "wix_groups_url_candidates.md")
    seed_urls = [item["url"] for item in candidates["candidates"] if item["slug"] in {"catsat", "ft-issues", "marport"}]
    if not seed_urls:
        seed_urls = [item["url"] for item in candidates["candidates"][:3]]
    report = run_auth_check(
        config,
        seed_urls=seed_urls,
        force_login=args.force_login,
        login_timeout_seconds=args.login_timeout,
    )
    print("Wix auth check completed.")
    print(f"auth_mode: {report['auth_mode']}")
    print(f"auth_user: {report['auth_user']}")
    print(f"auth_state_path: {report['auth_state_path']}")
    print(f"auth_state_used: {report['auth_state_used']}")
    print(f"login_required_groups: {report['login_required_groups']}")
    print(f"Report: {PROJECT_ROOT / 'data' / 'reports' / 'wix_auth_check.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
