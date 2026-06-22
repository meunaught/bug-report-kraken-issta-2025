# Manual overrides for classified_bugs_mahadi.csv

After running `python main.py generate`, apply the following corrections to
`output/classified_bugs.csv` and write the result to `output/classified_bugs_mahadi.csv`.

---

## Exclude rows (remove entirely)

| report_url | reason |
|---|---|
| https://lists.gnu.org/archive/html/bug-ncurses/2021-10/msg00023.html | Duplicate CVE reference for ncurses; the 2020-08 ML post is the canonical entry |
| https://github.com/LibRaw/LibRaw/issues/318 | Consolidated into issue #319 via related_url |
| https://bugzilla.redhat.com/show_bug.cgi?id=1959585 | Downstream duplicate of dmg2img/issues/9 (CVE-2021-3548) |
| https://bugzilla.redhat.com/show_bug.cgi?id=1959911 | Downstream duplicate of dmg2img/issues/11 (CVE-2021-32614) |
| https://bugzilla.redhat.com/show_bug.cgi?id=1962854 | Downstream duplicate of jocr/bugs/40 and /41 (CVE-2021-33480) |
| https://bugzilla.redhat.com/show_bug.cgi?id=1962861 | Downstream duplicate of jocr/bugs/39 (CVE-2021-33479) |
| https://bugzilla.redhat.com/show_bug.cgi?id=1962865 | Downstream duplicate of jocr/bugs/42 (CVE-2021-33481) |

## Force `where_url_found = activity_history`

_None currently — projects where all paper bugs have CVEs are handled automatically
(libelfin, libslax, retdec, sela: bugs == cves in projects.csv → no-CVE found bugs
are classified activity\_history by the pipeline)._

## Manual updates for the following unknowns

| report_url | where_url_found | reason |
|---|---|---|
| https://github.com/LibRaw/LibRaw/issues/319 | paper_artifact | Issues #318 and #319 count as one bug; both are paper bugs |
| https://github.com/LibRaw/LibRaw/issues/322 | paper_artifact | Count-based pass leaves this unresolved; confirmed paper bug |
| https://github.com/Lekensteyn/dmg2img/issues/8 | paper_artifact | All 7 dmg2img bugs are paper bugs; After excluding bugzilla duplicates, 7/7 matches
| https://github.com/Lekensteyn/dmg2img/issues/9 | paper_artifact | Same as above |
| https://github.com/Lekensteyn/dmg2img/issues/10 | paper_artifact | Same as above |
| https://github.com/Lekensteyn/dmg2img/issues/11 | paper_artifact | Same as above |
| https://github.com/Lekensteyn/dmg2img/issues/12 | paper_artifact | Same as above |
| https://github.com/Lekensteyn/dmg2img/issues/13 | paper_artifact | Same as above |
| https://github.com/Lekensteyn/dmg2img/issues/14 | paper_artifact | Same as above |
| https://lists.gnu.org/archive/html/bug-ncurses/2020-08/msg00007.html | paper_artifact | after excluding duplicate msg00023; 2/2 ncurses bugs are paper bugs |

## Set `cve_id`

| report_url | cve_id | reason |
|---|---|---|
| https://github.com/Lekensteyn/dmg2img/issues/9 | CVE-2021-3548 | CVE only references downstream redhat entry (id=1959585); this is the upstream report |
| https://github.com/Lekensteyn/dmg2img/issues/11 | CVE-2021-32614 | CVE only references downstream redhat entry (id=1959911); this is the upstream report |

## Set `reporter`

| report_url | reporter | reason |
|---|---|---|
| https://github.com/leonhad/pdftools/issues/1 | seviezhou | Verified by manual inspection of Wayback snapshot |
| https://github.com/leonhad/pdftools/issues/2 | seviezhou | Verified by manual inspection of Wayback snapshot |
| https://github.com/leonhad/pdftools/issues/3 | seviezhou | Verified by manual inspection of Wayback snapshot |
| https://github.com/leonhad/pdftools/issues/4 | seviezhou | Verified by manual inspection of Wayback snapshot |
| https://github.com/leonhad/pdftools/issues/5 | seviezhou | Verified by manual inspection of Wayback snapshot |
| https://github.com/leonhad/pdftools/issues/6 | seviezhou | Verified by manual inspection of Wayback snapshot |

## Set `related_url`

| report_url | related_url | reason |
|---|---|---|
| https://github.com/LibRaw/LibRaw/issues/319 | https://github.com/LibRaw/LibRaw/issues/318 | #318 is the excluded companion issue |
| https://github.com/leonhad/pdftools/issues/1 | https://web.archive.org/web/20201018023239/https://github.com/leonhad/pdftools/issues/1 | Original issue deleted; Wayback snapshot is the live copy |
| https://github.com/leonhad/pdftools/issues/2 | https://web.archive.org/web/20201018023239/https://github.com/leonhad/pdftools/issues/2 | Original issue deleted; Wayback snapshot is the live copy |
| https://github.com/leonhad/pdftools/issues/3 | https://web.archive.org/web/20201018023240/https://github.com/leonhad/pdftools/issues/3 | Original issue deleted; Wayback snapshot is the live copy |
| https://github.com/leonhad/pdftools/issues/4 | https://web.archive.org/web/20201018023240/https://github.com/leonhad/pdftools/issues/4 | Original issue deleted; Wayback snapshot is the live copy |
| https://github.com/leonhad/pdftools/issues/5 | https://web.archive.org/web/20201018023241/https://github.com/leonhad/pdftools/issues/5 | Original issue deleted; Wayback snapshot is the live copy |
| https://github.com/leonhad/pdftools/issues/6 | https://web.archive.org/web/20201018023239/https://github.com/leonhad/pdftools/issues/6 | Original issue deleted; Wayback snapshot is the live copy |
