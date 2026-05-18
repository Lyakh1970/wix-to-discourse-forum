# Local Dataset Analysis

Root: `E:\OneDrive\Documents\Claude\projects\fisherydb-forum-parser`

## Summary

- SQLite categories: **67**
- SQLite threads: **589**
- SQLite posts: **1236**
- SQLite comments: **647**
- SQLite attachments: **1151**
- Thread JSON files: **60**
- JSON threads/posts/comments: **589 / 1236 / 647**
- JSON attachment references: **1158**

## Key Files

| File | Status | Size |
|---|---|---:|
| `forum_data_db` | found | 11472896 |
| `category_mapping_json` | found | 2958 |
| `category_mapping_review_md` | found | 10280 |
| `discourse_categories_json` | found | 164732 |
| `forum_structure_detailed_json` | missing |  |
| `auth_state_json` | found | 7084 |

## Category Reconciliation

- SQLite categories: **67**
- Thread JSON categories: **60**
- Mapping slugs: **67**
- Discourse IDs referenced by mapping: **58**

### SQLite categories without `threads.json`

- `3d-design`
- `_nmea`
- `equipment`
- `fleet-orders`
- `issues-log-log-polomok`
- `km-orders`
- `mrto-2022-2023-2024`

### `threads.json` categories absent from SQLite

_None._

### SQLite categories missing from mapping

_None._

### Mapping slugs absent from SQLite

_None._

### Mapped Discourse IDs absent from `discourse_categories.json`

- `90`
- `91`
- `92`
- `93`
- `94`
- `95`
- `96`
- `97`
- `101`
- `103`
- `104`
- `105`
- `106`
- `109`

## Attachment Reconciliation

- SQLite attachment rows: **1151**
- JSON attachment references: **1158**
- JSON minus SQLite: **7**
- Local output attachment/image files: **1135**
- SQLite rows missing local_path: **15**
- SQLite rows with broken local_path: **0**
- JSON references missing local_path: **18**

### SQLite Attachments Missing Local Path

