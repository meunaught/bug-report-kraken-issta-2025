import csv
from pathlib import Path

from extract_project import extract_project
from extract_refs import extract_refs

DATA_DIR = Path(__file__).parent.parent / "data" / "generated"
CVES_CSV = DATA_DIR / "cves.csv"

FIELDS = ["cve_id", "project", "bug_url", "label"]


def build_cves_csv(cve_ids: list[str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []

    for cve_id in cve_ids:
        project = extract_project(cve_id)
        refs = extract_refs(cve_id)

        if refs:
            for ref in refs:
                rows.append({"cve_id": cve_id, "project": project,
                             "bug_url": ref.url, "label": ref.label})
        else:
            rows.append({"cve_id": cve_id, "project": project,
                         "bug_url": "", "label": ""})

    with CVES_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Written {len(rows)} rows → {CVES_CSV}")
