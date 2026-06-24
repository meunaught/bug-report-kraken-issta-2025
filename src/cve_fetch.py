import json
from pathlib import Path

import httpx

from client import github_client, github_get

CVELISTV5_RAW = "https://raw.githubusercontent.com/CVEProject/cvelistV5/main/cves"
CACHE_DIR = Path(__file__).parent.parent / "cache" / "json"


def cve_json_url(cve_id: str) -> str:
    # CVE-YYYY-NNNNN  →  cves/YYYY/NNNxxx/CVE-YYYY-NNNNN.json
    _, year, number = cve_id.split("-")
    folder = number[:-3] + "xxx"
    return f"{CVELISTV5_RAW}/{year}/{folder}/{cve_id}.json"


def fetch_all(cve_ids: list[str], *, refresh: bool = False) -> dict[str, str]:
    """
    Fetch and cache CVE JSON records.

    Returns a dict mapping CVE ID → status:
      "cached"   — already on disk, skipped
      "fetched"  — newly downloaded
      "missing"  — HTTP 404, written as .missing sentinel
      "error"    — other HTTP error
    """
    CACHE_DIR.mkdir(exist_ok=True)
    results: dict[str, str] = {}

    with github_client() as client:
        for cve_id in cve_ids:
            json_path = CACHE_DIR / f"{cve_id}.json"
            missing_path = CACHE_DIR / f"{cve_id}.missing"

            if not refresh:
                if json_path.exists():
                    results[cve_id] = "cached"
                    continue
                if missing_path.exists():
                    results[cve_id] = "missing"
                    continue

            url = cve_json_url(cve_id)
            try:
                resp = client.get(url)
                if resp.status_code == 404:
                    missing_path.write_text(url)
                    results[cve_id] = "missing"
                else:
                    resp.raise_for_status()
                    # Validate it's parseable JSON before caching
                    json.loads(resp.text)
                    json_path.write_text(resp.text)
                    results[cve_id] = "fetched"
            except httpx.HTTPStatusError as e:
                print(f"  ERROR {cve_id}: HTTP {e.response.status_code}")
                results[cve_id] = "error"
            except Exception as e:
                print(f"  ERROR {cve_id}: {e}")
                results[cve_id] = "error"

    return results


if __name__ == "__main__":
    import sys
    from cve_list import fetch_cve_list

    refresh = "--refresh" in sys.argv
    print("Fetching CVE list from KRAKEN README...")
    cve_ids = fetch_cve_list()
    print(f"  {len(cve_ids)} CVE IDs found")

    print(f"Fetching CVE JSON records (refresh={refresh})...")
    results = fetch_all(cve_ids, refresh=refresh)

    counts = {"cached": 0, "fetched": 0, "missing": 0, "error": 0}
    for status in results.values():
        counts[status] += 1

    print(f"  cached:  {counts['cached']}")
    print(f"  fetched: {counts['fetched']}")
    print(f"  missing: {counts['missing']}")
    print(f"  error:   {counts['error']}")

    missing = [cve for cve, s in results.items() if s == "missing"]
    if missing:
        print(f"\nMissing CVEs: {', '.join(missing)}")
