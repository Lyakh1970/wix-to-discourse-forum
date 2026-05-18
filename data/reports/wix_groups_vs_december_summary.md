# Wix Groups Snapshot vs December Archive Summary

- This is a read-only verification report.
- `MISSING_IN_DECEMBER` is not an automatic import instruction.

## Counts

- groups_checked: 3
- public_groups: 3
- login_required_groups: 0
- broken_not_found_groups: 0
- discussions_in_wix_snapshot: 6
- discussions_in_december_archive: 589
- discussions_missing_in_december: 0
- comments_in_wix_snapshot: 18
- comments_in_december_archive: 647
- comments_missing_in_december: 0
- attachments_in_wix_snapshot: 107
- attachments_in_december_archive: 1151
- attachments_missing_in_december: 0
- attachments_downloaded_during_snapshot: 0
- attachments_remote_only: 107

## Status Counts

- discussions: {'FOUND_IN_DECEMBER': 6}
- comments: {'COMMENT_NEEDS_REVIEW': 8, 'COMMENT_FOUND': 7, 'COMMENT_PROBABLY_FOUND': 3}
- attachments: {'REMOTE_ONLY_UNVERIFIED': 88, 'ATTACHMENT_FOUND': 19}

## Limitations

- Absence from current Wix Groups is not proof that the December archive is wrong; Groups may have changed.
- The snapshot parser is verification-oriented and may need selector tuning after authenticated test runs.
- Remote-only attachments are compared by URL/filename only unless media downloading is enabled later.