| Post ID | Filename | Type | URL |
|---|---|---|---|
| `63904b7ac846590012bf05f4` | `https://www.dropbox.com/static/metaserver/static/images/spectrum-icons/generated/content/content-exe-large.png` | png | https://static.wixstatic.com/media/https://www.dropbox.com/static/metaserver/static/images/spectrum-icons/generated/content/content-exe-large.png |
| `63904bf7c846590012bf0602` | `https://www.dropbox.com/temp_thumb_from_token/s/t7kj22yo9ji2vy6?preserve_transparency=False&size=1200x1200&size_mode=4&unfurl=1` | jpg | https://static.wixstatic.com/media/https://www.dropbox.com/temp_thumb_from_token/s/t7kj22yo9ji2vy6?preserve_transparency=False&size=1200x1200&size_mode=4&unfurl=1 |
| `64f97423096b680010e0603c` | `https://lh3.googleusercontent.com/docs/AOD9vFrqw8ZYKD-MOTKhtsiiOdhRhrF9fwQYsDblmWxb8dLINTDIMwXq3Iusvz15TSWy_5RXVlic7JQuwWufRb68DABMoR7Xk5ZiNAoyl7SAvmE=w1200-h630-p` | jpg | https://static.wixstatic.com/media/https://lh3.googleusercontent.com/docs/AOD9vFrqw8ZYKD-MOTKhtsiiOdhRhrF9fwQYsDblmWxb8dLINTDIMwXq3Iusvz15TSWy_5RXVlic7JQuwWufRb68DABMoR7Xk5ZiNAoyl7SAvmE=w1200-h630-p |
| `652ea3e808b50900101a892a` | `/web/wp-content/uploads/2023/09/CW-cockpit-edit2-1024x576.jpeg` | jpeg | https://static.wixstatic.com/media//web/wp-content/uploads/2023/09/CW-cockpit-edit2-1024x576.jpeg |
| `657b142feb80b000103846a5` | `https://www.dropbox.com/static/metaserver/static/images/opengraph/opengraph-content-icon-file-exe-landscape.png` | png | https://static.wixstatic.com/media/https://www.dropbox.com/static/metaserver/static/images/opengraph/opengraph-content-icon-file-exe-landscape.png |
| `65856269edbdce00103f8be2` | `https://www.dropbox.com/static/metaserver/static/images/opengraph/opengraph-content-icon-folder-dropbox-landscape.png` | png | https://static.wixstatic.com/media/https://www.dropbox.com/static/metaserver/static/images/opengraph/opengraph-content-icon-folder-dropbox-landscape.png |
| `65d1d91375cace00107afe1f` | `https://sklep.inveo.com.pl/464-large_default/hero-web-sensor.jpg` | jpg | https://static.wixstatic.com/media/https://sklep.inveo.com.pl/464-large_default/hero-web-sensor.jpg |
| `65d1d91375cace00107afe1f` | `https://sklep.inveo.com.pl/465-large_default/nano-temp.jpg` | jpg | https://static.wixstatic.com/media/https://sklep.inveo.com.pl/465-large_default/nano-temp.jpg |
| `66012bee955a430010bb86ca` | `https://www.dropbox.com/static/metaserver/static/images/opengraph/opengraph-content-icon-file-unknown-landscape.png` | png | https://static.wixstatic.com/media/https://www.dropbox.com/static/metaserver/static/images/opengraph/opengraph-content-icon-file-unknown-landscape.png |
| `6756e7fcbfcf59af44a39c91` | `https://lh7-us.googleusercontent.com/docs/AHkbwyJIAYbAsQMRp3uChL33eDSKsnfgAk5enp67GljQ70zUxuIV7-SEtkec7bJ-xqiyY9rxFa0uPxR9eWnu9ZwAaTeU36Ryi5p4COGD8pTgOkB1T_t4Ws4=w1200-h630-p` | jpg | https://static.wixstatic.com/media/https://lh7-us.googleusercontent.com/docs/AHkbwyJIAYbAsQMRp3uChL33eDSKsnfgAk5enp67GljQ70zUxuIV7-SEtkec7bJ-xqiyY9rxFa0uPxR9eWnu9ZwAaTeU36Ryi5p4COGD8pTgOkB1T_t4Ws4=w1200-h630-p |
| `6756e7fcbfcf59af44a39c91` | `https://lh7-us.googleusercontent.com/docs/AHkbwyJTV47bX4zBZf-I8_00qr8Ocy70TwjoqSVals_rWoRm8It1mL4DY3CeFAkryYLEt1JOrr17bmze6dCAe-xnkAdUNEWy2tEvNoV4lc_muFsrUIlYhTRV=w1200-h630-p` | jpg | https://static.wixstatic.com/media/https://lh7-us.googleusercontent.com/docs/AHkbwyJTV47bX4zBZf-I8_00qr8Ocy70TwjoqSVals_rWoRm8It1mL4DY3CeFAkryYLEt1JOrr17bmze6dCAe-xnkAdUNEWy2tEvNoV4lc_muFsrUIlYhTRV=w1200-h630-p |
| `6756e7fcbfcf59af44a39c91` | `https://lh7-us.googleusercontent.com/docs/AHkbwyK2Vp-Zzi2-UsSYHk82P_raw2AKZG2J91QLOmEBlCKfBlWJycVRK3Ax_wi-0w2waSxFgIUBHo9b_bWArysI6YRYJy4nHFwSYSVjCaUUAlq4m5II71SH=w1200-h630-p` | jpg | https://static.wixstatic.com/media/https://lh7-us.googleusercontent.com/docs/AHkbwyK2Vp-Zzi2-UsSYHk82P_raw2AKZG2J91QLOmEBlCKfBlWJycVRK3Ax_wi-0w2waSxFgIUBHo9b_bWArysI6YRYJy4nHFwSYSVjCaUUAlq4m5II71SH=w1200-h630-p |
| `6756e7fcbfcf59af44a39c91` | `https://lh7-us.googleusercontent.com/docs/AHkbwyL_YvNspuyyTXQ6e5Jnepj586hKfmZkb8atgbTGUAAlkARJEHb2KhBh1w5oGW8oMtmztLSO7QQ4wGuZ9xQ2qKf5D5PmhbJcrcKsxDHbnTySR2V4ekKM=w1200-h630-p` | jpg | https://static.wixstatic.com/media/https://lh7-us.googleusercontent.com/docs/AHkbwyL_YvNspuyyTXQ6e5Jnepj586hKfmZkb8atgbTGUAAlkARJEHb2KhBh1w5oGW8oMtmztLSO7QQ4wGuZ9xQ2qKf5D5PmhbJcrcKsxDHbnTySR2V4ekKM=w1200-h630-p |
| `6756e7fcbfcf59af44a39c91` | `https://lh7-us.googleusercontent.com/docs/AHkbwyLtmHKqLZKkkYydUEqTxwOzG5ggJIjfX0suzFR58qjA1zhnFBJFo_h5-LnSMO258WZ_lGu5WQyVLFf-bilumx1yGKDAFV7VfX9Up54W7DWyG9xurFbF=w1200-h630-p` | jpg | https://static.wixstatic.com/media/https://lh7-us.googleusercontent.com/docs/AHkbwyLtmHKqLZKkkYydUEqTxwOzG5ggJIjfX0suzFR58qjA1zhnFBJFo_h5-LnSMO258WZ_lGu5WQyVLFf-bilumx1yGKDAFV7VfX9Up54W7DWyG9xurFbF=w1200-h630-p |
| `6791f9b4b10608647a89287f` | `https://radiochief.ru/wp-content/uploads/2014/12/sr_srg.jpg` | jpg | https://static.wixstatic.com/media/https://radiochief.ru/wp-content/uploads/2014/12/sr_srg.jpg |

## Quality Checks

- Duplicate thread ids: **0**
- Duplicate thread URLs: **0**
- Duplicate post ids: **0**
- Duplicate attachment ids: **0**
- Categories where declared `thread_count` is zero: **67**
- Categories with at least one thread: **60**

## Recommendations

- Review SQLite categories without threads.json before Wix/Discourse comparison.
- Check mapped Discourse IDs that are not present in discourse_categories.json.
- Resolve attachment records without local_path or mark them as remote-only.
- Compare JSON attachment references against SQLite attachment rows.
