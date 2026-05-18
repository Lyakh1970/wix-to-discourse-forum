# Archive Completeness Audit

Root: `E:\OneDrive\Documents\Claude\projects\fisherydb-forum-parser`

## Scope

- Discourse API: not used
- Discourse category mapping correctness: not checked as an error
- Primary source: `output/forum_data.db`
- Secondary source: `output/*/threads.json`

## A. Archive Self-Containment

| Check | Value |
|---|---:|
| SQLite categories | 67 |
| SQLite categories with threads | 60 |
| Categories with threads.json | 60 |
| Threads | 589 |
| Posts | 1236 |
| Original posts | 589 |
| Comments | 647 |
| Attachments | 1151 |
| Images | 1055 |
| Referenced local files present | 1135 |
| Physical local attachment/image files | 1135 |

## B. Data Quality

| Check | Value |
|---|---:|
| Threads without title | 0 |
| Threads without author | 0 |
| Threads without date | 0 |
| Threads without category | 0 |
| Posts/comments without body | 0 |
| Posts/comments without author | 0 |
| Posts/comments without date | 0 |
| Attachments without local_path | 15 |
| Attachments with broken local_path | 0 |
| Suspicious short bodies (<20 chars) | 12 |
| Bodies containing Wix/security error markers | 0 |

### Attachments Without Local Path

