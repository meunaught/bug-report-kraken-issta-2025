"""
Fetch HTML pages for projects where found bug/CVE counts don't match data/projects.csv.

Fetches ALL rows for those projects so the full picture is available — unknowns,
paper_artifact peers, and Bugzilla CVE entries alike.

Run via: python main.py review

After fetching, Claude Code reads cache/html/ alongside output/classified_auto.csv
and data/projects.csv, reasons about classifications, and writes data/ai/suggestions.md.
"""

import csv
import re
from collections import defaultdict
from pathlib import Path

import httpx

ROOT           = Path(__file__).parent.parent
CLASSIFIED_CSV = ROOT / "output" / "classified_auto.csv"
PROJECTS_CSV   = ROOT / "data" / "projects.csv"
HTML_CACHE     = ROOT / "cache" / "html"


def _slug(url: str) -> str:
    url = re.sub(r"^https?://", "", url)
    return re.sub(r"[^a-zA-Z0-9._-]", "_", url) + ".html"


def fetch_for_review() -> None:
    HTML_CACHE.mkdir(parents=True, exist_ok=True)

    rows = list(csv.DictReader(CLASSIFIED_CSV.open()))
    paper = {r["project"]: {"bugs": int(r["bugs"]), "cves": int(r["cves"])}
             for r in csv.DictReader(PROJECTS_CSV.open())}

    # Group by project
    by_project: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row["project"]:
            by_project[row["project"]].append(row)

    # Trigger: found bug count or CVE count doesn't match projects.csv
    projects_to_review = set()
    for proj, proj_rows in by_project.items():
        if proj not in paper:
            continue
        found_bugs = sum(1 for r in proj_rows if r["where_url_found"] == "paper_artifact")
        found_cves = len({r["cve_id"] for r in proj_rows if r.get("cve_id")})
        if found_bugs != paper[proj]["bugs"] or found_cves != paper[proj]["cves"]:
            projects_to_review.add(proj)

    if not projects_to_review:
        print("All project counts match projects.csv — nothing to review.")
        return

    to_fetch = [r for r in rows if r["project"] in projects_to_review]

    print(f"Projects with count mismatch: {sorted(projects_to_review)}")
    print(f"Fetching HTML for {len(to_fetch)} rows → cache/html/")

    for row in to_fetch:
        url = row["report_url"]
        path = HTML_CACHE / _slug(url)
        if path.exists():
            print(f"  cached  [{row['where_url_found']}] {url}")
            continue
        print(f"  fetch   [{row['where_url_found']}] {url}")
        try:
            r = httpx.get(url, follow_redirects=True, timeout=15)
            r.raise_for_status()
            path.write_text(r.text, encoding="utf-8")
        except Exception as e:
            print(f"  ERROR   {e}")
