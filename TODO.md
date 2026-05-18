# TODO — FISHERYDB_FORUM_NG

## Phase 1 — Local dataset inventory

- [ ] Locate December 2025 export files in `E:\OneDrive\Documents\Claude\projects\fisherydb-forum-parser`
- [ ] Detect all JSON, HTML, Markdown and attachment folders
- [ ] Count categories, posts, comments and attachments
- [ ] Detect duplicate posts
- [ ] Detect empty or broken posts
- [ ] Detect posts without title/body/date/author/category
- [ ] Generate `data/reports/local_inventory.md`
- [ ] Generate `data/reports/local_inventory.json`

## Phase 2 — Wix Groups verification

- [ ] Build list of known Wix Group discussion URLs
- [ ] Check which groups are public, private, empty or broken
- [ ] Extract visible group title, post count estimate, latest/oldest visible dates
- [ ] Generate `data/reports/wix_groups_inventory.md`
- [ ] Generate `data/reports/wix_groups_inventory.json`

## Phase 3 — Compare local export vs Wix Groups

- [ ] Match groups by slug/title/category mapping
- [ ] Compare post titles and dates
- [ ] Identify content visible in Wix Groups but missing locally
- [ ] Identify local content not visible in Wix Groups
- [ ] Generate `data/reports/local_vs_wix_groups.md`

## Phase 4 — Discourse inventory

- [ ] Connect to Discourse API in read-only mode
- [ ] Export categories, topics, posts and attachments metadata
- [ ] Generate `data/reports/discourse_inventory.md`

## Phase 5 — Final migration decision

- [ ] Build matrix: Wix Groups / Local Export / Discourse
- [ ] Decide what to re-import
- [ ] Decide what to fix manually
- [ ] Prepare dry-run import plan
