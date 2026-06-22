import csv
import re
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from github_client import github_get

DATA_DIR = Path(__file__).parent.parent / "data" / "generated"

# ── known identities ──────────────────────────────────────────────────────────

# Anshunkang Zhou — first author of the KRAKEN paper.
AUTHOR_NAME     = "Anshunkang Zhou"
GITHUB_USERNAME = "seviezhou"
SF_USERNAME     = "azhouad"
SF_USERNAMES    = {SF_USERNAME, "zhouhan"}  # additional SF identity for advancecomp
TRAC_USERNAME   = "seviezhou"   # confirmed from existing cves.csv entries

# (sf_project, sf_tracker, internal_project_name)
# SF project slugs differ from our internal names.
SF_PROJECTS: list[tuple[str, str, str]] = [
    ("giflib",       "bugs",    "giflib"),
    ("jocr",         "bugs",    "gocr"),
    ("mcj",          "tickets", "fig2dev"),
    ("sox",          "bugs",    "sox"),
    ("advancemame",  "bugs",    "advancecomp"),
]

# Red Hat Bugzilla IDs confirmed to be from Anshunkang Zhou.
# 1959585, 1959911 — ack text "Name: Anshunkang Zhou" present.
# 1962854, 1962861, 1962865 — gocr RH tracking bugs linked from azhouad's SF reports.
BUGZILLA_CONFIRMED: dict[str, list[int]] = {
    "dmg2img": [1959585, 1959911],
    "gocr":    [1962854, 1962861, 1962865],
}


@dataclass
class BugResult:
    project: str
    bug_url: str
    author:  str


# ── GitHub ────────────────────────────────────────────────────────────────────

def _repo_name(repository_url: str) -> str:
    m = re.search(r"/repos/[^/]+/([^/]+)$", repository_url)
    return m.group(1).lower() if m else ""


def search_github() -> list[BugResult]:
    results: list[BugResult] = []
    page = 1

    while True:
        r = github_get(
            "https://api.github.com/search/issues",
            params={"q": f"author:{GITHUB_USERNAME} type:issue",
                    "per_page": 100, "page": page},
        )
        if r.status_code == 422:
            break
        if r.status_code == 403:
            print(f"    WARNING: rate-limited after {len(results)} results")
            break
        r.raise_for_status()

        items = r.json().get("items", [])
        for item in items:
            results.append(BugResult(
                project=_repo_name(item.get("repository_url", "")),
                bug_url=item.get("html_url", ""),
                author=GITHUB_USERNAME,
            ))

        if len(items) < 100 or page * 100 >= 1000:
            break
        page += 1
        time.sleep(1)

    return results


# ── SourceForge ───────────────────────────────────────────────────────────────

def _sf_all_ticket_nums(sf_project: str, sf_tracker: str) -> list[int]:
    """Paginate the list endpoint (returns ticket_num + summary only)."""
    nums: list[int] = []
    page = 0  # SF REST API uses 0-based page indexing
    while True:
        try:
            r = httpx.get(
                f"https://sourceforge.net/rest/p/{sf_project}/{sf_tracker}/",
                params={"limit": 100, "page": page},
                follow_redirects=True, timeout=20,
            )
        except Exception:
            break
        if r.status_code != 200:
            break
        tickets = r.json().get("tickets", [])
        nums.extend(t["ticket_num"] for t in tickets if "ticket_num" in t)
        if len(tickets) < 100:
            break
        page += 1
    return nums


def search_sourceforge() -> list[BugResult]:
    from reporter_fetcher import get_reporters

    results: list[BugResult] = []

    for sf_project, sf_tracker, internal in SF_PROJECTS:
        nums = _sf_all_ticket_nums(sf_project, sf_tracker)
        print(f"    {sf_project}/{sf_tracker}: {len(nums)} tickets, fetching each...")

        urls = [f"https://sourceforge.net/p/{sf_project}/{sf_tracker}/{num}" for num in nums]
        reporters = get_reporters(urls)

        for url, reporter in reporters.items():
            if reporter in SF_USERNAMES:
                results.append(BugResult(
                    project=internal,
                    bug_url=url,
                    author=reporter,
                ))

    return results


# ── FFmpeg Trac ───────────────────────────────────────────────────────────────

def search_trac() -> list[BugResult]:
    url = f"https://trac.ffmpeg.org/query?reporter={TRAC_USERNAME}&format=tab"
    try:
        r = httpx.get(url, follow_redirects=True, timeout=20)
    except Exception:
        return []
    if r.status_code != 200:
        return []

    results: list[BugResult] = []
    lines = r.text.splitlines()
    if len(lines) < 2:
        return []

    headers = [h.strip("﻿") for h in lines[0].split("\t")]
    try:
        id_col = headers.index("id")
    except ValueError:
        id_col = 0

    for line in lines[1:]:
        cols = line.split("\t")
        ticket_id = cols[id_col].strip() if id_col < len(cols) else ""
        if ticket_id:
            results.append(BugResult(
                project="ffmpeg",
                bug_url=f"https://trac.ffmpeg.org/ticket/{ticket_id}",
                author=TRAC_USERNAME,
            ))

    return results


# ── Red Hat Bugzilla ──────────────────────────────────────────────────────────

def _bz_ack_name(bug_id: int) -> str:
    try:
        r = httpx.get(
            f"https://bugzilla.redhat.com/rest/bug/{bug_id}/comment",
            follow_redirects=True, timeout=20,
        )
        if r.status_code != 200:
            return ""
        comments = r.json().get("bugs", {}).get(str(bug_id), {}).get("comments", [])
        for c in comments:
            m = re.search(r"Acknowledgments?:\s*\n+\s*Name:\s*(.+)", c.get("text", ""))
            if m:
                return m.group(1).strip()
    except Exception:
        pass
    return ""


def search_bugzilla() -> list[BugResult]:
    results: list[BugResult] = []
    for project, ids in BUGZILLA_CONFIRMED.items():
        for bug_id in ids:
            results.append(BugResult(
                project=project,
                bug_url=f"https://bugzilla.redhat.com/show_bug.cgi?id={bug_id}",
                author=AUTHOR_NAME,
            ))
    return results


# ── combined ──────────────────────────────────────────────────────────────────

def search_all() -> list[BugResult]:
    all_results: list[BugResult] = []

    print("  GitHub Issues:")
    gh = search_github()
    print(f"    {len(gh)} found")
    all_results.extend(gh)

    print("  FFmpeg Trac:")
    trac = search_trac()
    print(f"    {len(trac)} found")
    all_results.extend(trac)

    print("  SourceForge:")
    sf = search_sourceforge()
    print(f"    {len(sf)} found")
    all_results.extend(sf)

    print("  Red Hat Bugzilla:")
    bz = search_bugzilla()
    print(f"    {len(bz)} found")
    all_results.extend(bz)

    return all_results


def write_csv(results: list[BugResult]) -> Path:
    from dataclasses import asdict
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / "bugs_by_author.csv"
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["project", "bug_url", "author"])
        writer.writeheader()
        writer.writerows(asdict(r) for r in results)
    return out
