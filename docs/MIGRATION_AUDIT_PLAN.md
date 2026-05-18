# Migration Audit Plan

## Objective

Determine the real state of the FisheryDB forum migration.

The audit must answer:

1. What was successfully parsed in December 2025?
2. What exists now in Wix Groups?
3. What exists now in Discourse?
4. What is missing, duplicated, corrupted or incorrectly mapped?
5. What should be re-imported or fixed manually?

## Phase 1 — Local dataset inventory

Run:

```powershell
python scripts\01_inventory_local_export.py --root "E:\OneDrive\Documents\Claude\projects\fisherydb-forum-parser"
```

Expected outputs:

```text
data\reports\local_inventory.json
data\reports\local_inventory.md
```

## Phase 2 — Wix Groups inventory

Use `config/wix_groups.yaml` as a seed list.

The goal is not to re-scrape all content, but to verify group existence and visible content counts.

## Phase 3 — Discourse inventory

Use Discourse API in read-only mode.

No imports, deletes or updates at this stage.

## Phase 4 — Comparison matrix

Build table:

| Category / Group | Local export | Wix Groups | Discourse | Status |
|---|---:|---:|---:|---|

## Phase 5 — Decision

Only after reports are available, decide:

- what to re-import;
- what to normalize;
- what to leave as archive;
- what to fix manually in Discourse.
