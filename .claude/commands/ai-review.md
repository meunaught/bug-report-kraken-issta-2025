# AI-overrides workflow

Write entries to `data/static/patch.yaml` to resolve mismatches found by `python main.py verify`.

## Setup

1. Run `python main.py verify`. For every failing project it writes a raw evidence file
   `cache/review/<project>.md` (report bodies, full sanitizer traces, cached page text).
2. For each failing project, read:
   - `cache/review/<project>.md` — raw evidence
   - `data/static/projects.csv` — expected bug/CVE counts for that project
   - `data/static/curated.csv` — manually verified entries (Debian, NASM, ncurses, deleted issues)

## Process

- Work through failing projects **one at a time** — do not proceed to the next until the user confirms
- Before starting each project, **wait for the user** — they may switch AI model between projects
- Present proposed entries for each project and wait for user approval before writing
- Write confirmed entries directly to `data/static/patch.yaml` — no intermediate files
- After all projects are resolved, run `python main.py apply && python main.py verify`
  (verify re-writes context only for projects that still fail)

## Entry format

```yaml
- action: <action>
  report_url: <exact URL from classified_auto.csv>
  value: <new value>        # omit for exclude
  reason: <justification>  # for exclude: key technical justification
```

## Actions

| Action | Effect in classified_{commit}.csv |
| --- | --- |
| `exclude` | Removes the row entirely |
| `set_label` | Sets `where_url_found` to `value` (`paper_artifact` or `activity_history`) |
| `set_cve_id` | Sets `cve_id` to `value` |
| `set_reporter` | Sets `reporter` to `value` |
| `set_archived_url` | Sets `related_url` to `value` (Wayback URL); sets `notes` to `"Archived copy (original deleted)"` |
| `set_cve_ref` | Sets `notes` to `"[CVE-REFERENCE] <value>"`; `related_url` stays empty |

## Known expected failures

gpac and libredwg will always fail CVE count (8/9) — 2 reserved CVEs not yet published in CVEProject/cvelistV5. Ignore these.

## Author-verification rule

Every `report_url` and tracker `related_url` in the output must be filed by the verified author
(`seviezhou`, `azhouad`, `zhouan`, `Anshunkang Zhou`).

When a CVE names a different reporter for the same bug as the author's report:

1. `exclude` the non-author row
2. `set_cve_ref` on the author's canonical row to record the CVE URL
3. `set_cve_id` on the canonical row to transfer the CVE ID
4. `set_label` on the canonical row if the label needs correcting
