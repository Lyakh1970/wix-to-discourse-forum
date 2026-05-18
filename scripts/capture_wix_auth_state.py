from __future__ import annotations

import argparse
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


DEFAULT_URL = "https://www.fisherydb.com/group/catsat/discussion"
DEFAULT_BROWSER = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Open a visible browser for manual Wix login, then save Playwright "
            "storage state. Do not commit the generated auth JSON."
        )
    )
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--output", default="data/working/wix_auth_state.json")
    parser.add_argument("--browser", default=DEFAULT_BROWSER)
    parser.add_argument("--wait-seconds", type=int, default=240)
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    browser_path = Path(args.browser)
    if not browser_path.exists():
        raise SystemExit(f"Browser executable not found: {browser_path}")

    print("Opening browser for manual Wix login.")
    print(f"URL: {args.url}")
    print(f"Storage state will be saved to: {output}")
    print(f"Wait time: {args.wait_seconds} seconds")
    print("Please log in manually in the browser window. Do not paste credentials here.")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=str(browser_path),
            headless=False,
            args=["--start-maximized"],
        )
        context = browser.new_context(
            viewport=None,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        page.goto(args.url, wait_until="domcontentloaded", timeout=60000)

        deadline = time.time() + args.wait_seconds
        while time.time() < deadline:
            remaining = int(deadline - time.time())
            if remaining % 30 == 0:
                print(f"Waiting for manual login... {remaining}s left")
            time.sleep(1)

        context.storage_state(path=str(output))
        print(f"Saved storage state: {output}")
        browser.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
