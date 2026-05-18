# Discourse Import Strategy — Draft

## Rule 1

Do not import anything until the audit reports are complete.

## Rule 2

Always run dry-run first.

## Rule 3

Preserve source traceability.

Each imported Discourse topic should contain or preserve:

- original Wix URL, if available;
- original category/group;
- original date, if available;
- original author, if available;
- local export record ID or file path.

## Rule 4

If author/date are missing, do not block import.

Content completeness is more important than perfect metadata.

## Rule 5

Attachments must be verified before import.

For every referenced attachment:

- check if local file exists;
- calculate checksum;
- upload to Discourse only once if possible;
- record upload result.
