import json
import re
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / "cache" / "json"

# URL patterns that identify bug tracker links.
_TRACKER_PATTERNS: list[re.Pattern] = [
    re.compile(r"github\.com/[^/]+/[^/]+/issues/\d+"),
    re.compile(r"bugzilla\.redhat\.com/show_bug\.cgi\?id=\d+"),
    re.compile(r"sourceforge\.net/p/[^/]+/(?:bugs|tickets)/\d+"),
    re.compile(r"trac\.ffmpeg\.org/ticket/\d+"),
    re.compile(r"lists\.gnu\.org/archive/html/[^/]+/"),
]

# URL substrings that identify non-tracker links to skip.
_SKIP = [
    "/commit/", "/compare/", "/pull/", "/tree/",
    "debian.org", "fedoraproject.org", "gentoo.org",
    "netapp.com", "apple.com", "seclists.org",
    "apache.org", "cwe.mitre.org", "gnu.com",
    "git.videolan.org", "cvsweb.netbsd.org",
    "xiaoxiongwang", "netbsd",
]


def extract_refs(cve_id: str) -> list[str]:
    json_path = CACHE_DIR / f"{cve_id}.json"
    if not json_path.exists():
        return []

    data = json.loads(json_path.read_text())
    try:
        raw_refs = data["containers"]["cna"]["references"]
    except KeyError:
        raw_refs = data.get("references", {}).get("reference_data", [])

    seen: set[str] = set()
    results: list[str] = []

    for r in raw_refs:
        url = r.get("url", "")
        if any(skip in url for skip in _SKIP):
            continue
        for pattern in _TRACKER_PATTERNS:
            if pattern.search(url):
                if url not in seen:
                    seen.add(url)
                    results.append(url)
                break

    return results


if __name__ == "__main__":
    from cve_list import fetch_cve_list

    cve_ids = fetch_cve_list()
    no_refs = []

    for cve_id in cve_ids:
        refs = extract_refs(cve_id)
        if not refs:
            no_refs.append(cve_id)
        else:
            for url in refs:
                print(f"{cve_id:25s}  {url}")

    if no_refs:
        print(f"\nNo refs found ({len(no_refs)}): {', '.join(no_refs)}")
