import json
import re
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / "cache"

# CVEs whose references don't contain a GitHub URL — project name hardcoded.
_HARDCODED: dict[str, str] = {
    "CVE-2020-23922": "giflib",
    "CVE-2020-24995": "ffmpeg",
    "CVE-2021-32280": "fig2dev",
    "CVE-2021-32614": "dmg2img",
    "CVE-2021-3548":  "dmg2img",
    "CVE-2021-33479": "gocr",
    "CVE-2021-33480": "gocr",
    "CVE-2021-33481": "gocr",
    "CVE-2021-39537": "ncurses",
}

# Repo names that don't match the paper's project name.
_REPO_ALIAS: dict[str, str] = {
    "pbrt-v3": "pbrt",
}


def _github_repo(url: str) -> str | None:
    """Return lowercase repo name from a github.com URL, or None."""
    m = re.match(r"https?://github\.com/[^/]+/([^/]+)", url)
    return m.group(1).lower() if m else None


def extract_project(cve_id: str) -> str:
    if cve_id in _HARDCODED:
        return _HARDCODED[cve_id]

    json_path = CACHE_DIR / f"{cve_id}.json"
    if not json_path.exists():
        return "UNKNOWN"

    data = json.loads(json_path.read_text())
    try:
        refs = data["containers"]["cna"]["references"]
    except KeyError:
        refs = data.get("references", {}).get("reference_data", [])

    for r in refs:
        name = _github_repo(r.get("url", ""))
        if name:
            return _REPO_ALIAS.get(name, name)

    return "UNKNOWN"


if __name__ == "__main__":
    from fetch_cve_list import fetch_cve_list

    cve_ids = fetch_cve_list()
    unknowns = []
    projects: dict[str, list[str]] = {}

    for cve_id in cve_ids:
        project = extract_project(cve_id)
        if project == "UNKNOWN":
            unknowns.append(cve_id)
        projects.setdefault(project, []).append(cve_id)

    for project, cves in sorted(projects.items()):
        print(f"{project:20s} {len(cves):3d}  {', '.join(cves)}")

    if unknowns:
        print(f"\nUNKNOWN ({len(unknowns)}): {', '.join(unknowns)}")
    else:
        print(f"\nAll {len(cve_ids)} CVEs resolved.")
