"""
Build output/classified_auto.csv.

Sources (in merge order, later wins on conflict):
  1. data/generated/author_bugs.csv  — all author-searched bugs (KRAKEN + non-KRAKEN)
  2. data/curated.csv                — manually verified entries no search can reach

Classification (where_url_found):
  paper_artifact   — certain this bug was found by the KRAKEN paper
  activity_history — certain it is NOT a paper bug
  unknown          — cannot determine from available data

Rules:
  - Non-KRAKEN project bugs → activity_history
  - Bugs with a CVE → paper_artifact
  - KRAKEN bugs without CVE: if project total matches projects.csv count → paper_artifact,
    else → unknown

Manual overrides are applied separately — see data/overrides.md.
"""

import csv
import re
from collections import defaultdict
from pathlib import Path

DATA_DIR     = Path(__file__).parent.parent / "data"
OUTPUT_DIR   = Path(__file__).parent.parent / "output"
AUTHOR_CSV   = DATA_DIR / "generated" / "author_bugs.csv"
HAND_CURATED = DATA_DIR / "static" / "curated.csv"
PROJECTS_CSV = DATA_DIR / "static" / "projects.csv"

FIELDS = ["project", "report_url", "related_url", "where_url_found", "date", "reporter", "cve_id", "notes"]

# ── URL canonicalisation ───────────────────────────────────────────────────────

_REPO_REDIRECTS = {
    "github.com/matthiaskramm/swftools/": "github.com/swftools/swftools/",
    "github.com/hfp/libxsmm/":           "github.com/libxsmm/libxsmm/",
}


def _canonicalize(url: str) -> str:
    if re.search(r"sourceforge\.net/p/[^/]+/(?:bugs|tickets)/\d+$", url):
        url = url + "/"
    return url


def _normalize(url: str) -> str:
    url = url.split("#")[0].rstrip("/")
    for old, new in _REPO_REDIRECTS.items():
        if old in url:
            url = url.replace(old, new)
    return url




# ── Pipeline ──────────────────────────────────────────────────────────────────

def _load_cve_map() -> tuple[dict[str, str], dict[str, str]]:
    from cve_refs import extract_refs
    from cve_list import fetch_cve_list
    cve_map: dict[str, str] = {}
    fragment_urls: dict[str, str] = {}  # norm_key → original URL with fragment
    for cve_id in fetch_cve_list():
        for url in extract_refs(cve_id):
            norm = _normalize(url)
            cve_map[norm] = cve_id
            if "#" in url:
                fragment_urls[norm] = url
    return cve_map, fragment_urls


def _merge(existing: dict, incoming: dict) -> dict:
    out = dict(existing)
    for field in ("project", "reporter", "author", "cve_id", "date", "related_url", "where_url_found", "notes"):
        if not out.get(field) and incoming.get(field):
            out[field] = incoming[field]
    return out


def _infer_project(url: str, kraken_projects: set[str]) -> str:
    """Infer KRAKEN project name from a bug URL."""
    # GitHub: github.com/owner/{repo}/
    m = re.search(r"github\.com/[^/]+/([^/]+?)(?:/|$)", url)
    if m:
        name = m.group(1).lower().split("#")[0]
        if name in kraken_projects:
            return name

    # SourceForge: sourceforge.net/p/{project}/
    m = re.search(r"sourceforge\.net/p/([^/]+)/", url)
    if m and m.group(1) in kraken_projects:
        return m.group(1)

    # GNU mailing lists: lists.gnu.org/archive/html/bug-{project}/
    m = re.search(r"lists\.gnu\.org/archive/html/bug-([^/]+)/", url)
    if m and m.group(1) in kraken_projects:
        return m.group(1)

    # FFmpeg Trac
    if "trac.ffmpeg.org" in url and "ffmpeg" in kraken_projects:
        return "ffmpeg"

    # NASM Bugzilla
    if "bugzilla.nasm.us" in url and "nasm" in kraken_projects:
        return "nasm"

    return ""


