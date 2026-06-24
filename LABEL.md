# Override reasoning

Projects are flagged when pipeline `paper_artifact` count or unique CVE count differs from
`data/projects.csv`. Raw HTML pages for all rows in flagged projects are fetched
(`python main.py review`), reasoned over by Claude Code ([suggestions](data/ai/suggestions.md)),
and verified manually ([overrides](data/overrides.yaml)).

| Project | Paper | Found | Actions | Reasoning |
|---|---|---|---|---|
| **bento4** | 6 bugs, 4 CVEs | 8 rows, 4 CVEs | Exclude #544, #546. Reclassify #539, #547 → `paper_artifact` | #544 and #539 both crash in `AP4_Descriptor::GetTag()` at commit `174b94`, triggered by `mp4info` vs `mp42aac`. #546 and #540 both crash in `AP4_StszAtom::WriteFields`, same commit, same pattern. After excluding the two tool-duplicates, 6 = 6 ✓ |
| **dmg2img** | 7 bugs, 2 CVEs | 9 rows, 2 CVEs | Exclude Bugzilla 1959585, 1959911. Reclassify issues/8–14 → `paper_artifact`. Set CVE on #9, #11 | The 2 Red Hat Bugzilla entries are downstream CVE tracking records. Their HTML bodies explicitly link the upstream GitHub reports: Bugzilla 1959585 → issues/9 (CVE-2021-3548), Bugzilla 1959911 → issues/11 (CVE-2021-32614). After exclusion, 7 distinct GitHub issues = 7 ✓ |
| **gocr** | 4 bugs, 3 CVEs | 7 rows, 3 CVEs | Exclude Bugzilla 1962854, 1962861, 1962865 | Same pattern as dmg2img. Bugzilla pages reference SF upstream reports: 1962854 → bugs/40 and bugs/41 (CVE-2021-33480 covers two use-after-free bugs in `context_correction()`), 1962861 → bugs/39, 1962865 → bugs/42. After exclusion, 4 SF issues = 4 ✓ |
| **gpac** | 12 bugs, 9 CVEs | 12 rows, 8 CVEs | None | Bug count matches. CVE count is 8 vs 9 — the 9th CVE is not present in the KRAKEN README trophy list and therefore absent from our CVE cache. Issues #1570 and #1571 have no CVE assigned; one likely holds the missing CVE. No reclassification needed. |
| **libraw** | 3 bugs, 1 CVE | 4 rows, 1 CVE | Exclude #318. Reclassify #319, #322 → `paper_artifact` | #318 and #319 both crash in `LibRaw::identify_process_dng_fields()`, commit `87792a`, tool `simple_dcraw`, error `stack-buffer-overflow READ 8` — identical call stacks, lines 1309 vs 1314. CVE-2020-24870 (#330) also crashes at `identify.cpp:1309`, same site as #318. Excluding #318: 1 CVE + #319 + #322 = 3 ✓ |
| **libredwg** | 12 bugs, 9 CVEs | 13 rows, 8 CVEs | Exclude #257. Reclassify #253, #259, #260, #265 → `paper_artifact` | #257 and #256 (CVE-2021-39528) are the same double-free at commit `4b99ed` — ASan traces show the same heap address `0x60400000dfd0`, triggered via `dwg2dxf` vs `dwgbmp`. After exclusion: 8 CVE + 4 unknowns = 12 ✓. The 9th CVE is absent from our cache. |
| **ncurses** | 2 bugs, 1 CVE | 3 rows, 1 CVE | Exclude msg00023. Reclassify msg00007 → `paper_artifact` | CVE-2021-39537 JSON `references` lists both msg00006 and msg00023 for the same `_nc_captoinfo` heap-overflow — msg00023 is a duplicate reference, not a separate bug. msg00007 is a distinct report (memory leak in `_nc_resolve_uses2` at `comp_parse.c:470`). After exclusion: 2 = 2 ✓ |
