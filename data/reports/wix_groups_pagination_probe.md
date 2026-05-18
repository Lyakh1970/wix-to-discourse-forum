# Wix Groups Pagination Probe

Generated at: `2026-05-18T16:56:01.535497+00:00`
auth_mode: `authenticated`
auth_state_used: `True`

| slug | expected | initial | after scroll | after buttons | network JSON links | hydration links | direct success | best strategy | confidence | notes |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| catsat | 3 | 1 | 2 | 2 | 0 | 0 | 3 | dom_scroll | MEDIUM | Discovered count is lower than December expected count.; Direct known December URLs/slugs open while index remains incomplete. |
| ft-issues | 24 | 2 | 2 | 1 | 0 | 0 | 5 | dom_scroll | MEDIUM | Discovered count is lower than December expected count.; Direct known December URLs/slugs open while index remains incomplete. |
| marport | 12 | 2 | 2 | 2 | 0 | 0 | 5 | dom_scroll | MEDIUM | Discovered count is lower than December expected count.; Direct known December URLs/slugs open while index remains incomplete. |
| fs-issues | 30 | 2 | 4 | 3 | 0 | 0 | 5 | dom_scroll | MEDIUM | Discovered count is lower than December expected count.; Direct known December URLs/slugs open while index remains incomplete. |
| km-issues | 30 | 2 | 3 | 1 | 0 | 0 | 5 | dom_scroll | MEDIUM | Discovered count is lower than December expected count.; Direct known December URLs/slugs open while index remains incomplete. |
| marport-1 | 30 | 0 | 0 | 0 | 0 | 0 | 5 | dom_scroll | LOW | Discovered count is lower than December expected count.; Direct known December URLs/slugs open while index remains incomplete. |
| trondheim-issues | 24 | 0 | 0 | 0 | 0 | 0 | 5 | dom_scroll | LOW | Discovered count is lower than December expected count.; Direct known December URLs/slugs open while index remains incomplete. |

## Network/API Signals

- `catsat`: relevant responses=1367, json responses=197, likely API endpoints=25
  - `GET 200 https://www.fisherydb.com/group/catsat/discussion` (text/html, 241652)
  - `GET 200 https://static.parastorage.com/services/social-groups-ooi/5.823.0/client-viewer/DiscussionPage.chunk.min.js` (application/javascript, 6967)
  - `GET 200 https://siteassets.parastorage.com/pages/pages/thunderbolt` (application/json, 322110)
  - `GET 200 https://siteassets.parastorage.com/pages/pages/thunderbolt` (application/json, 67204)
  - `GET 200 https://siteassets.parastorage.com/pages/pages/thunderbolt` (application/json, 44653)
  - `GET 200 https://siteassets.parastorage.com/pages/pages/thunderbolt` (application/json, 20382)
  - `GET 200 https://www.fisherydb.com/_api/v1/access-tokens` (application/json, 64556)
  - `GET 200 https://static.parastorage.com/services/editor-elements/1.15127.0/rb_wixui.thunderbolt.manifest.min.json` (application/json, 43580)
- `ft-issues`: relevant responses=2218, json responses=328, likely API endpoints=25
  - `GET 200 https://www.fisherydb.com/group/ft-issues/discussion` (text/html, 239417)
  - `GET 200 https://static.parastorage.com/services/social-groups-ooi/5.823.0/client-viewer/DiscussionPage.chunk.min.js` (application/javascript, 6967)
  - `GET 200 https://siteassets.parastorage.com/pages/pages/thunderbolt` (application/json, 322110)
  - `GET 200 https://siteassets.parastorage.com/pages/pages/thunderbolt` (application/json, 44653)
  - `GET 200 https://siteassets.parastorage.com/pages/pages/thunderbolt` (application/json, 20382)
  - `GET 200 https://siteassets.parastorage.com/pages/pages/thunderbolt` (application/json, 67204)
  - `GET 200 https://www.fisherydb.com/_api/v1/access-tokens` (application/json, 64556)
  - `GET 200 https://static.parastorage.com/services/editor-elements/1.15129.0/rb_wixui.thunderbolt.manifest.min.json` (application/json, 43580)
- `marport`: relevant responses=2143, json responses=322, likely API endpoints=25
  - `GET 200 https://www.fisherydb.com/group/marport/discussion` (text/html, None)
  - `GET 200 https://static.parastorage.com/services/social-groups-ooi/5.823.0/client-viewer/DiscussionPage.chunk.min.js` (application/javascript, 6967)
  - `GET 200 https://siteassets.parastorage.com/pages/pages/thunderbolt` (application/json, 322228)
  - `GET 200 https://siteassets.parastorage.com/pages/pages/thunderbolt` (application/json, 44653)
  - `GET 200 https://siteassets.parastorage.com/pages/pages/thunderbolt` (application/json, 67204)
  - `GET 200 https://siteassets.parastorage.com/pages/pages/thunderbolt` (application/json, 20382)
  - `GET 200 https://www.fisherydb.com/_api/v1/access-tokens` (application/json, 64556)
  - `GET 200 https://static.parastorage.com/services/editor-elements/1.15127.0/rb_wixui.thunderbolt.manifest.min.json` (application/json, 43580)
