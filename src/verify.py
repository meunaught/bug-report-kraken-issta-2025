"""
Verify output/classified_human_{commit}.csv against data/projects.csv rules.

Rules:
  1. No unknown labels
  2. paper_artifact count == paper bugs per project
  3. Unique CVE count == paper CVEs per project
  4. No duplicate report_url
  5. No empty reporter field

Exit 0 if all pass. Exit 1 if any fail — run `python main.py review` and
update data/ai/suggestions.md to resolve mismatches.

Run via: python main.py verify
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

from client import git_short_commit

ROOT         = Path(__file__).parent.parent
OUTPUT_DIR   = ROOT / "output"
PROJECTS_CSV = ROOT / "data" / "projects.csv"


def verify() -> bool:
    commit = git_short_commit()
    human_csv = OUTPUT_DIR / f"classified_human_{commit}.csv"
    if not human_csv.exists():
        print(f"ERROR: {human_csv} not found — run `python main.py apply` first")
        return False

    rows = list(csv.DictReader(human_csv.open()))
    paper = {r["project"]: {"bugs": int(r["bugs"]), "cves": int(r["cves"])}
             for r in csv.DictReader(PROJECTS_CSV.open())}

    failures: list[str] = []

    # Rule 1: no unknowns
    unknowns = [r["report_url"] for r in rows if r["where_url_found"] == "unknown"]
    if unknowns:
        for url in unknowns:
            failures.append(f"  unknown label: {url}")

    # Rule 4: no duplicate report_url
    seen_urls: dict[str, int] = {}
    for r in rows:
        seen_urls[r["report_url"]] = seen_urls.get(r["report_url"], 0) + 1
    for url, count in seen_urls.items():
        if count > 1:
            failures.append(f"  duplicate url ({count}x): {url}")

    # Rule 5: no empty reporter
    missing_reporter = [r["report_url"] for r in rows if not r.get("reporter")]
    for url in missing_reporter:
        failures.append(f"  empty reporter: {url}")

    # Rules 2 & 3: per-project counts
    by_project: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r["project"]:
            by_project[r["project"]].append(r)

    review_needed: list[str] = []
    for proj, proj_rows in sorted(by_project.items()):
        if proj not in paper:
            continue
        expected_bugs = paper[proj]["bugs"]
        expected_cves = paper[proj]["cves"]
        found_bugs = sum(1 for r in proj_rows if r["where_url_found"] == "paper_artifact")
        found_cves = len({r["cve_id"] for r in proj_rows if r.get("cve_id")})

        bug_ok = found_bugs == expected_bugs
        cve_ok = found_cves == expected_cves

        if not bug_ok or not cve_ok:
            parts = []
            if not bug_ok:
                parts.append(f"bugs {found_bugs}/{expected_bugs}")
            if not cve_ok:
                parts.append(f"CVEs {found_cves}/{expected_cves}")
            failures.append(f"  {proj}: {', '.join(parts)}")
            review_needed.append(proj)

    # Report
    print(f"Verifying {human_csv.name} ({len(rows)} rows)")
    if not failures:
        print("  All checks passed.")
        return True

    print(f"  {len(failures)} failure(s):")
    for f in failures:
        print(f)

    if review_needed:
        print()
        print("AI-assisted review needed for:")
        for proj in review_needed:
            print(f"  {proj}")
        print()
        print("Run: python main.py review")
        print("Then update data/ai/suggestions.md and data/overrides.yaml, then re-apply.")

    return False


if __name__ == "__main__":
    sys.exit(0 if verify() else 1)
