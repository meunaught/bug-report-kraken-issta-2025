import json
import re
from dataclasses import dataclass
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / "cache"


@dataclass
class BugRef:
    url: str
    label: str


# URL patterns that are bug tracker links, in priority order.
# Each entry: (compiled regex, label template using first capture group)
_TRACKER_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"github\.com/[^/]+/[^/]+/issues/(\d+)"),          "Issue #{}"),
    (re.compile(r"bugzilla\.redhat\.com/show_bug\.cgi\?id=(\d+)"),  "Bug #{}"),
    (re.compile(r"sourceforge\.net/p/[^/]+/(?:bugs|tickets)/(\d+)"), "SF #{}"),
    (re.compile(r"trac\.ffmpeg\.org/ticket/(\d+)"),                 "Trac #{}"),
    (re.compile(r"lists\.gnu\.org/archive/html/([^/]+)/"),          "ML Post"),
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


def _make_label(pattern: re.Pattern, template: str, url: str) -> str:
    m = pattern.search(url)
    if not m:
        return template  # e.g. "ML Post" has no capture group
    group = m.group(1)
    return template.format(group) if "{}" in template else template


def extract_refs(cve_id: str) -> list[BugRef]:
    json_path = CACHE_DIR / f"{cve_id}.json"
    if not json_path.exists():
        return []

    data = json.loads(json_path.read_text())
    try:
        raw_refs = data["containers"]["cna"]["references"]
    except KeyError:
        raw_refs = data.get("references", {}).get("reference_data", [])

    seen: set[str] = set()
    results: list[BugRef] = []

    for r in raw_refs:
        url = r.get("url", "")

        if any(skip in url for skip in _SKIP):
            continue

        for pattern, template in _TRACKER_PATTERNS:
            if pattern.search(url):
                if url not in seen:
                    seen.add(url)
                    results.append(BugRef(url=url, label=_make_label(pattern, template, url)))
                break

    return results


if __name__ == "__main__":
    from fetch_cve_list import fetch_cve_list

    cve_ids = fetch_cve_list()
    no_refs = []

    for cve_id in cve_ids:
        refs = extract_refs(cve_id)
        if not refs:
            no_refs.append(cve_id)
        else:
            for ref in refs:
                print(f"{cve_id:25s}  {ref.label:15s}  {ref.url}")

    if no_refs:
        print(f"\nNo refs found ({len(no_refs)}): {', '.join(no_refs)}")
