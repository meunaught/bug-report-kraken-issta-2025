# CLAUDE.md

## Project overview

Python pipeline that locates and classifies all bug reports filed by the first author of the KRAKEN paper (ISSTA 2025). Produces two CSVs in `output/`.

## Key facts

- **Author identity**: Anshunkang Zhou — `seviezhou` on GitHub/Trac, `azhouad` on SourceForge, `zhouan` on NASM Bugzilla, real name on Debian/ncurses
- **KRAKEN targets**: 37 projects listed in `data/projects.csv` (also contains paper bug/CVE counts)
- **Output**: `output/classified_auto.csv` (programmatic) → `output/classified_human_{commit}.csv` (after overrides)
- **Date cutoff**: bugs with `date > 2025-04-24` are excluded from output
- **`where_url_found` values**: `paper_artifact` | `activity_history` | `unknown`
- **`notes` values**: `"Archived copy (original deleted)"` (when `related_url` is a Wayback Archive URL) | `"[CVE-REFERENCE] <url>"` (non-author CVE reference URL)

## Running the pipeline

```bash
uv sync                        # install deps
python main.py fetch           # download CVE JSON records into cache/
python main.py search-author   # populate data/generated/author_bugs.csv (slow: SF fetches ~334 tickets)
python main.py generate        # build output/classified_auto.csv
python main.py match-prs       # fetch PR HTML, extract linked issues → data/generated/pr-matches.yaml
python main.py review          # fetch HTML for projects with count mismatch → cache/html/
python main.py apply           # apply pr-matches + overrides → output/classified_human_{commit}.csv
python main.py verify          # check classified_human_{commit}.csv against projects.csv rules
```

For AI-assisted classification: after `review`, read the HTMLs in `cache/html/` alongside
`output/classified_auto.csv` and `data/projects.csv`. The `review` step triggers on any project where:

- found bug count or unique CVE count differs from `data/projects.csv`, or
- a CVE ID appears on more than one row (potential duplicate needing `related_url`)

### AI-overrides workflow

Run `/ai-overrides` for the full step-by-step process. Requires `GITHUB_TOKEN` in `.env`.

## Pipeline architecture

```text
CVE JSON cache        ──┐
data/generated/       ──┼── src/classify.py ──→ output/classified_auto.csv
data/curated.csv      ──┘
                              ↓ src/apply.py — pass 1: PR matching (data/generated/pr-matches.yaml)
                                              — pass 2: labelling  (data/overrides.yaml, data/ai/ai-overrides.yaml)
                         output/classified_human_{commit}.csv
```

## Classification logic

1. Non-KRAKEN project bugs → `activity_history`
2. Bugs with a CVE → `paper_artifact`
3. Projects where `bugs == cves` in `projects.csv` (all paper bugs have CVEs) → no-CVE found bugs → `activity_history`
4. Remaining KRAKEN bugs without CVE: if project total matches `projects.csv` bug count → `paper_artifact`, else → `unknown`

Orphan CVE bugs (in CVE references but not found by author search) are added automatically; their reporters are fetched from GitHub/SF API and cached in `cache/json/issues/` or `cache/json/prs/`.

## Known data gaps

`python main.py verify` will always report CVE count mismatches for two projects:

| Project | Expected CVEs | Found CVEs |
| --- | --- | --- |
| gpac | 9 | 8 |
| libredwg | 9 | 8 |

117 of 119 CVEs from the trophy list are fetchable; 2 are reserved CVEs (exist but not yet
published) in CVEProject/cvelistV5 and leave `.missing` sentinel files in `cache/json/cve/`. These
gaps are in the upstream data, not the pipeline — the verify failures for gpac and libredwg are
expected and can be ignored.

## Source files

| File | Purpose |
| --- | --- |
| `src/client.py` | Shared httpx client, GitHub token + `.env` loader, `git_short_commit()`, all cache path constants (`ISSUE_JSON`, `PR_JSON`, `CVE_JSON`, `HTML_ISSUE`, `HTML_PR`, `TRAC_CACHE`), and `url_slug()` |
| `src/cve_list.py` | Fetch 119 CVE IDs from KRAKEN README Trophy section |
| `src/cve_fetch.py` | Download CVE JSON records to `cache/json/cve/` |
| `src/cve_refs.py` | Parse bug URLs out of CVE JSON `references` field |
| `src/classify.py` | Main pipeline: joins all sources → `classified_auto.csv`; applies date cutoff |
| `src/search.py` | Author-based search: GitHub API (issues + PRs), FFmpeg Trac, SourceForge, Bugzilla |
| `src/pr_match.py` | Fetch PR HTML, extract linked issue URLs → `data/generated/pr-matches.yaml` |
| `src/reporter.py` | Fetch reporter username for GitHub/SF URLs from per-item JSON cache |
| `src/fetch_html.py` | Fetch HTML for projects with bug/CVE count mismatch → `cache/html/issue/` for AI reasoning |
| `src/apply.py` | Two-pass apply: (1) PR matching via `pr-matches.yaml`, (2) labelling via override YAMLs |
| `src/verify.py` | Verify `classified_human_{commit}.csv` against `data/projects.csv` rules; exits 1 if AI review needed |

## Data files

| File | Notes |
| --- | --- |
| `data/projects.csv` | 37 KRAKEN targets with paper `bugs` and `cves` counts |
| `data/curated.csv` | Manually verified entries no automated search can reach (Debian BTS, NASM Bugzilla, ncurses ML, deleted GitHub issues); schema matches `classified_auto.csv` |
| `data/overrides.yaml` | Human-verified corrections: list of `{action, report_url, value?, reason}`; actions: `exclude`, `set_label`, `set_cve_id`, `set_cve_ref` |
| `data/ai/ai-overrides.yaml` | Human-verified AI-assisted overrides; same format as `overrides.yaml`; drafted by Claude Code, confirmed by user before applying |
| `data/generated/author_bugs.csv` | Output of `search-author` (issues + PRs); gitignored |
| `data/generated/pr-matches.yaml` | Output of `match-prs`; maps each PR URL to its linked issue URL (or null); gitignored |
| `cache/json/cve/` | CVE JSON records; gitignored |
| `cache/json/issues/` | Per-item GitHub issue JSON + SourceForge ticket JSON; populated by `search-author` and reporter fetches; gitignored |
| `cache/json/prs/` | Per-item GitHub PR JSON; populated by `search-author`; gitignored |
| `cache/json/trac_ffmpeg.tsv` | FFmpeg Trac query result (reporter + date); gitignored |
| `cache/html/issue/` | Issue HTML pages fetched by `review` step; gitignored |
| `cache/html/pr/` | PR HTML pages fetched by `match-prs`; gitignored |
