# CLAUDE.md

## Project overview

Python pipeline that locates and classifies all bug reports filed by the first author of the KRAKEN paper (ISSTA 2025). Produces two CSVs in `output/`.

## Key facts

- **Author identity**: Anshunkang Zhou — `seviezhou` on GitHub/Trac, `azhouad` on SourceForge, `zhouan` on NASM Bugzilla, real name on Debian/ncurses
- **KRAKEN targets**: 37 projects listed in `data/projects.csv` (also contains paper bug/CVE counts)
- **Output**: `output/classified_bugs.csv` (programmatic) → `output/classified_bugs_mahadi.csv` (after manual overrides)
- **`where_url_found` values**: `paper_artifact` | `activity_history` | `unknown`

## Running the pipeline

```bash
uv sync                        # install deps
python main.py search-author   # populate bugs_by_author.csv (slow: SF fetches ~334 tickets)
python main.py generate        # build output/classified_bugs.csv
```

Then apply `data/overrides.md` manually to produce `output/classified_bugs_mahadi.csv`.

Requires `GITHUB_TOKEN` in `.env`.

## Pipeline architecture

```
CVE JSON cache      ──┐
bugs_by_author.csv  ──┼── build_classified_bugs_csv.py ──→ output/classified_bugs.csv
data/hand_curated.csv ┘
                                        ↓ apply data/overrides.md manually
                              output/classified_bugs_mahadi.csv
```

## Classification logic

1. Non-KRAKEN project bugs → `activity_history`
2. Bugs with a CVE → `paper_artifact`
3. Projects where `bugs == cves` in `projects.csv` (all paper bugs have CVEs) → no-CVE found bugs → `activity_history`
4. Remaining KRAKEN bugs without CVE: if project total matches `projects.csv` bug count → `paper_artifact`, else → `unknown`

Orphan CVE bugs (in CVE references but not found by author search) are added automatically and their reporters fetched via API. See `cache/authors.json`.

## Source files

| File | Purpose |
|------|---------|
| `src/fetch_cve_list.py` | Fetch 119 CVE IDs from KRAKEN README Trophy section |
| `src/fetch_cves.py` | Download CVE JSON records to `cache/` |
| `src/extract_refs.py` | Parse bug URLs out of CVE JSON `references` field |
| `src/build_classified_bugs_csv.py` | Main pipeline: joins all sources → `classified_bugs.csv` |
| `src/search_by_author.py` | Author-based search: GitHub API, FFmpeg Trac, SourceForge, Bugzilla |
| `src/reporter_fetcher.py` | Fetch reporter username for GitHub/SF URLs; cache in `cache/authors.json` |
| `src/github_client.py` | Shared httpx client with GitHub token + `.env` loader |

## Data files

| File | Notes |
|------|-------|
| `data/projects.csv` | 37 KRAKEN targets with paper `bugs` and `cves` counts |
| `data/hand_curated.csv` | `project, bug_url, author` — entries no automated search can reach (Debian, NASM Bugzilla, ncurses ML) |
| `data/overrides.md` | Manual corrections applied post-generation to produce `classified_bugs_mahadi.csv` |
| `data/generated/bugs_by_author.csv` | Output of `search-author`; gitignored |
| `cache/` | CVE JSON files + `authors.json` reporter cache; gitignored |