| post_id | filename | file_type | url |
|---|---|---|---|
| 63904b7ac846590012bf05f4 | https://www.dropbox.com/static/metaserver/static/images/spectrum-icons/generated/content/content-exe-large.png | png | https://static.wixstatic.com/media/https://www.dropbox.com/static/metaserver/static/images/spectrum-icons/generated/content/content-exe-large.png |
| 63904bf7c846590012bf0602 | https://www.dropbox.com/temp_thumb_from_token/s/t7kj22yo9ji2vy6?preserve_transparency=False&size=1200x1200&size_mode=4&unfurl=1 | jpg | https://static.wixstatic.com/media/https://www.dropbox.com/temp_thumb_from_token/s/t7kj22yo9ji2vy6?preserve_transparency=False&size=1200x1200&size_mode=4&unfurl=1 |
| 64f97423096b680010e0603c | https://lh3.googleusercontent.com/docs/AOD9vFrqw8ZYKD-MOTKhtsiiOdhRhrF9fwQYsDblmWxb8dLINTDIMwXq3Iusvz15TSWy_5RXVlic7JQuwWufRb68DABMoR7Xk5ZiNAoyl7SAvmE=w1200-h630-p | jpg | https://static.wixstatic.com/media/https://lh3.googleusercontent.com/docs/AOD9vFrqw8ZYKD-MOTKhtsiiOdhRhrF9fwQYsDblmWxb8dLINTDIMwXq3Iusvz15TSWy_5RXVlic7JQuwWufRb68DABMoR7Xk5ZiNAoyl7SAvmE=w1200-h630-p |
| 652ea3e808b50900101a892a | /web/wp-content/uploads/2023/09/CW-cockpit-edit2-1024x576.jpeg | jpeg | https://static.wixstatic.com/media//web/wp-content/uploads/2023/09/CW-cockpit-edit2-1024x576.jpeg |
| 657b142feb80b000103846a5 | https://www.dropbox.com/static/metaserver/static/images/opengraph/opengraph-content-icon-file-exe-landscape.png | png | https://static.wixstatic.com/media/https://www.dropbox.com/static/metaserver/static/images/opengraph/opengraph-content-icon-file-exe-landscape.png |
| 65856269edbdce00103f8be2 | https://www.dropbox.com/static/metaserver/static/images/opengraph/opengraph-content-icon-folder-dropbox-landscape.png | png | https://static.wixstatic.com/media/https://www.dropbox.com/static/metaserver/static/images/opengraph/opengraph-content-icon-folder-dropbox-landscape.png |
| 65d1d91375cace00107afe1f | https://sklep.inveo.com.pl/464-large_default/hero-web-sensor.jpg | jpg | https://static.wixstatic.com/media/https://sklep.inveo.com.pl/464-large_default/hero-web-sensor.jpg |
| 65d1d91375cace00107afe1f | https://sklep.inveo.com.pl/465-large_default/nano-temp.jpg | jpg | https://static.wixstatic.com/media/https://sklep.inveo.com.pl/465-large_default/nano-temp.jpg |
| 66012bee955a430010bb86ca | https://www.dropbox.com/static/metaserver/static/images/opengraph/opengraph-content-icon-file-unknown-landscape.png | png | https://static.wixstatic.com/media/https://www.dropbox.com/static/metaserver/static/images/opengraph/opengraph-content-icon-file-unknown-landscape.png |
| 6756e7fcbfcf59af44a39c91 | https://lh7-us.googleusercontent.com/docs/AHkbwyJIAYbAsQMRp3uChL33eDSKsnfgAk5enp67GljQ70zUxuIV7-SEtkec7bJ-xqiyY9rxFa0uPxR9eWnu9ZwAaTeU36Ryi5p4COGD8pTgOkB1T_t4Ws4=w1200-h630-p | jpg | https://static.wixstatic.com/media/https://lh7-us.googleusercontent.com/docs/AHkbwyJIAYbAsQMRp3uChL33eDSKsnfgAk5enp67GljQ70zUxuIV7-SEtkec7bJ-xqiyY9rxFa0uPxR9eWnu9ZwAaTeU36Ryi5p4COGD8pTgOkB1T_t4Ws4=w1200-h630-p |
| 6756e7fcbfcf59af44a39c91 | https://lh7-us.googleusercontent.com/docs/AHkbwyJTV47bX4zBZf-I8_00qr8Ocy70TwjoqSVals_rWoRm8It1mL4DY3CeFAkryYLEt1JOrr17bmze6dCAe-xnkAdUNEWy2tEvNoV4lc_muFsrUIlYhTRV=w1200-h630-p | jpg | https://static.wixstatic.com/media/https://lh7-us.googleusercontent.com/docs/AHkbwyJTV47bX4zBZf-I8_00qr8Ocy70TwjoqSVals_rWoRm8It1mL4DY3CeFAkryYLEt1JOrr17bmze6dCAe-xnkAdUNEWy2tEvNoV4lc_muFsrUIlYhTRV=w1200-h630-p |
| 6756e7fcbfcf59af44a39c91 | https://lh7-us.googleusercontent.com/docs/AHkbwyK2Vp-Zzi2-UsSYHk82P_raw2AKZG2J91QLOmEBlCKfBlWJycVRK3Ax_wi-0w2waSxFgIUBHo9b_bWArysI6YRYJy4nHFwSYSVjCaUUAlq4m5II71SH=w1200-h630-p | jpg | https://static.wixstatic.com/media/https://lh7-us.googleusercontent.com/docs/AHkbwyK2Vp-Zzi2-UsSYHk82P_raw2AKZG2J91QLOmEBlCKfBlWJycVRK3Ax_wi-0w2waSxFgIUBHo9b_bWArysI6YRYJy4nHFwSYSVjCaUUAlq4m5II71SH=w1200-h630-p |
| 6756e7fcbfcf59af44a39c91 | https://lh7-us.googleusercontent.com/docs/AHkbwyL_YvNspuyyTXQ6e5Jnepj586hKfmZkb8atgbTGUAAlkARJEHb2KhBh1w5oGW8oMtmztLSO7QQ4wGuZ9xQ2qKf5D5PmhbJcrcKsxDHbnTySR2V4ekKM=w1200-h630-p | jpg | https://static.wixstatic.com/media/https://lh7-us.googleusercontent.com/docs/AHkbwyL_YvNspuyyTXQ6e5Jnepj586hKfmZkb8atgbTGUAAlkARJEHb2KhBh1w5oGW8oMtmztLSO7QQ4wGuZ9xQ2qKf5D5PmhbJcrcKsxDHbnTySR2V4ekKM=w1200-h630-p |
| 6756e7fcbfcf59af44a39c91 | https://lh7-us.googleusercontent.com/docs/AHkbwyLtmHKqLZKkkYydUEqTxwOzG5ggJIjfX0suzFR58qjA1zhnFBJFo_h5-LnSMO258WZ_lGu5WQyVLFf-bilumx1yGKDAFV7VfX9Up54W7DWyG9xurFbF=w1200-h630-p | jpg | https://static.wixstatic.com/media/https://lh7-us.googleusercontent.com/docs/AHkbwyLtmHKqLZKkkYydUEqTxwOzG5ggJIjfX0suzFR58qjA1zhnFBJFo_h5-LnSMO258WZ_lGu5WQyVLFf-bilumx1yGKDAFV7VfX9Up54W7DWyG9xurFbF=w1200-h630-p |
| 6791f9b4b10608647a89287f | https://radiochief.ru/wp-content/uploads/2014/12/sr_srg.jpg | jpg | https://static.wixstatic.com/media/https://radiochief.ru/wp-content/uploads/2014/12/sr_srg.jpg |

