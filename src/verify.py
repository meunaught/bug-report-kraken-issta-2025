"""
Verify output/classified_{commit}.csv against data/projects.csv rules.

Rules:
  1. No unknown labels
  2. paper_artifact count == paper bugs per project
  3. Unique CVE count == paper CVEs per project
  4. No duplicate report_url
  5. reporter must be present, a verified author identity, and any tracker related_url must also resolve to a verified author

Exit 0 if all pass. Exit 1 if any fail — run `python main.py review` and
update data/static/patch.yaml to resolve mismatches.

Run via: python main.py verify
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

from client import git_short_commit
from reporter import is_supported

AUTHOR_USERNAMES = {"seviezhou", "azhouad", "zhouan", "Anshunkang Zhou", "Zhou Anshunkang"}

ROOT         = Path(__file__).parent.parent
OUTPUT_DIR   = ROOT / "output"
PROJECTS_CSV = ROOT / "data" / "static" / "projects.csv"


def verify() -> bool:
    commit = git_short_commit()
    human_csv = OUTPUT_DIR / f"classified_{commit}.csv"
    if not human_csv.exists():
        print(f"ERROR: {human_csv} not found — run `python main.py apply` first")
        return False

    rows = list(csv.DictReader(human_csv.open()))
    paper = {r["project"]: {"bugs": int(r["bugs"]), "cves": int(r["cves"])}
             for r in csv.DictReader(PROJECTS_CSV.open())}

    failures: list[str] = []
    failing_projects: set[str] = set()
    url2proj = {r["report_url"]: r["project"] for r in rows}

    # Rule 1: no unknowns
    for r in rows:
        if r["where_url_found"] == "unknown":
            failures.append(f"  unknown label: {r['report_url']}")
            if r["project"]:
                failing_projects.add(r["project"])

    # Rule 4: no duplicate report_url
    seen_urls: dict[str, int] = {}
    for r in rows:
        seen_urls[r["report_url"]] = seen_urls.get(r["report_url"], 0) + 1
    for url, count in seen_urls.items():
        if count > 1:
            failures.append(f"  duplicate url ({count}x): {url}")
            if url2proj.get(url):
                failing_projects.add(url2proj[url])

    # Rule 5: reporter must be present, a verified author identity,
    #          and any tracker related_url must also resolve to a verified author
    reporter_by_url = {r["report_url"]: r.get("reporter", "") for r in rows}
    for r in rows:
        reporter = r.get("reporter", "")
        if not reporter:
            failures.append(f"  empty reporter: {r['report_url']}")
            if r["project"]:
                failing_projects.add(r["project"])
        elif reporter not in AUTHOR_USERNAMES:
            failures.append(f"  unverified reporter ({reporter}): {r['report_url']}")
            if r["project"]:
                failing_projects.add(r["project"])
        related = r.get("related_url", "")
        if related and "web.archive.org" not in related and is_supported(related):
            related_reporter = reporter_by_url.get(related, "")
            if related_reporter not in AUTHOR_USERNAMES:
                failures.append(f"  unverified related_url ({related_reporter or 'unknown'}): {related}")
                if r["project"]:
                    failing_projects.add(r["project"])

    # Rules 2 & 3: per-project counts
    by_project: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r["project"]:
            by_project[r["project"]].append(r)

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
            failing_projects.add(proj)

    # Report
    print(f"Verifying {human_csv.name} ({len(rows)} rows)")
    if not failures:
        print("  All checks passed.")
        return True

    print(f"  {len(failures)} failure(s):")
    for f in failures:
        print(f)

    if failing_projects:
        from context_bundle import generate_context_for
        print()
        print(f"Generating AI context for {len(failing_projects)} failing project(s):")
        generate_context_for(sorted(failing_projects))
        print()
        print("Read cache/review/<project>.md, update data/static/patch.yaml, then re-apply.")

    return False


if __name__ == "__main__":
    sys.exit(0 if verify() else 1)
