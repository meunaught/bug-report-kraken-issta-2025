# CLAUDE.md

## Project overview

Python pipeline that locates and classifies all bug reports filed by the first author of the KRAKEN paper (ISSTA 2025). Produces `output/classified_{commit}.csv`.

## Key facts

- **Author identity**: Anshunkang Zhou — `seviezhou` on GitHub/Trac, `azhouad` on SourceForge, `zhouan` on NASM Bugzilla, real name on Debian/ncurses
- **KRAKEN targets**: 37 projects listed in `data/static/projects.csv` (also contains paper bug/CVE counts)
- **Output**: `output/classified_{commit}.csv` (programmatic base, then overrides applied in-place)
- **Date cutoff**: bugs with `date > 2025-04-24` are excluded from output
- **Output CSV columns**: `project`, `report_url`, `related_url`, `where_url_found`, `date`, `reporter`, `cve_id`, `notes`
- **`where_url_found` values**: `paper_artifact` | `activity_history` | `unknown`
- **`notes` values**: `"Archived copy (original deleted)"` (when `related_url` is a Wayback Archive URL) | `"[CVE-REFERENCE] <url>"` (non-author CVE reference URL)

## Setup

- Install [uv](https://docs.astral.sh/uv/) — used for dependency management (`uv sync`)
- Add `GITHUB_TOKEN=<token>` to `.env` — required for `search-author` and `match-prs`

## Running the pipeline

```bash
uv sync                        # install deps
python main.py fetch           # download CVE JSON records into cache/
python main.py search-author   # populate data/generated/author_bugs.csv (slow: SF fetches ~334 tickets)
python main.py generate        # build output/classified_{commit}.csv (programmatic)
python main.py match-prs       # fetch PR HTML, extract linked issues → data/generated/pr-matches.yaml
python main.py apply           # apply pr-matches + overrides in-place to classified_{commit}.csv
python main.py verify          # check classified_{commit}.csv; on failure → cache/review/<project>.md
```

For AI-assisted classification: run `/ai-review` (reads `cache/review/<project>.md` written by `verify`, drafts entries for `data/static/patch.yaml`).

## Pipeline architecture

```text
CVE JSON cache                    ──┐
data/generated/author_bugs.csv    ──┼── src/classify.py ──→ output/classified_{commit}.csv
data/static/curated.csv           ──┘                               ↓
                              src/apply.py (in-place) — pass 1: PR matching (pr-matches.yaml)
                                                       — pass 2: labelling  (patch.yaml)
                         output/classified_{commit}.csv  (same file, overrides applied)
```

## Verify rules

`python main.py verify` checks `classified_{commit}.csv` against these rules:

1. No `unknown` labels
2. `paper_artifact` count per project == `bugs` in `data/static/projects.csv`
3. Unique `cve_id` count per project == `cves` in `data/static/projects.csv`
4. No duplicate `report_url`
5. `reporter` must be present and a verified author identity (`seviezhou`, `azhouad`, `zhouan`, `Anshunkang Zhou`); any tracker `related_url` must also resolve to a verified author

Failures trigger `cache/review/<project>.md` generation. Run `/ai-review` to resolve.

## Source files

| File | Purpose |
| --- | --- |
| `src/client.py` | Shared httpx client, GitHub token + `.env` loader, `git_short_commit()`, all cache path constants (`ISSUE_JSON`, `PR_JSON`, `CVE_JSON`, `HTML_ISSUE`, `HTML_PR`, `TRAC_CACHE`), and `url_slug()` |
| `src/cve_list.py` | Fetch 119 CVE IDs from KRAKEN README Trophy section |
| `src/cve_fetch.py` | Download CVE JSON records to `cache/json/cve/` |
| `src/cve_refs.py` | Parse bug URLs out of CVE JSON `references` field |
| `src/classify.py` | Main pipeline: joins all sources → `classified_{commit}.csv`; applies date cutoff |
| `src/search.py` | Author-based search: GitHub API (issues + PRs), FFmpeg Trac, SourceForge, Bugzilla |
| `src/pr_match.py` | Fetch PR HTML, extract linked issue URLs → `data/generated/pr-matches.yaml` |
| `src/reporter.py` | Fetch reporter username for GitHub/SF URLs from per-item JSON cache |
| `src/apply.py` | Two-pass apply: (1) PR matching via `pr-matches.yaml`, (2) labelling via `patch.yaml` |
| `src/verify.py` | Verify `classified_{commit}.csv` against `data/static/projects.csv` rules; exits 1 if review needed, and writes `cache/review/<project>.md` for each failing project |
| `src/context_bundle.py` | Build raw per-project evidence files (`cache/review/<project>.md`) for failing projects; fetches issue HTML on demand, no analysis applied. Driven by `verify` |

## Data files

| File | Notes |
| --- | --- |
| `data/static/projects.csv` | 37 KRAKEN targets with paper `bugs` and `cves` counts |
| `data/static/curated.csv` | Manually verified entries no automated search can reach (Debian BTS, NASM Bugzilla, ncurses ML, deleted GitHub issues); schema matches `classified_{commit}.csv` |
| `data/static/patch.yaml` | All overrides: AI-assisted, human-confirmed; list of `{action, report_url, value?, reason}` |
| `data/generated/author_bugs.csv` | Output of `search-author` (issues + PRs); gitignored |
| `data/generated/pr-matches.yaml` | Output of `match-prs`; maps each PR URL to its linked issue URL (or null); gitignored |
| `cache/json/cve/` | CVE JSON records; gitignored |
| `cache/json/issues/` | Per-item GitHub issue JSON + SourceForge ticket JSON; populated by `search-author` and reporter fetches; gitignored |
| `cache/json/prs/` | Per-item GitHub PR JSON; populated by `search-author`; gitignored |
| `cache/json/trac_ffmpeg.tsv` | FFmpeg Trac query result (reporter + date); gitignored |
| `cache/html/issue/` | Issue HTML pages fetched on demand by `verify`/`context_bundle`; gitignored |
| `cache/review/` | Raw per-project evidence files written by `verify` for failing projects; gitignored |
| `cache/html/pr/` | PR HTML pages fetched by `match-prs`; gitignored |
