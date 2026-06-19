import sys

sys.path.insert(0, "src")

from build_csv import build_cves_csv
from fetch_cve_list import fetch_cve_list
from fetch_cves import fetch_all
from render_table import render


def _fetch_cve_ids() -> list[str]:
    print("Step 1 — fetching CVE list from KRAKEN README...")
    cve_ids = fetch_cve_list()
    print(f"  {len(cve_ids)} CVE IDs found")
    return cve_ids


def cmd_fetch(args: list[str]) -> None:
    refresh = "--refresh" in args
    cve_ids = _fetch_cve_ids()

    print(f"Step 2 — fetching CVE JSON records (refresh={refresh})...")
    results = fetch_all(cve_ids, refresh=refresh)

    counts = {"cached": 0, "fetched": 0, "missing": 0, "error": 0}
    for status in results.values():
        counts[status] += 1
    print(f"  cached: {counts['cached']}  fetched: {counts['fetched']}  "
          f"missing: {counts['missing']}  error: {counts['error']}")

    missing = [c for c, s in results.items() if s == "missing"]
    if missing:
        print(f"  Missing CVEs: {', '.join(missing)}")

    if counts["error"]:
        print(f"  WARNING: {counts['error']} fetch error(s) — rerun to retry")


def cmd_build_csv(args: list[str]) -> None:
    cve_ids = _fetch_cve_ids()
    print("Step 2 — building data/generated/cves.csv from cache...")
    build_cves_csv(cve_ids)


def cmd_generate(args: list[str]) -> None:
    cve_ids = _fetch_cve_ids()
    print("Step 2 — rendering tables from CSV...")
    render(total_cves=len(cve_ids))


def cmd_all(args: list[str]) -> None:
    refresh = "--refresh" in args
    cve_ids = _fetch_cve_ids()

    print(f"Step 2 — fetching CVE JSON records (refresh={refresh})...")
    results = fetch_all(cve_ids, refresh=refresh)
    counts = {"cached": 0, "fetched": 0, "missing": 0, "error": 0}
    for status in results.values():
        counts[status] += 1
    print(f"  cached: {counts['cached']}  fetched: {counts['fetched']}  "
          f"missing: {counts['missing']}  error: {counts['error']}")
    missing = [c for c, s in results.items() if s == "missing"]
    if missing:
        print(f"  Missing CVEs: {', '.join(missing)}")
    if counts["error"]:
        print(f"  WARNING: {counts['error']} fetch error(s) — rerun to retry")

    print("\nStep 3 — building data/generated/cves.csv from cache...")
    build_cves_csv(cve_ids)

    print("\nStep 4 — rendering tables from CSV...")
    render(total_cves=len(cve_ids))


COMMANDS = {
    "fetch":     (cmd_fetch,     "Download CVE JSON records into cache/"),
    "build-csv": (cmd_build_csv, "Extract data from cache into data/cves.csv"),
    "generate":  (cmd_generate,  "Render tex/generated/ tables from data/*.csv"),
    "all":       (cmd_all,       "fetch → build-csv → generate"),
}


def usage() -> None:
    print("Usage: python main.py <command> [--refresh]")
    print()
    print("Commands:")
    for name, (_, desc) in COMMANDS.items():
        print(f"  {name:12s}  {desc}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] not in COMMANDS:
        usage()
        sys.exit(1 if args else 0)

    cmd, _ = COMMANDS[args[0]]
    cmd(args[1:])
