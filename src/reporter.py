"""
Fetch and cache the reporter username and creation date for bug URLs on supported platforms.

Supported:
  - GitHub (issues, PRs, issue comments)
  - SourceForge (bugs, tickets)

Unsupported platforms (Bugzilla, Debian, mailing lists, Wayback) return "".

Caches:
  cache/json/issues/{slug}.json  — full GitHub issue / SF ticket JSON
  cache/json/prs/{slug}.json     — full GitHub PR JSON
"""

import json
import re
from pathlib import Path

import httpx

from client import ISSUE_JSON, PR_JSON, url_slug

# ── Platform detection ────────────────────────────────────────────────────────

_GH_ISSUE_RE   = re.compile(r"github\.com/([^/]+)/([^/]+)/issues/(\d+)")
_GH_COMMENT_RE = re.compile(r"#issuecomment-(\d+)$")
_GH_PR_RE      = re.compile(r"github\.com/([^/]+)/([^/]+)/pull/(\d+)")
_SF_RE         = re.compile(r"sourceforge\.net/p/([^/]+)/([^/]+)/(\d+)")


def is_supported(url: str) -> bool:
    return bool(
        _GH_ISSUE_RE.search(url)
        or _GH_PR_RE.search(url)
        or _SF_RE.search(url)
    )


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _gh_cache_path(url: str) -> Path:
    return (PR_JSON if _GH_PR_RE.search(url) else ISSUE_JSON) / url_slug(url)


def _sf_json_path(url: str) -> Path:
    return ISSUE_JSON / url_slug(url)


def _reporter_from_cache(url: str) -> str | None:
    """Return cached reporter, or None if no cache file exists."""
    if _GH_ISSUE_RE.search(url) or _GH_PR_RE.search(url):
        path = _gh_cache_path(url)
        if path.exists():
            return json.loads(path.read_text()).get("user", {}).get("login", "")
        return None
    if _SF_RE.search(url):
        path = _sf_json_path(url)
        if path.exists():
            return json.loads(path.read_text()).get("ticket", {}).get("reported_by", "")
        return None
    return ""  # unsupported — no fetch needed


# ── Fetchers ──────────────────────────────────────────────────────────────────

def _fetch_github(url: str) -> str:
    from client import github_get

    comment_m = _GH_COMMENT_RE.search(url)
    issue_m   = _GH_ISSUE_RE.search(url)
    pr_m      = _GH_PR_RE.search(url)

    try:
        if comment_m and issue_m:
            owner, repo = issue_m.group(1), issue_m.group(2)
            api = (f"https://api.github.com/repos/{owner}/{repo}"
                   f"/issues/comments/{comment_m.group(1)}")
        elif issue_m:
            owner, repo, num = issue_m.group(1), issue_m.group(2), issue_m.group(3)
            api = f"https://api.github.com/repos/{owner}/{repo}/issues/{num}"
        elif pr_m:
            owner, repo, num = pr_m.group(1), pr_m.group(2), pr_m.group(3)
            api = f"https://api.github.com/repos/{owner}/{repo}/pulls/{num}"
        else:
            return ""

        resp = github_get(api)
        if resp.status_code == 200:
            data = resp.json()
            cache_path = _gh_cache_path(url)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(data))
            return data.get("user", {}).get("login", "")
    except Exception:
        pass
    return ""


def _fetch_sourceforge(url: str) -> str:
    m = _SF_RE.search(url)
    if not m:
        return ""
    project, tracker, ticket_id = m.group(1), m.group(2), m.group(3)

    json_path = _sf_json_path(url)
    if json_path.exists():
        return json.loads(json_path.read_text()).get("ticket", {}).get("reported_by", "")

    api = f"https://sourceforge.net/rest/p/{project}/{tracker}/{ticket_id}/"
    try:
        resp = httpx.get(api, timeout=20, follow_redirects=True)
        if resp.status_code == 200:
            data = resp.json()
            ISSUE_JSON.mkdir(parents=True, exist_ok=True)
            json_path.write_text(json.dumps(data))
            return data.get("ticket", {}).get("reported_by", "")
    except Exception:
        pass
    return ""


def _fetch(url: str) -> str:
    if _GH_ISSUE_RE.search(url) or _GH_PR_RE.search(url):
        return _fetch_github(url)
    if _SF_RE.search(url):
        return _fetch_sourceforge(url)
    return ""


# ── Public API ────────────────────────────────────────────────────────────────

def get_reporters(urls: list[str]) -> dict[str, str]:
    """Return {url: reporter} for all given URLs, fetching uncached ones."""
    result: dict[str, str] = {}
    to_fetch = [u for u in urls if _reporter_from_cache(u) is None and is_supported(u)]

    if to_fetch:
        print(f"  Fetching reporters for {len(to_fetch)} URL(s)...")
        for url in to_fetch:
            login = _fetch(url)
            print(f"    {login or '(unknown)':20s} {url}")

    for url in urls:
        cached = _reporter_from_cache(url)
        result[url] = cached if cached is not None else ""

    return result


def _normalize_sf_date(raw: str) -> str:
    """Convert SF created_date ('2020-08-03 02:09:58.162000') to ISO 8601."""
    if not raw:
        return ""
    try:
        import datetime
        dt = datetime.datetime.strptime(raw[:19], "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return raw


def get_sf_dates(urls: list[str]) -> dict[str, str]:
    """Return {url: created_date} for SourceForge URLs with cached JSON."""
    result: dict[str, str] = {}
    for url in urls:
        if not _SF_RE.search(url):
            continue
        json_path = _sf_json_path(url)
        if json_path.exists():
            ticket = json.loads(json_path.read_text()).get("ticket", {})
            result[url] = _normalize_sf_date(ticket.get("created_date", ""))
    return result
