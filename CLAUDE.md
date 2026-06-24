# CLAUDE.md

## Project overview

Python pipeline that locates and classifies all bug reports filed by the first author of the KRAKEN paper (ISSTA 2025). Produces two CSVs in `output/`.

## Key facts

- **Author identity**: Anshunkang Zhou — `seviezhou` on GitHub/Trac, `azhouad` on SourceForge, `zhouan` on NASM Bugzilla, real name on Debian/ncurses
- **KRAKEN targets**: 37 projects listed in `data/projects.csv` (also contains paper bug/CVE counts)
- **Output**: `output/classified_auto.csv` (programmatic) → `output/classified_human_{commit}.csv` (after overrides)
- **`where_url_found` values**: `paper_artifact` | `activity_history` | `unknown`

## Running the pipeline

```bash
uv sync                        # install deps
python main.py fetch           # download CVE JSON records into cache/
python main.py search-author   # populate data/generated/author_bugs.csv (slow: SF fetches ~334 tickets)
python main.py generate        # build output/classified_auto.csv
python main.py review          # fetch HTML for projects with count mismatch → cache/html/
python main.py apply           # apply data/overrides.yaml → output/classified_human_{commit}.csv
python main.py verify          # check classified_human_{commit}.csv against projects.csv rules
```

For AI-assisted classification: after `review`, read the HTMLs in `cache/html/` alongside
`output/classified_auto.csv` and `data/projects.csv`, then write suggestions to
`data/ai/suggestions.md`. The `review` step triggers on any project where:
- found bug count or unique CVE count differs from `data/projects.csv`, or
- a CVE ID appears on more than one row (potential duplicate needing `related_url`)

### Promoting suggestions to ai-overrides

After writing `data/ai/suggestions.md`, go through it **one project at a time** and present
each suggested action to the user for manual confirmation. Do not batch-apply — ask per
project, wait for approval, then write confirmed entries to `data/ai/ai-overrides.yaml`.
Never touch `data/overrides.yaml` — that file is human-curated only.

Requires `GITHUB_TOKEN` in `.env`.

## Pipeline architecture

```
CVE JSON cache        ──┐
data/generated/       ──┼── src/classify.py ──→ output/classified_auto.csv
data/curated.csv      ──┘
                                    ↓ src/apply.py (data/overrides.yaml)
                         output/classified_human_{commit}.csv
```

## Classification logic

1. Non-KRAKEN project bugs → `activity_history`
2. Bugs with a CVE → `paper_artifact`
3. Projects where `bugs == cves` in `projects.csv` (all paper bugs have CVEs) → no-CVE found bugs → `activity_history`
4. Remaining KRAKEN bugs without CVE: if project total matches `projects.csv` bug count → `paper_artifact`, else → `unknown`

Orphan CVE bugs (in CVE references but not found by author search) are added automatically and their reporters fetched via API. See `cache/json/authors.json`.

## Known data gaps

`python main.py verify` will always report CVE count mismatches for two projects:

| Project | Expected CVEs | Found CVEs | Notes |
|---|---|---|---|
| gpac | 9 | 8 | 9th CVE absent from KRAKEN README trophy list |
| libredwg | 9 | 8 | 9th CVE absent from KRAKEN README trophy list |

117 of 119 CVEs from the trophy list are fetchable; 2 are missing from the CVEProject/cvelistV5
source and leave `.missing` sentinel files in `cache/json/`. These gaps are in the upstream data,
not the pipeline — the verify failures for gpac and libredwg are expected and can be ignored.

## Source files

| File | Purpose |
|------|---------|
| `src/client.py` | Shared httpx client with GitHub token + `.env` loader; `git_short_commit()` helper |
| `src/cve_list.py` | Fetch 119 CVE IDs from KRAKEN README Trophy section |
| `src/cve_fetch.py` | Download CVE JSON records to `cache/` |
| `src/cve_refs.py` | Parse bug URLs out of CVE JSON `references` field |
| `src/classify.py` | Main pipeline: joins all sources → `classified_auto.csv` |
| `src/search.py` | Author-based search: GitHub API, FFmpeg Trac, SourceForge, Bugzilla |
| `src/reporter.py` | Fetch reporter username for GitHub/SF URLs; cache in `cache/authors.json` |
| `src/fetch_html.py` | Fetch HTML for projects with bug/CVE count mismatch → `cache/html/` for AI reasoning |
| `src/apply.py` | Apply `data/overrides.yaml` → `classified_human_{commit}.csv` |
| `src/verify.py` | Verify `classified_human_{commit}.csv` against `data/projects.csv` rules; exits 1 if AI review needed |

## Data files

| File | Notes |
|------|-------|
| `data/projects.csv` | 37 KRAKEN targets with paper `bugs` and `cves` counts |
| `data/curated.csv` | `project, bug_url, author` — entries no automated search can reach (Debian, NASM Bugzilla, ncurses ML) |
| `data/overrides.yaml` | Machine-applied corrections: list of `{action, report_url, value?, reason}`; actions: `exclude`, `set_label`, `set_cve_id`, `set_reporter`, `set_related_url` |
| `data/ai/suggestions.md` | AI-suggested overrides; written by Claude Code after reading `cache/html/` |
| `data/ai/ai-overrides.yaml` | User-confirmed AI overrides; same format as `overrides.yaml`; written by Claude Code after per-project user approval of `suggestions.md` |
| `data/generated/author_bugs.csv` | Output of `search-author`; gitignored |
| `cache/` | CVE JSON files + `authors.json` reporter cache + `html/` HTML pages; gitignored |
