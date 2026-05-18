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

from fisherydb_forum_ng.wix_groups_pagination_probe import DEFAULT_GROUPS, ProbeConfig, run_pagination_probe


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Authenticated read-only probe for Wix Groups discussion list pagination/network loading."
    )
    parser.add_argument("--groups", nargs="*", default=DEFAULT_GROUPS, help="Group slugs to probe.")
    parser.add_argument("--headful", action="store_true")
    parser.add_argument("--scroll-rounds", type=int, default=14)
    parser.add_argument("--wait-ms", type=int, default=1800)
    parser.add_argument("--direct-limit", type=int, default=5)
    parser.add_argument("--auth-state-path", default=None)
    parser.add_argument(
        "--december-db",
        default=r"E:\OneDrive\Documents\Claude\projects\fisherydb-forum-parser\output\forum_data.db",
    )
    args = parser.parse_args()

    load_dotenv(PROJECT_ROOT / ".env")
    auth_state_path = Path(
        args.auth_state_path
        or os.getenv("WIX_AUTH_STATE_PATH")
        or PROJECT_ROOT / "data" / "private" / "wix_auth_state.json"
    )
    if not auth_state_path.exists():
        print(f"Missing Wix auth state: {auth_state_path}", file=sys.stderr)
        print("Run scripts/08a_wix_auth_check.py --force-login --headful first.", file=sys.stderr)
        return 1
    config = ProbeConfig(
        project_root=PROJECT_ROOT,
        auth_state_path=auth_state_path,
        reports_dir=PROJECT_ROOT / "data" / "reports",
        december_db=Path(args.december_db),
        headful=args.headful,
        scroll_rounds=args.scroll_rounds,
        wait_ms=args.wait_ms,
        direct_limit=args.direct_limit,
    )
    report = run_pagination_probe(config, args.groups)
    print("Wix Groups pagination probe completed.")
    for item in report["groups"]:
        print(
            f"{item['slug']}: expected={item['expected_december_threads']} "
            f"initial={item['discovered_links_initial']} "
            f"scroll={item['discovered_links_after_scroll']} "
            f"buttons={item['discovered_links_after_buttons']} "
            f"network={item['discovered_links_from_network_json']} "
            f"hydration={item['discovered_links_from_hydration_state']} "
            f"direct={item['direct_known_thread_open_success_count']} "
            f"confidence={item['confidence']}"
        )
    print(f"Recommendation: {report['recommendation']['summary']}")
    print(f"Report: {PROJECT_ROOT / 'data' / 'reports' / 'wix_groups_pagination_probe.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
