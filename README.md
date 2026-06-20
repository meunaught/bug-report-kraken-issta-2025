# bug-report-kraken-issta-2025

Automated pipeline that locates and documents all bug reports filed by the first author of the [KRAKEN paper (ISSTA 2025)](https://github.com/seviezhou/Kraken), producing a LaTeX PDF report.

## How it works

Two independent paths are run and joined on `bug_url`:

| Path | Source | Output |
|------|--------|--------|
| CVE JSON | CVEProject/cvelistV5 GitHub repo | `bug_url → cve_id` map (from `cache/`) |
| Author search | GitHub, FFmpeg Trac, SourceForge, Red Hat Bugzilla | `data/generated/bugs_by_author.csv` |

The join produces `data/generated/joined.csv` (188 rows across 31 KRAKEN projects), which is rendered into LaTeX tables and compiled to `output/bug-report.pdf`.

## Commands

```
python main.py fetch           # Download CVE JSON records into cache/
python main.py search-author   # Search bug trackers by author → bugs_by_author.csv
python main.py generate        # Join CSVs + render tables + compile PDF
python main.py all             # fetch → search-author → generate
```

Add `--refresh` to `fetch` or `all` to re-download cached JSON records.

## First run

```bash
uv sync
python main.py all
```

Requires a `GITHUB_TOKEN` in `.env` to avoid GitHub API rate limits:

```
GITHUB_TOKEN=ghp_...
```

## Output

`output/bug-report.pdf` — a LaTeX document containing:

- **Section 2**: Search process flowchart (CVE path + author path → join)
- **Table 1**: Summary by project (bugs filed, with/without CVE, platform)
- **Table 2**: All 188 bug reports grouped by project with CVE JSON links

## Project structure

```
main.py                     Entry point
src/
  fetch_cve_list.py         Fetch 119 CVE IDs from KRAKEN README
  fetch_cves.py             Download CVE JSON records to cache/
  extract_refs.py           Extract bug URLs from CVE JSON
  build_joined_csv.py       Join cache + bugs_by_author.csv → joined.csv
  search_by_author.py       Query GitHub / Trac / SourceForge / Bugzilla
  render_table.py           Render joined.csv → LaTeX tables
  github_client.py          Shared GitHub HTTP client (reads GITHUB_TOKEN)
data/
  projects.csv              37 KRAKEN target projects with platform info
  generated/
    bugs_by_author.csv      Output of search-author
    joined.csv              Final joined dataset
cache/                      CVE JSON files (gitignored)
templates/                  Jinja2 LaTeX templates
tex/                        LaTeX source (main.tex + generated tables)
output/                     Compiled PDF
```
