import os
import re
import subprocess
from pathlib import Path

import httpx

_ENV_FILE = Path(__file__).parent.parent / ".env"

ROOT       = Path(__file__).parent.parent
ISSUE_JSON = ROOT / "cache" / "json" / "issues"
PR_JSON    = ROOT / "cache" / "json" / "prs"
CVE_JSON   = ROOT / "cache" / "json" / "cve"
HTML_ISSUE = ROOT / "cache" / "html" / "issue"
HTML_PR    = ROOT / "cache" / "html" / "pr"
TRAC_CACHE = ROOT / "cache" / "json" / "trac_ffmpeg.tsv"


def url_slug(url: str, ext: str = ".json") -> str:
    url = re.sub(r"^https?://", "", url)
    return re.sub(r"[^a-zA-Z0-9._-]", "_", url) + ext


def _load_env() -> None:
    if not _ENV_FILE.exists():
        return
    for line in _ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


_load_env()


def github_headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def github_get(url: str, **kwargs) -> httpx.Response:
    return httpx.get(url, headers=github_headers(), follow_redirects=True,
                     timeout=20, **kwargs)


def github_client(**kwargs) -> httpx.Client:
    return httpx.Client(headers=github_headers(), follow_redirects=True,
                        timeout=30, **kwargs)


def git_short_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except Exception:
        return "unknown"
