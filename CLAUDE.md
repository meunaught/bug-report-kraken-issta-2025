# CLAUDE.md

## Project overview

Python pipeline that documents bug reports filed by the first author of the KRAKEN paper (ISSTA 2025). Produces a LaTeX PDF (`output/bug-report.pdf`).

## Key facts

- **Author identity**: Anshunkang Zhou — `seviezhou` on GitHub/Trac, `azhouad` on SourceForge, real name on Bugzilla
- **KRAKEN targets**: 37 projects listed in `data/projects.csv`
- **Final dataset**: `data/generated/joined.csv` — 188 rows, 31 projects (73 with CVE, 115 without)
- The 115 no-CVE bugs are available by design (live search results); no unavailability tracking needed

## Running the pipeline

```bash
uv sync                        # install deps
python main.py search-author   # populate bugs_by_author.csv (slow: SF fetches ~334 tickets)
python main.py generate        # join + render + compile
```

Requires `GITHUB_TOKEN` in `.env`.

## Compiling the PDF

Always compile from the `tex/` directory:

```bash
cd tex && latexmk -CA && latexmk -pdf -outdir=../output -jobname=bug-report main.tex
```

## Pipeline architecture

```
CVE JSON cache  ──┐
                  ├── build_joined_csv.py ──→ joined.csv ──→ render_table.py ──→ tables
bugs_by_author.csv ──┘
```

`cves.csv` no longer exists — the `bug_url → cve_id` map is built directly from `cache/*.json` via `extract_refs.py`.

## Source files

| File | Purpose |
|------|---------|
| `src/fetch_cve_list.py` | Fetch 119 CVE IDs from KRAKEN README Trophy section |
| `src/fetch_cves.py` | Download CVE JSON records to `cache/` |
| `src/extract_refs.py` | Parse bug URLs out of CVE JSON `references` field |
| `src/build_joined_csv.py` | Join JSON cache + `bugs_by_author.csv` → `joined.csv`; filters to KRAKEN projects only |
| `src/search_by_author.py` | Author-based search: GitHub API, FFmpeg Trac, SourceForge, Bugzilla |
| `src/render_table.py` | Render `joined.csv` → LaTeX tables; reads `projects.csv` for platform info |
| `src/github_client.py` | Shared httpx client with GitHub token + `.env` loader |

## Data files

| File | Notes |
|------|-------|
| `data/projects.csv` | 37 KRAKEN targets — only `project` and `platform` columns are used |
| `data/generated/bugs_by_author.csv` | Output of `search-author`; gitignored |
| `data/generated/joined.csv` | Final joined dataset; gitignored |
| `cache/` | CVE JSON files; gitignored |

## LaTeX notes

- Tables are Jinja2-rendered into `tex/generated/` before compilation
- `_DISPLAY_NAME` values in `render_table.py` are pre-formatted LaTeX — do not pass through `tex_escape()`
- `data/projects.csv` key must match the project name in `joined.csv` exactly (e.g. `pbrt-v3` not `pbrt`)