### Suspicious Short Body Sample

| post_id | thread_id | category_slug | body_length | body_preview |
|---|---|---|---|---|
| 658bfc84fd348c0011076cd2 | astican-permit-request-link | staff-only | 13 | QUESTIONNAIRE |
| C-c1dfffdb-1b98-4bde-ad33-a476e8df5ea3 | catsat-podgotovka-k-ustanovke | catsat | 12 | FT ПК MaxSea |
| C-d0778be1-5d50-4efe-8046-82d528f609f6 | catsat-podgotovka-k-ustanovke | catsat | 8 | FV PC IE |
| C-56d877a7-cbf8-4f7b-86fc-a9c9c2329aa7 | fk-re-03-2024 | fk-orders | 19 | В стадии обсуждения |
| C-cfc46f0b-2ceb-40a6-99ce-510fab7abdbc | ggs-ryabina-opisanie-blokov | rjabina | 7 | атавизм |
| 68edf21a29364ee32f91aa20 | intermec-px4i-spare-parts-catalog | honeywell-px4 | 16 | NY_PX_spares.pdf |
| C-9c4fd4af-70bf-4cd8-bedd-ebe1c4df6225 | marport-ds-15-00-s-n-4194776-8f9a | marport-1 | 14 | KM CALIBRATION |
| C-fb684239-7fcc-466a-8254-863680937a19 | marport-ds-ss-16-00-s-n-4194777-d3f2 | marport-1 | 19 | KM CALIBRATION DATA |
| C-31a20ffb-c124-458e-8bf4-121fede0bd1c | marport-ds-ss-16-00-s-n-na-4aec | marport-1 | 14 | KM CALIBRATION |
| C-377ee8e6-2011-47a2-8d9e-a269a9198fe0 | new-vessels-e-mail-how-to-jan-2024 | obshchie-voprosy | 10 | Выполнено. |
| C-260ce608-f586-4d12-b45a-0ecdd18dc849 | perenos-kamery-flir-na-nosovoy-portal-na-pedestal-antenny-vsat | _flir | 15 | Ну и два фото 🤓 |
| C-9a168881-cc09-4753-ae9c-b1e83b626b51 | sumrad-es80-38khz-vibrator-replacement | ___ks | 17 | Понятно, спасибо. |

## C. SQLite vs JSON Consistency

| Check | Value |
|---|---:|
| Threads SQLite / JSON | 589 / 589 |
| Posts SQLite / JSON | 1236 / 1236 |
| Comments SQLite / JSON | 647 / 647 |
| Attachment refs SQLite / JSON | 1151 / 1158 |
| Attachment delta JSON - SQLite | 7 |


### SQLite categories without threads.json