- `fs-issues`: relevant responses=2356, json responses=372, likely API endpoints=25
  - `GET 200 https://www.fisherydb.com/group/fs-issues/discussion` (text/html, None)
  - `GET 200 https://static.parastorage.com/services/social-groups-ooi/5.823.0/client-viewer/DiscussionPage.chunk.min.js` (application/javascript, 6967)
  - `GET 200 https://siteassets.parastorage.com/pages/pages/thunderbolt` (application/json, 322110)
  - `GET 200 https://siteassets.parastorage.com/pages/pages/thunderbolt` (application/json, 67204)
  - `GET 200 https://siteassets.parastorage.com/pages/pages/thunderbolt` (application/json, 20382)
  - `GET 200 https://siteassets.parastorage.com/pages/pages/thunderbolt` (application/json, 44653)
  - `GET 200 https://www.fisherydb.com/_api/v1/access-tokens` (application/json, 64556)
  - `GET 200 https://static.parastorage.com/services/editor-elements/1.15127.0/rb_wixui.thunderbolt.manifest.min.json` (application/json, 43580)
- `km-issues`: relevant responses=2348, json responses=358, likely API endpoints=25
  - `GET 200 https://www.fisherydb.com/group/km-issues/discussion` (text/html, None)
  - `GET 200 https://static.parastorage.com/services/social-groups-ooi/5.823.0/client-viewer/DiscussionPage.chunk.min.js` (application/javascript, 6967)
  - `GET 200 https://siteassets.parastorage.com/pages/pages/thunderbolt` (application/json, 322228)
  - `GET 200 https://siteassets.parastorage.com/pages/pages/thunderbolt` (application/json, 67204)
  - `GET 200 https://siteassets.parastorage.com/pages/pages/thunderbolt` (application/json, 20382)
  - `GET 200 https://siteassets.parastorage.com/pages/pages/thunderbolt` (application/json, 44653)
  - `GET 200 https://www.fisherydb.com/_api/v1/access-tokens` (application/json, 64556)
  - `GET 200 https://static.parastorage.com/services/editor-elements/1.15127.0/rb_wixui.thunderbolt.manifest.min.json` (application/json, 43580)
- `marport-1`: relevant responses=2291, json responses=590, likely API endpoints=25
  - `GET 200 https://www.fisherydb.com/group/marport-1/discussion` (text/html, None)
  - `GET 200 https://siteassets.parastorage.com/pages/pages/thunderbolt` (application/json, 322110)
  - `GET 200 https://siteassets.parastorage.com/pages/pages/thunderbolt` (application/json, 67204)
  - `GET 200 https://siteassets.parastorage.com/pages/pages/thunderbolt` (application/json, 20382)
  - `GET 200 https://siteassets.parastorage.com/pages/pages/thunderbolt` (application/json, 44653)
  - `GET 200 https://www.fisherydb.com/_api/v1/access-tokens` (application/json, 64556)
  - `GET 200 https://static.parastorage.com/services/editor-elements/1.15127.0/rb_wixui.thunderbolt.manifest.min.json` (application/json, 43580)
  - `GET 200 https://static.parastorage.com/services/editor-elements/1.15127.0/rb_wixui.corvid.manifest.min.json` (application/json, 12037)
- `trondheim-issues`: relevant responses=2287, json responses=589, likely API endpoints=25
  - `GET 200 https://www.fisherydb.com/group/trondheim-issues/discussion` (text/html, None)
  - `GET 200 https://siteassets.parastorage.com/pages/pages/thunderbolt` (application/json, 322110)
  - `GET 200 https://siteassets.parastorage.com/pages/pages/thunderbolt` (application/json, 44653)
  - `GET 200 https://siteassets.parastorage.com/pages/pages/thunderbolt` (application/json, 67204)
  - `GET 200 https://siteassets.parastorage.com/pages/pages/thunderbolt` (application/json, 20382)
  - `GET 200 https://www.fisherydb.com/_api/v1/access-tokens` (application/json, 64556)
  - `GET 200 https://static.parastorage.com/services/editor-elements/1.15127.0/rb_wixui.thunderbolt.manifest.min.json` (application/json, 43580)
  - `GET 200 https://www.fisherydb.com/_api/tag-manager/api/v1/tags/sites/aae8aca6-317b-4aff-9e86-21f997d3e9c1` (application/json, 1143)

## Recommendation

Do not run full snapshot yet. Index pagination is not proven complete; use a hybrid strategy or continue Wix internal API/network investigation.
- Use December archive thread list as the seed for direct-open verification where current group index is incomplete.
- Promote any captured JSON/API endpoint with discussion IDs into the snapshot list builder after manual review.
- Keep network response samples sanitized and small; do not store cookies or auth headers.
