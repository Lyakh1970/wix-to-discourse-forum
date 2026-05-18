# FISHERYDB_FORUM_NG — Project Context

## Purpose

This project is not a new Wix parser.

The goal is to audit, normalize and complete the migration of the FisheryDB technical forum from Wix / Wix Groups to Discourse.

The December 2025 parsed dataset from:

```text
E:\OneDrive\Documents\Claude\projects\fisherydb-forum-parser
```

must be treated as the primary source of truth unless proven incomplete.

## Historical context

The old Wix Forum is no longer available as the original forum. However, much of the content appears to have been transformed into Wix Groups, where old forum categories/topics may now correspond to group discussion pages.

Known examples:

```text
https://www.fisherydb.com/group/ft-issues/discussion
https://www.fisherydb.com/group/chE4ZQ/discussion
https://www.fisherydb.com/group/catsat/discussion
```

The Discourse forum already exists at:

```text
https://fisherydb.forum
```

but the import is incomplete and requires inventory and cleanup.

## Main principle

Do not start by scraping everything again.

First:

1. Inventory the existing parsed dataset.
2. Compare it with visible Wix Groups.
3. Compare it with current Discourse state.
4. Produce audit reports.
5. Only then decide what must be re-imported, fixed or manually restored.

## Known source folders

Primary:

```text
E:\OneDrive\Documents\Claude\projects\fisherydb-forum-parser
```

Historical / secondary:

```text
C:\Users\MIXA-BEAR\OneDrive\Documents\Cursor\DISCOURSE_SELFHOSTED
C:\Users\MIXA-BEAR\OneDrive\Documents\Cursor\fisherydb-forum
C:\Users\MIXA-BEAR\OneDrive\Documents\Cursor\fisherydb-forum-migration
C:\Users\MIXA-BEAR\OneDrive\Documents\Cursor\new_forum_discourse
C:\Users\MIXA-BEAR\OneDrive\Documents\Cursor\NEW_WIX_GITHUB_SCRAPER
C:\Users\MIXA-BEAR\OneDrive\Documents\Cursor\bot_wix_discourse
```

## Current priorities

1. Analyze the local December 2025 dataset.
2. Determine whether the dataset contains the complete forum content.
3. Use Wix Groups only as a verification / comparison source.
4. Build a clear matrix:

```text
Wix Groups / Local Export / Discourse
```

5. Prepare a practical migration completion plan.
