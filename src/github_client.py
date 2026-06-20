import os
from pathlib import Path

import httpx

_ENV_FILE = Path(__file__).parent.parent / ".env"


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
