# bug-report-kraken-issta-2025

Pipeline that locates and classifies all bug reports filed by the first author of the [KRAKEN paper (ISSTA 2025)](https://github.com/seviezhou/Kraken).

## How it works

Three sources are merged and classified:

| Source | How found |
|--------|-----------|
| `data/generated/bugs_by_author.csv` | Author search across GitHub, FFmpeg Trac, SourceForge, Bugzilla |
| `data/hand_curated.csv` | Manually verified entries no search can reach (Debian, NASM Bugzilla, ncurses ML) |
| CVE references | Bugs linked in CVE JSON that weren't found by author search (orphan CVEs) |

Each bug gets a `where_url_found` label: `paper_artifact` / `activity_history` / `unknown`.

## Commands

```bash
uv sync                       # install deps
python main.py fetch          # download CVE JSON records into cache/
python main.py search-author  # search bug trackers by author → bugs_by_author.csv
python main.py generate       # build output/classified_bugs.csv
```

Requires a `GITHUB_TOKEN` in `.env`.

## Output

| File | Description |
|------|-------------|
| `output/classified_bugs.csv` | Programmatically generated classification |
| `output/classified_bugs_mahadi.csv` | After applying manual overrides from `data/overrides.md` |

## Project structure

```
main.py
src/
  fetch_cve_list.py             Fetch CVE IDs from KRAKEN README
  fetch_cves.py                 Download CVE JSON records to cache/
  extract_refs.py               Extract bug URLs from CVE JSON references
  build_classified_bugs_csv.py  Main pipeline → classified_bugs.csv
  search_by_author.py           Query GitHub / Trac / SourceForge / Bugzilla
  reporter_fetcher.py           Fetch & cache reporter usernames (GitHub, SF)
  github_client.py              Shared GitHub HTTP client
data/
  projects.csv                  37 KRAKEN targets with paper bug/CVE counts
  hand_curated.csv              Manually verified bug entries
  overrides.md                  Manual corrections for classified_bugs_mahadi.csv
  generated/
    bugs_by_author.csv          Output of search-author (gitignored)
cache/                          CVE JSON files + authors.json (gitignored)
output/
  classified_bugs.csv           Programmatic output
  classified_bugs_mahadi.csv    Final output after overrides
```
