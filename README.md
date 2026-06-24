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
| Total bug reports found by pipeline | 295 |
| Classified by pipeline alone | 275 |
| Flagged `unknown` — needed manual inspection | 20 |
| **Final rows after overrides** | **272** |

Of the 20 flagged unknowns (across 6 projects: bento4, dmg2img, gocr, libraw, libredwg, ncurses):

| | Count |
|---|---|
| Duplicate entries excluded | 10 |
| Reclassified `unknown` → `paper_artifact` | 16 |
| CVE IDs assigned to upstream reports | 2 |
| Reporters set (deleted/archived issues) | 6 |

PR rows are handled separately: 13 matched PRs are collapsed into their linked issue's `related_url` and excluded from the row count; 24 unmatched PRs (no linked issue found) retain their own rows.

---

## Override reasoning

See [LABEL.md](LABEL.md) for the per-project labelling decisions.
