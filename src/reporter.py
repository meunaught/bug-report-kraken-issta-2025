"""
Fetch and cache the reporter username for bug URLs on supported platforms.

Supported:
  - GitHub (issues, PRs, issue comments)
  - SourceForge (bugs, tickets)

Unsupported platforms (Bugzilla, Debian, mailing lists, Wayback) return "".

Cache: cache/json/authors.json — {url: login}. API is only called for URLs not yet
in cache.
"""

import json
import re
from pathlib import Path

import httpx

CACHE_PATH = Path(__file__).parent.parent / "cache" / "json" / "authors.json"

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
            return resp.json().get("user", {}).get("login", "")
    except Exception:
        pass
    return ""


def _fetch_sourceforge(url: str) -> str:
    m = _SF_RE.search(url)
    if not m:
        return ""
    project, tracker, ticket_id = m.group(1), m.group(2), m.group(3)
    api = f"https://sourceforge.net/rest/p/{project}/{tracker}/{ticket_id}/"
    try:
        resp = httpx.get(api, timeout=20, follow_redirects=True)
        if resp.status_code == 200:
            return resp.json().get("ticket", {}).get("reported_by", "")
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

def _load_cache() -> dict[str, str]:
    return json.loads(CACHE_PATH.read_text()) if CACHE_PATH.exists() else {}


def _save_cache(cache: dict[str, str]) -> None:
    CACHE_PATH.write_text(json.dumps(cache, indent=2, sort_keys=True))


def get_reporters(urls: list[str]) -> dict[str, str]:
    """Return {url: reporter} for all given URLs, fetching uncached ones."""
    cache = _load_cache()
    missing = [u for u in urls if u not in cache and is_supported(u)]

    if missing:
        print(f"  Fetching reporters for {len(missing)} URL(s)...")
        for url in missing:
            login = _fetch(url)
            cache[url] = login
            print(f"    {login or '(unknown)':20s} {url}")
        _save_cache(cache)

    return {u: cache.get(u, "") for u in urls}
