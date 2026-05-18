# AGENTS.md — Instructions for Codex / AI agents

## Mission

You are working on `FISHERYDB_FORUM_NG`.

Your task is to help audit and complete the migration of the FisheryDB technical forum from Wix / Wix Groups to Discourse.

## Very important

Do **NOT** create a new full Wix parser unless explicitly requested.

The main assumption is that the December 2025 parser already extracted most or all content.

Primary source folder:

```text
E:\OneDrive\Documents\Claude\projects\fisherydb-forum-parser
```

## Priorities

1. Inventory existing parsed data.
2. Determine exact counts:
   - categories
   - topics/posts
   - comments
   - attachments
   - images
   - missing fields
   - duplicate records
3. Build comparison reports:
   - local parsed dataset vs Wix Groups
   - local parsed dataset vs current Discourse
4. Do not perform destructive actions.
5. Do not import into Discourse without an explicit dry-run report first.

## Expected outputs

All scripts must write:

- machine-readable JSON reports;
- human-readable Markdown reports.

Reports must be saved into:

```text
data/reports/
```

## Safety

Never commit:

- API keys;
- cookies;
- `auth_state.json`;
- Discourse API keys;
- Wix session files;
- `.env`.

Use `.env` for secrets.

## Coding style

- Prefer small scripts with clear CLI arguments.
- Each script must be safe to run multiple times.
- Never overwrite source data.
- Write output files into `data/reports/` or `data/working/`.
- Print a short summary to the console.
