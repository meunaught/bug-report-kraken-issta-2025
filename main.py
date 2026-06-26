import sys

sys.path.insert(0, "src")

from cve_list import fetch_cve_list
from cve_fetch import fetch_all
from search import search_all, write_csv as write_author_csv


def _fetch_cve_ids() -> list[str]:
    print("Fetching CVE list from KRAKEN README...")
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
    print(f"Fetching CVE JSON records (refresh={refresh})...")
    _print_fetch_results(fetch_all(cve_ids, refresh=refresh))


def cmd_generate(args: list[str]) -> None:
    from classify import build_classified_bugs_csv
    build_classified_bugs_csv()


def cmd_match_prs(args: list[str]) -> None:
    from pr_match import match_prs
    print("Matching PRs to issues via HTML extraction...")
    match_prs()


def cmd_apply(args: list[str]) -> None:
    from apply import apply_overrides
    apply_overrides()


def cmd_verify(args: list[str]) -> None:
    from verify import verify
    sys.exit(0 if verify() else 1)


def cmd_search_author(args: list[str]) -> None:
    from search import AUTHOR_NAME, GITHUB_USERNAME, SF_USERNAME
    print(f"Searching bugs by {AUTHOR_NAME} "
          f"(GitHub: {GITHUB_USERNAME}, SF: {SF_USERNAME})")
    results = search_all()
    out = write_author_csv(results)
    print(f"  {len(results)} total → {out}")


COMMANDS = {
    "fetch":         (cmd_fetch,         "Download CVE JSON records into cache/"),
    "generate":      (cmd_generate,      "Build output/classified_auto.csv"),
    "search-author": (cmd_search_author, "Search bugs by author across GitHub, Trac, SF, Bugzilla"),
    "match-prs":     (cmd_match_prs,     "Fetch PR HTML, extract linked issues → data/generated/pr-matches.yaml"),
    "apply":         (cmd_apply,         "Apply pr-matches + overrides in-place to classified_{commit}.csv"),
    "verify":        (cmd_verify,        "Verify classified_{commit}.csv; on failure write cache/review/<project>.md"),
}


def usage() -> None:
    print("Usage: python main.py <command> [options]")
    print()
    print("Commands:")
    for name, (_, desc) in COMMANDS.items():
        print(f"  {name:16s}  {desc}")
    print()
    print("Options:")
    print("  --refresh        (fetch)  Re-download even if cached")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] not in COMMANDS:
        usage()
        sys.exit(1 if args else 0)

    cmd, _ = COMMANDS[args[0]]
    cmd(args[1:])
