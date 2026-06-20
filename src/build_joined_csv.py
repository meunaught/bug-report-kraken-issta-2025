import csv
from pathlib import Path

from extract_refs import extract_refs

DATA_DIR     = Path(__file__).parent.parent / "data" / "generated"
PROJECTS_CSV = Path(__file__).parent.parent / "data" / "projects.csv"
AUTHOR_CSV   = DATA_DIR / "bugs_by_author.csv"
JOINED_CSV   = DATA_DIR / "joined.csv"
FIELDS       = ["project", "bug_url", "label", "author", "cve_id"]


# GitHub repos that moved to a new owner/org after the CVE records were written.
_REPO_REDIRECTS: dict[str, str] = {
    "github.com/matthiaskramm/swftools/": "github.com/swftools/swftools/",
    "github.com/hfp/libxsmm/":           "github.com/libxsmm/libxsmm/",
}


def _normalize(url: str) -> str:
    url = url.split("#")[0].rstrip("/")
    for old, new in _REPO_REDIRECTS.items():
        if old in url:
            url = url.replace(old, new)
    return url


def build_joined_csv(cve_ids: list[str]) -> None:
    # Build url → cve_id map directly from JSON cache
    cve_map: dict[str, str] = {}
    for cve_id in cve_ids:
        for ref in extract_refs(cve_id):
            cve_map[_normalize(ref.url)] = cve_id

    if not AUTHOR_CSV.exists():
        raise FileNotFoundError(
            f"{AUTHOR_CSV} not found — run: python main.py search-author"
        )

    kraken_projects = {r["project"] for r in csv.DictReader(PROJECTS_CSV.open())}

    rows: list[dict] = []
    with AUTHOR_CSV.open() as f:
        for r in csv.DictReader(f):
            if r["project"] not in kraken_projects:
                continue
            rows.append({
                "project": r["project"],
                "bug_url": r["bug_url"],
                "label":   r["label"],
                "author":  r["author"],
                "cve_id":  cve_map.get(_normalize(r["bug_url"]), ""),
            })

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with JOINED_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    matched = sum(1 for r in rows if r["cve_id"])
    print(f"Written {len(rows)} rows → {JOINED_CSV}  "
          f"(with CVE: {matched}, no CVE: {len(rows) - matched})")
