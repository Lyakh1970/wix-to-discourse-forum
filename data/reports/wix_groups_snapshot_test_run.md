# Wix Groups Snapshot Test Run

Generated after authenticated read-only test run for `catsat`, `ft-issues`, and `marport`.

## Scope

- auth_mode: authenticated
- auth_user: hostmarine.office@gmail.com
- auth_state_used: yes (`data/private/wix_auth_state.json`, not committed)
- groups tested: 3
- limit_discussions: 5 per group
- media download: disabled
- Discourse actions: none
- December archive actions: read-only

## Snapshot Result

- groups checked: 3
- public groups: 3
- login-required groups: 0
- broken/not found groups: 0
- discussions collected: 6
- comments collected: 18
- attachment/media URL refs collected: 107
- media downloaded: 0
- remote-only media refs: 107

## December Comparison Result

- discussions found in December archive: 6
- discussions missing in December archive: 0
- comments missing in December archive: 0
- attachments missing in December archive: 0
- comment statuses: `COMMENT_FOUND=7`, `COMMENT_PROBABLY_FOUND=3`, `COMMENT_NEEDS_REVIEW=8`
- attachment statuses: `ATTACHMENT_FOUND=19`, `REMOTE_ONLY_UNVERIFIED=88`

## What Worked

- Authenticated Playwright session works with stored local storage state.
- Wix Groups discussion pages are visible without anonymous/public fallback.
- Group candidate URL collection works from SQLite, `CATEGORY_MAPPING_REVIEW.md`, and `config/wix_groups.yaml`.
- Infinite/lazy scrolling finds discussion links.
- Discussion pages expose usable visible text for title/body/date extraction.
- Real discussion titles are recoverable from the visible text pattern `author/date/title`.
- Comment-like DOM selectors found comments on the tested pages.
- DOM and network URL capture found wixstatic/media URLs.
- SQLite checkpoint/resume dataset is created under `data/wix_groups_snapshot/`.

## Problems / Limitations

- Media was not downloaded in this test; most attachment refs remain `REMOTE_ONLY_UNVERIFIED`.
- Comment extraction is still generic and should be validated on more groups before full trust.
- Attachment matching is currently strongest for filenames/URLs present in both sources; remote-only URLs without downloaded hashes remain limited.
- Raw pages and snapshot DB are local artifacts and should not be committed.

## Recommendation

The test run is good enough to proceed to a larger authenticated snapshot, but not yet enough for a final answer to whether December 2025 contains everything. Next run should use `--full --resume` with conservative throttling, then rerun `scripts/09_compare_wix_groups_snapshot_vs_december_archive.py`.
