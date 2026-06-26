# Bug report locator — KRAKEN (ISSTA 2025)

Locates and classifies all bug reports filed by the first author of the KRAKEN paper.
Covers both the 37 KRAKEN target projects and any other projects the author reported bugs in.
See [CLAUDE.md](CLAUDE.md) for pipeline documentation.

---

## Classification logic

Each bug report is assigned one of three labels:

| Label | Meaning |
| --- | --- |
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

8 reports found by the pipeline. The classifier resolves 4 directly via CVE records (`paper_artifact`) and leaves 4 as `unknown` (8 found ≠ 6 expected). The mismatch — 8 found but only 6 in the paper — hints that duplicates exist. Inspecting the 4 unknowns against the 4 CVE-matched reports reveals two duplicate pairs: #544 ≡ #509 and #546 ≡ #615 (same crash, different reporters). Once the duplicates are excluded and their CVEs transferred to the author's reports, the remaining 4 unknowns resolve to `paper_artifact` and the count reaches 6.

| Issue | Auto CVE | Classifier | Human review |
| --- | --- | --- | --- |
| #540 | CVE-2020-23912 | `paper_artifact` | — |
| #545 | CVE-2021-32265 | `paper_artifact` | — |
| #509 | CVE-2020-23331 | `paper_artifact` | excluded — duplicate of #544 (seviezhou); CVE-2020-23331 transferred to #544 |
| #615 | CVE-2021-35306 | `paper_artifact` | excluded — duplicate of #546 (seviezhou); CVE-2021-35306 transferred to #546 |
| #544 | — | `unknown` (8 found ≠ 6) | `paper_artifact` — author's canonical report; receives CVE-2020-23331 from #509 |
| #546 | — | `unknown` (8 found ≠ 6) | `paper_artifact` — author's canonical report; receives CVE-2021-35306 from #615 |
| #539 | — | `unknown` (8 found ≠ 6) | `paper_artifact` — distinct crash site |
| #547 | — | `unknown` (8 found ≠ 6) | `paper_artifact` — distinct crash site |

---

## Stats

| | Count |
| --- | --- |
| Total bug reports found by pipeline | 258 |
| Classified by pipeline alone | 238 |
| Flagged `unknown` — needed manual inspection | 20 |
| **Final rows after overrides** | **247** |

Of the 20 flagged unknowns (across 6 projects: bento4, dmg2img, gocr, libraw, libredwg, ncurses):

| | Count |
| --- | --- |
| Duplicate entries excluded | 11 |
| Reclassified `unknown` → `paper_artifact` | 10 |
| CVE IDs assigned to author reports | 7 |

9 PR rows appear in the output with `related_url` pointing to their linked issue. 51 override entries in `data/static/patch.yaml` cover label corrections, CVE assignments, and CVE-reference notes.

---

## Override reasoning

See [LABEL.md](LABEL.md) for the per-project labelling decisions.
