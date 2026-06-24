# Override reasoning

Projects are flagged when pipeline `paper_artifact` count or unique CVE count differs from
`data/projects.csv`. Raw HTML pages for all rows in flagged projects are fetched
(`python main.py review`), reasoned over by Claude Code, and confirmed manually
([ai-overrides](data/ai/ai-overrides.yaml), [overrides](data/overrides.yaml)).

| Project | Paper | Found | Actions | Reasoning |
|---|---|---|---|---|
| **bento4** | 6 bugs, 4 CVEs | 8 rows, 4 CVEs | #539 and #544 count as one bug (`related_url`). #540 and #546 count as one bug (`related_url`). Reclassify #539, #547 → `paper_artifact` | #544 and #539 both crash in `AP4_Descriptor::GetTag()` at commit `174b94`, triggered by `mp4info` vs `mp42aac`. #546 and #540 both crash in `AP4_StszAtom::WriteFields`, same commit, same pattern. After deduplication, 6 = 6 ✓ |
| **libraw** | 3 bugs, 1 CVE | 4 rows, 1 CVE | #318 and #319 count as one bug (`related_url`). Reclassify #319, #322 → `paper_artifact` | #318 and #319 both crash in `LibRaw::identify_process_dng_fields()`, same function, same file, [fixed in the same commit](https://github.com/LibRaw/LibRaw/commit/4feaed4dea636cee4fee010f615881ccf76a096d). After deduplication: 1 CVE + #319 + #322 = 3 ✓ |
| **libredwg** | 12 bugs, 9 CVEs | 13 rows, 8 CVEs | #256 and #257 count as one bug (`related_url`). Reclassify #253, #259, #260, #265 → `paper_artifact` | #257 and #256 (CVE-2021-39528) are the same double-free at commit `4b99ed` — ASan traces show the same heap address `0x60400000dfd0`, triggered via `dwg2dxf` vs `dwgbmp`. After deduplication: 8 CVE + 4 unknowns = 12 ✓. The 9th CVE is in the trophy list but failed to fetch from CVEProject/cvelistV5 (404). |
