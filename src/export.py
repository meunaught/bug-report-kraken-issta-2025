"""
Export output/classified_{commit}.csv to starter_kraken.csv format.

Writes output/kraken_{commit}.csv with the same column layout as
data/static/starter_kraken.csv. Empty columns (is_paper_relevant?,
is_author?, etc.) are left blank for manual fill-in.
"""

import csv
from pathlib import Path

from client import git_short_commit

ROOT       = Path(__file__).parent.parent
OUTPUT_DIR = ROOT / "output"

REPORTER_MAP = {
    "seviezhou":       "https://github.com/seviezhou",
    "azhouad":         "https://sourceforge.net/u/azhouad/profile/",
    "zhouan":          "zhouan",
    "Anshunkang Zhou": "Anshunkang Zhou",
    "Zhou Anshunkang": "Zhou Anshunkang",
}

FIELDS = [
    "overleaf_id", "report_url", "where_url_found", "is_paper_relevant?",
    "related_url", "date", "reporter", "is_author?", "#_bugs_in_report",
    "source_of_#_bugs", "authors_claim", "resolution_2025-04-24",
    "resolution_2026-04-24", "notes",
]


def export_kraken_csv() -> Path:
    commit = git_short_commit()
    src = OUTPUT_DIR / f"classified_{commit}.csv"
    if not src.exists():
        print(f"ERROR: {src} not found — run `python main.py apply` first")
        return src

    rows = list(csv.DictReader(src.open()))
    out_rows = []

    for r in rows:
        # pdftools issues were deleted; Wayback URL is the canonical report URL
        pdftools = r["project"] == "pdftools"
        report_url  = r["related_url"] if pdftools else r["report_url"]
        related_url = ""               if pdftools else r["related_url"]

        if pdftools:
            notes = r["cve_id"]
        elif r["notes"].startswith("[CVE-REFERENCE] "):
            ref_url = r["notes"][len("[CVE-REFERENCE] "):]
            notes = f"{r['cve_id']} has {ref_url}" if r["cve_id"] else ref_url
        else:
            notes = r["cve_id"]

        out_rows.append({
            "overleaf_id":           "KRAKEN",
            "report_url":            report_url,
            "where_url_found":       r["where_url_found"],
            "is_paper_relevant?":    "",
            "related_url":           related_url,
            "date":                  r["date"],
            "reporter":              REPORTER_MAP.get(r["reporter"], r["reporter"]),
            "is_author?":            "",
            "#_bugs_in_report":      "",
            "source_of_#_bugs":      "",
            "authors_claim":         "",
            "resolution_2025-04-24": "",
            "resolution_2026-04-24": "",
            "notes":                 notes,
        })

    out = OUTPUT_DIR / f"kraken_{commit}.csv"
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"Written {len(out_rows)} rows → {out}")
    return out
