import sys

sys.path.insert(0, "src")

from fetch_cve_list import fetch_cve_list
from fetch_cves import fetch_all
from render_table import render
from search_by_author import search_all, write_csv as write_author_csv


def _fetch_cve_ids() -> list[str]:
    print("Step 1 — fetching CVE list from KRAKEN README...")
    cve_ids = fetch_cve_list()
    print(f"  {len(cve_ids)} CVE IDs found")
    return cve_ids


def _print_fetch_results(results: dict) -> None:
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


def cmd_fetch(args: list[str]) -> None:
    refresh = "--refresh" in args
    cve_ids = _fetch_cve_ids()
    print(f"Step 2 — fetching CVE JSON records (refresh={refresh})...")
    _print_fetch_results(fetch_all(cve_ids, refresh=refresh))


def cmd_generate(args: list[str]) -> None:
    cve_ids = _fetch_cve_ids()
    print("Step 2 — rendering tables from CSV...")
    render(cve_ids)


def cmd_all(args: list[str]) -> None:
    refresh = "--refresh" in args
    cve_ids = _fetch_cve_ids()

    print(f"Step 2 — fetching CVE JSON records (refresh={refresh})...")
    _print_fetch_results(fetch_all(cve_ids, refresh=refresh))

    print("\nStep 3 — searching bug trackers by author...")
    from search_by_author import AUTHOR_NAME, GITHUB_USERNAME, SF_USERNAME
    print(f"  {AUTHOR_NAME} (GitHub: {GITHUB_USERNAME}, SF: {SF_USERNAME})")
    out = write_author_csv(search_all())
    print(f"  Written → {out}")

    print("\nStep 4 — rendering tables...")
    render(cve_ids)


def cmd_search_author(args: list[str]) -> None:
    from search_by_author import AUTHOR_NAME, GITHUB_USERNAME, SF_USERNAME
    print(f"Searching bugs by {AUTHOR_NAME} "
          f"(GitHub: {GITHUB_USERNAME}, SF: {SF_USERNAME})")
    results = search_all()
    out = write_author_csv(results)
    print(f"  {len(results)} total → {out}")


COMMANDS = {
    "fetch":         (cmd_fetch,         "Download CVE JSON records into cache/"),
    "generate":      (cmd_generate,      "Render tex/generated/ tables from CSV + cache"),
    "all":           (cmd_all,           "fetch → search-author → generate"),
    "search-author": (cmd_search_author, "Search bugs by author across GitHub, Trac, SF, Bugzilla"),
}


def usage() -> None:
    print("Usage: python main.py <command> [options]")
    print()
    print("Commands:")
    for name, (_, desc) in COMMANDS.items():
        print(f"  {name:16s}  {desc}")
    print()
    print("Options:")
    print("  --refresh        (fetch, all)  Re-download even if cached")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] not in COMMANDS:
        usage()
        sys.exit(1 if args else 0)

    cmd, _ = COMMANDS[args[0]]
    cmd(args[1:])
