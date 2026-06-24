# Bug report locator — KRAKEN (ISSTA 2025)

Locates and classifies all bug reports filed by the first author of the KRAKEN paper.
Covers both the 37 KRAKEN target projects and any other projects the author reported bugs in.
See [CLAUDE.md](CLAUDE.md) for pipeline documentation.

---

## Classification logic

Each bug report is assigned one of three labels:

| Label | Meaning |
|---|---|
| `paper_artifact` | Bug was found and reported as part of the KRAKEN research |
| `activity_history` | Bug filed outside the paper scope (non-KRAKEN project, or project where all paper bugs have CVEs) |
| `unknown` | Cannot determine from available data alone |

The pipeline applies four rules in order:

**Rule 1 — Non-KRAKEN project** → `activity_history`  
The author filed bugs outside the 37 KRAKEN targets as normal open-source activity.

**Rule 2 — CVE match** → `paper_artifact`  
If a bug URL appears in the `references` field of any KRAKEN CVE JSON record, it is a confirmed paper artifact.

**Rule 3 — All-CVE project** → `activity_history` for no-CVE bugs  
If `projects.csv` shows `bugs == cves` (every paper bug got a CVE), any bug without a CVE cannot be a paper bug.

**Rule 4 — Count match** → `paper_artifact` or `unknown`  
For remaining KRAKEN bugs without a CVE: if the total found equals the paper's bug count, all are `paper_artifact`. Otherwise `unknown`.

### Example — bento4 (paper: 6 bugs, 4 CVEs)

| Issue | CVE | Classifier | Human review |
|---|---|---|---|
| #509 | CVE-2020-23331 | `paper_artifact` | — |
| #540 | CVE-2020-23912 | `paper_artifact` | — |
| #545 | CVE-2021-32265 | `paper_artifact` | — |
| #615 | CVE-2021-35306 | `paper_artifact` | — |
| #539 | — | `unknown` (8 found ≠ 6) | `paper_artifact` — distinct bug; count resolves after deduplication |
| #547 | — | `unknown` (8 found ≠ 6) | `paper_artifact` — distinct bug; count resolves after deduplication |
| #544 | — | `unknown` (8 found ≠ 6) | excluded — duplicate of #539, same crash different tool (`mp4info` vs `mp42aac`) |
| #546 | — | `unknown` (8 found ≠ 6) | excluded — duplicate of #540, same crash different tool |

---

## Stats

| | Count |
|---|---|
| Total bug reports found by pipeline | 258 |
| Classified by pipeline alone | 238 |
| Flagged `unknown` — needed manual inspection | 20 |
| **Final rows after overrides** | **248** |

Of the 20 flagged unknowns (across 6 projects: bento4, dmg2img, gocr, libraw, libredwg, ncurses):

| | Count |
|---|---|
| Duplicate entries excluded | 10 |
| Reclassified `unknown` → `paper_artifact` | 16 |
| CVE IDs assigned to upstream reports | 2 |
| Reporters set (deleted/archived issues) | 6 |

---

## Override reasoning

Projects are flagged when pipeline `paper_artifact` count or unique CVE count differs from
`data/projects.csv`. Raw HTML pages for all rows in flagged projects are fetched
(`python main.py review`), reasoned over by Claude Code, and verified manually.

| Project | Paper | Found | Actions | Reasoning |
|---|---|---|---|---|
| **bento4** | 6 bugs, 4 CVEs | 8 rows, 4 CVEs | Exclude #544, #546. Reclassify #539, #547 → `paper_artifact` | #544 and #539 both crash in `AP4_Descriptor::GetTag()` at commit `174b94`, triggered by `mp4info` vs `mp42aac`. #546 and #540 both crash in `AP4_StszAtom::WriteFields`, same commit, same pattern. After excluding the two tool-duplicates, 6 = 6 ✓ |
| **dmg2img** | 7 bugs, 2 CVEs | 9 rows, 2 CVEs | Exclude Bugzilla 1959585, 1959911. Reclassify issues/8–14 → `paper_artifact`. Set CVE on #9, #11 | The 2 Red Hat Bugzilla entries are downstream CVE tracking records. Their HTML bodies explicitly link the upstream GitHub reports: Bugzilla 1959585 → issues/9 (CVE-2021-3548), Bugzilla 1959911 → issues/11 (CVE-2021-32614). After exclusion, 7 distinct GitHub issues = 7 ✓ |
| **gocr** | 4 bugs, 3 CVEs | 7 rows, 3 CVEs | Exclude Bugzilla 1962854, 1962861, 1962865 | Same pattern as dmg2img. Bugzilla pages reference SF upstream reports: 1962854 → bugs/40 and bugs/41 (CVE-2021-33480 covers two use-after-free bugs in `context_correction()`), 1962861 → bugs/39, 1962865 → bugs/42. After exclusion, 4 SF issues = 4 ✓ |
| **gpac** | 12 bugs, 9 CVEs | 12 rows, 8 CVEs | None | Bug count matches. CVE count is 8 vs 9 — the 9th CVE is not present in the KRAKEN README trophy list and therefore absent from our CVE cache. Issues #1570 and #1571 have no CVE assigned; one likely holds the missing CVE. No reclassification needed. |
| **libraw** | 3 bugs, 1 CVE | 4 rows, 1 CVE | Exclude #318. Reclassify #319, #322 → `paper_artifact` | #318 and #319 both crash in `LibRaw::identify_process_dng_fields()`, commit `87792a`, tool `simple_dcraw`, error `stack-buffer-overflow READ 8` — identical call stacks, lines 1309 vs 1314. CVE-2020-24870 (#330) also crashes at `identify.cpp:1309`, same site as #318. Excluding #318: 1 CVE + #319 + #322 = 3 ✓ |
| **libredwg** | 12 bugs, 9 CVEs | 13 rows, 8 CVEs | Exclude #257. Reclassify #253, #259, #260, #265 → `paper_artifact` | #257 and #256 (CVE-2021-39528) are the same double-free at commit `4b99ed` — ASan traces show the same heap address `0x60400000dfd0`, triggered via `dwg2dxf` vs `dwgbmp`. After exclusion: 8 CVE + 4 unknowns = 12 ✓. The 9th CVE is absent from our cache. |
| **ncurses** | 2 bugs, 1 CVE | 3 rows, 1 CVE | Exclude msg00023. Reclassify msg00007 → `paper_artifact` | CVE-2021-39537 JSON `references` lists both msg00006 and msg00023 for the same `_nc_captoinfo` heap-overflow — msg00023 is a duplicate reference, not a separate bug. msg00007 is a distinct report (memory leak in `_nc_resolve_uses2` at `comp_parse.c:470`). After exclusion: 2 = 2 ✓ |
