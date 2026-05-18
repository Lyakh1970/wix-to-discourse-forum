# Archive Completeness Summary

Archive usable as working source: **yes**

The audit treats the local December archive as an independent source. It does not use Discourse and does not treat old-to-new category mapping differences as primary errors.

## Core Counts

- Categories: **67**
- Categories with threads: **60**
- Categories with threads.json: **60**
- Threads: **589**
- Posts: **1236**
- Original posts: **589**
- Comments: **647**
- Attachments/images rows: **1151 / 1055**
- Referenced local files present: **1135**

## Blocking Issues

_None._

## Non-Blocking Review Items

- `Some attachment records have no local_path and may be remote-only embeds/previews.`
- `Some posts/comments have suspiciously short bodies.`
- `SQLite and JSON attachment reference counts differ.`
- `Some SQLite-only categories are empty and can be treated as structural remnants.`

## Important Quality Signals

- Posts/comments without body: **0**
- Attachments without local_path: **15**
- Attachments with broken local_path: **0**
- Suspicious short bodies: **12**
- Error-marker bodies: **0**
- SQLite/JSON attachment delta: **7**

## Wix Groups Next

Proceed to read-only Wix Groups verification: **yes**

- `Categories or topics involved in attachment count mismatches.`
- `Posts with missing local_path attachments that may be remote-only embeds.`
- `Representative high-volume categories to validate archive completeness against visible Wix Groups.`