- `3d-design`
- `_nmea`
- `equipment`
- `fleet-orders`
- `issues-log-log-polomok`
- `km-orders`
- `mrto-2022-2023-2024`

### SQLite categories with threads but without threads.json

_None._

### threads.json categories missing from SQLite

_None._
## D. Category Coverage

| Slug | Name | Threads | Posts | Comments | Attachments | threads.json | Status |
|---|---|---:|---:|---:|---:|---|---|
| `3d-design` | 3D DESIGN | 0 | 0 | 0 | 0 | no | DB_ONLY_EMPTY |
| `___fs` | FS | 9 | 12 | 3 | 3 | yes | OK |
| `___km` | KM | 5 | 7 | 2 | 12 | yes | OK |
| `___ks` | KS | 8 | 12 | 4 | 28 | yes | OK |
| `___mk` | MK | 12 | 18 | 6 | 31 | yes | OK |
| `__ais` | AIS | 3 | 7 | 4 | 2 | yes | OK |
| `__q-a` | Q&A | 11 | 15 | 4 | 18 | yes | OK |
| `_cctv` | CCTV | 1 | 1 | 0 | 1 | yes | OK |
| `_flir` | Flir | 5 | 21 | 16 | 14 | yes | OK |
| `_gyro` | GYRO | 1 | 1 | 0 | 2 | yes | OK |
| `_nmea` | NMEA | 0 | 0 | 0 | 0 | no | DB_ONLY_EMPTY |
| `_nmea-1` | NMEA (2) | 3 | 3 | 0 | 5 | yes | OK |
| `_olex` | Olex | 4 | 7 | 3 | 9 | yes | OK |
| `belize-orbcomm` | BELIZE ORBCOMM | 2 | 3 | 1 | 12 | yes | OK |
| `brands` | Brands | 1 | 1 | 0 | 1 | yes | OK |
| `catches` | Catches | 1 | 1 | 0 | 1 | yes | OK |
| `catsat` | CATSAT | 3 | 7 | 4 | 8 | yes | OK |
| `equipment` | Equipment | 0 | 0 | 0 | 0 | no | DB_ONLY_EMPTY |
| `ff-issues` | FF ISSUES | 25 | 38 | 13 | 38 | yes | OK |
| `ff-orders` | FF orders | 5 | 5 | 0 | 5 | yes | OK |
| `fk-catches` | FK catches | 2 | 2 | 0 | 1 | yes | OK |
| `fk-orders` | FK orders | 20 | 31 | 11 | 37 | yes | OK |
| `fleet-express` | Fleet express | 3 | 4 | 1 | 4 | yes | OK |
| `fleet-orders` | Fleet Orders | 0 | 0 | 0 | 0 | no | DB_ONLY_EMPTY |
| `fs-catches` | FS catches | 1 | 1 | 0 | 0 | yes | OK |
| `fs-issues` | FS ISSUES | 30 | 112 | 82 | 31 | yes | OK |
| `fs-orders` | FS orders | 8 | 11 | 3 | 10 | yes | OK |
| `fsea-cathes` | FSea catches | 1 | 1 | 0 | 0 | yes | OK |
| `fsea-orders` | FSea orders | 23 | 37 | 14 | 33 | yes | OK |
| `ft-orders` | FT orders | 10 | 22 | 12 | 22 | yes | OK |
| `furuno` | Furuno | 17 | 24 | 7 | 32 | yes | OK |
| `fv-catches` | FV catches | 1 | 1 | 0 | 0 | yes | OK |
| `fv-orders` | FV orders | 13 | 13 | 0 | 15 | yes | OK |
| `honeywell-px4` | Honeywell PX4 | 16 | 21 | 5 | 48 | yes | OK |
| `inmarsat-c` | INMARSAT-C | 2 | 2 | 0 | 1 | yes | OK |
| `issues-log-log-polomok` | Issues Log /// Лог поломок | 0 | 0 | 0 | 0 | no | DB_ONLY_EMPTY |
| `jotron` | Jotron | 1 | 1 | 0 | 3 | yes | OK |
| `km-catches` | KM catches | 1 | 1 | 0 | 0 | yes | OK |
| `km-issues` | KM ISSUES | 30 | 108 | 78 | 55 | yes | OK |
| `km-orders` | KM orders | 0 | 0 | 0 | 0 | no | DB_ONLY_EMPTY |
| `ks-issues` | KS ISSUES | 30 | 174 | 144 | 62 | yes | OK |
| `lan-staff` | LAN STAFF | 12 | 14 | 2 | 24 | yes | OK |
| `marport` | Marport | 12 | 19 | 7 | 18 | yes | OK |
| `marport-1` | MARPORT | 30 | 93 | 63 | 8 | yes | OK |
| `maxar-insightexplorer` | MAXAR | 6 | 8 | 2 | 10 | yes | OK |
| `mk-issues` | MK ISSUES | 30 | 52 | 22 | 130 | yes | OK |
| `mn-issue` | MN ISSUES | 10 | 12 | 2 | 0 | yes | OK |
| `monitoring` | Monitoring | 1 | 1 | 0 | 0 | yes | OK |
| `mrto-2022-2023-2024` | MRTO 2022-2023-2024 | 0 | 0 | 0 | 0 | no | DB_ONLY_EMPTY |
| `mrto-obshchie-voprosy` | MRTO Общие вопросы | 5 | 7 | 2 | 10 | yes | OK |
| `mv-issues` | MV ISSUES | 30 | 71 | 41 | 45 | yes | OK |
| `network` | NETWORK | 12 | 17 | 5 | 37 | yes | OK |
| `obshchie-voprosy` | Общие вопросы | 11 | 21 | 10 | 23 | yes | OK |
| `other-equipment` | OTHER EQUIPMENT | 30 | 46 | 16 | 79 | yes | OK |
| `other-equipment-on-board` | Other equipment on board | 3 | 3 | 0 | 8 | yes | OK |
| `raritan` | Raritan | 2 | 2 | 0 | 2 | yes | OK |
| `rjabina` | RJABINA | 9 | 12 | 3 | 7 | yes | OK |
| `simrad` | Simrad | 10 | 15 | 5 | 28 | yes | OK |
| `simrad-1` | SIMRAD | 6 | 7 | 1 | 4 | yes | OK |
| `staff-only` | Staff Only | 7 | 7 | 0 | 1 | yes | OK |
| `starlink` | STARLINK | 12 | 18 | 6 | 57 | yes | OK |
| `starlink-iridium-bandle` | STARLINK-IRIDIUM BANDLE | 3 | 3 | 0 | 1 | yes | OK |
| `transas` | TRANSAS | 2 | 4 | 2 | 5 | yes | OK |
| `trawltec` | TRAWLTEC | 3 | 6 | 3 | 19 | yes | OK |
| `triton` | TRITON | 7 | 8 | 1 | 13 | yes | OK |
| `trondheim-issues` | FT ISSUES | 24 | 59 | 35 | 71 | yes | OK |
| `video-cctv` | VIDEO CCTV | 4 | 6 | 2 | 7 | yes | OK |

## E. Practical Conclusion

- Can use local archive as working source: **yes**

### Blocking import issues

_None._

### Non-blocking review issues

- `Some attachment records have no local_path and may be remote-only embeds/previews.`
- `Some posts/comments have suspiciously short bodies.`
- `SQLite and JSON attachment reference counts differ.`
- `Some SQLite-only categories are empty and can be treated as structural remnants.`
- Can proceed to read-only Wix Groups check: **yes**

### Data to additionally verify via Wix Groups

- `Categories or topics involved in attachment count mismatches.`
- `Posts with missing local_path attachments that may be remote-only embeds.`
- `Representative high-volume categories to validate archive completeness against visible Wix Groups.`