def _load_bugs(cve_map: dict[str, str], fragment_urls: dict[str, str], kraken_projects: set[str]) -> list[dict]:
    seen: dict[str, dict] = {}

    def _add(rec: dict) -> None:
        # support both old (bug_url/author) and new (report_url/reporter) column names
        url = _canonicalize(rec.get("report_url") or rec.get("bug_url", ""))
        rec = dict(rec)
        rec["bug_url"] = url
        if not rec.get("reporter") and rec.get("author"):
            rec["reporter"] = rec["author"]
        if not rec.get("cve_id"):
            rec["cve_id"] = cve_map.get(_normalize(url), "")
        key = _normalize(url)
        seen[key] = _merge(seen[key], rec) if key in seen else rec

    for r in csv.DictReader(AUTHOR_CSV.open()):
        _add(r)
    for r in csv.DictReader(HAND_CURATED.open()):
        _add(r)

    # Add CVE-referenced KRAKEN URLs not found by author search (orphan CVEs)
    known_keys = set(seen.keys())
    for url, cve_id in cve_map.items():
        if url in known_keys:
            continue
        # Reconstruct original URL (cve_map keys are normalized)
        proj = _infer_project(url, kraken_projects)
        if not proj:
            continue
        seen[url] = {
            "project": proj,
            "bug_url": url,
            "label":   "",
            "author":  "",
            "cve_id":  cve_id,
        }

    # Prefer the CVE's original URL when it has a fragment (e.g. #issuecomment-…)
    for key, frag_url in fragment_urls.items():
        if key in seen and "#" not in seen[key].get("bug_url", ""):
            seen[key] = dict(seen[key])
            seen[key]["bug_url"] = frag_url

    return list(seen.values())


def classify(bugs: list[dict], kraken_projects: set[str], supplement: dict) -> list[dict]:
    # Projects where every paper bug has a CVE — no-CVE found bugs must be extra
    all_cve_projects = {p for p, s in supplement.items() if s["bugs"] == s["cves"] > 0}

    kept: list[dict] = []

    for r in bugs:
        rec = dict(r)
        if r["project"] not in kraken_projects:
            rec["where_url_found"] = "activity_history"
        elif rec.get("cve_id"):
            rec["where_url_found"] = "paper_artifact"
        elif r["project"] in all_cve_projects:
            rec["where_url_found"] = "activity_history"
        else:
            rec["where_url_found"] = ""  # resolved in pass 2
        kept.append(rec)

    # Pass 2: resolve remaining KRAKEN bugs by project count
    unresolved_by_proj: dict[str, list[dict]] = defaultdict(list)
    for rec in kept:
        if not rec["where_url_found"]:
            unresolved_by_proj[rec["project"]].append(rec)

    for proj, unresolved in unresolved_by_proj.items():
        paper_total = supplement.get(proj, {}).get("bugs", 0)
        total_kept = sum(1 for r in kept if r["project"] == proj)
        label = "paper_artifact" if total_kept == paper_total else "unknown"
        for rec in unresolved:
            rec["where_url_found"] = label

    return kept


DATE_CUTOFF = "2025-04-24"


def build_classified_bugs_csv() -> Path:
    from reporter import get_reporters, is_supported
    from client import git_short_commit
    classified_csv = OUTPUT_DIR / f"classified_{git_short_commit()}.csv"

    projects_rows = list(csv.DictReader(PROJECTS_CSV.open()))
    kraken_projects = {r["project"] for r in projects_rows}
    supplement = {r["project"]: {"bugs": int(r["bugs"]), "cves": int(r["cves"])} for r in projects_rows}

    print("Loading CVE map from cache...")
    cve_map, fragment_urls = _load_cve_map()

    bugs = _load_bugs(cve_map, fragment_urls, kraken_projects)
    classified = classify(bugs, kraken_projects, supplement)

    before = len(classified)
    classified = [r for r in classified if not r.get("date") or r["date"][:10] <= DATE_CUTOFF]
    dropped = before - len(classified)
    if dropped:
        print(f"  Dropped {dropped} bug(s) newer than {DATE_CUTOFF}")

    classified.sort(key=lambda r: (r["project"], r["bug_url"]))

    # Fetch reporters for GitHub URLs that have no author set
    fetchable = [r["bug_url"] for r in classified
                 if not r.get("author") and not r.get("reporter") and is_supported(r["bug_url"])]
    reporters = get_reporters(fetchable) if fetchable else {}

    with classified_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for rec in classified:
            reporter = rec.get("reporter") or rec.get("author") or reporters.get(rec["bug_url"], "")
            writer.writerow({
                "project":         rec.get("project", ""),
                "report_url":      rec["bug_url"],
                "related_url":     rec.get("related_url", ""),
                "where_url_found": rec["where_url_found"],
                "date":            rec.get("date", ""),
                "reporter":        reporter,
                "cve_id":          rec.get("cve_id", ""),
                "notes":           rec.get("notes", ""),
            })

    counts = {v: sum(1 for r in classified if r["where_url_found"] == v)
              for v in ("paper_artifact", "activity_history", "unknown")}
    print(
        f"Written {len(classified)} rows → {classified_csv}\n"
        f"  paper_artifact:   {counts['paper_artifact']}\n"
        f"  activity_history: {counts['activity_history']}\n"
        f"  unknown:          {counts['unknown']}"
    )
    return classified_csv


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    build_classified_bugs_csv()
