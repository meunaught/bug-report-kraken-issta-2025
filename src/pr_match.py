"""
Fetch HTML for all PR URLs in author_bugs.csv, extract linked issues,
and write data/generated/pr-matches.yaml.

Run via: python main.py match-prs
"""

import csv
from pathlib import Path

import httpx
import yaml

from client import HTML_PR as PR_CACHE, ROOT, url_slug

AUTHOR_CSV = ROOT / "data" / "generated" / "author_bugs.csv"
PR_MATCHES = ROOT / "data" / "generated" / "pr-matches.yaml"


def _fetch_html(url: str) -> str | None:
    path = PR_CACHE / url_slug(url, ".html")
    if path.exists():
        print(f"  cached  {url}")
        return path.read_text(encoding="utf-8")
    try:
        print(f"  fetch   {url}")
        r = httpx.get(url, follow_redirects=True, timeout=15,
                      headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        path.write_text(r.text, encoding="utf-8")
        return r.text
    except Exception as e:
        print(f"  ERROR   {url}: {e}")
        return None


def _extract_match(pr_url: str, html: str) -> dict:
    """Return a match record for this PR."""
    m = re.search(r"github\.com/([^/]+/[^/]+)/pull/\d+", pr_url)
    if not m:
        return {"issue_url": None, "confidence": "low",
                "reason": "could not parse repo from PR URL"}
    repo = m.group(1)

    issue_nums = list(dict.fromkeys(
        re.findall(rf'href="(?:https://github\.com)?/{re.escape(repo)}/issues/(\d+)"', html)
    ))

    if not issue_nums:
        return {"issue_url": None, "confidence": "high",
                "reason": "no issue links found in PR HTML"}

    issue_num = issue_nums[0]
    issue_url = f"https://github.com/{repo}/issues/{issue_num}"

    if len(issue_nums) == 1:
        return {"issue_url": issue_url, "confidence": "high",
                "reason": f"single issue link #{issue_num} in PR HTML"}

    others = ", ".join(f"#{n}" for n in issue_nums[1:])
    return {"issue_url": issue_url, "confidence": "low",
            "reason": f"multiple issue links; using first #{issue_num} (others: {others})"}


def match_prs() -> None:
    PR_CACHE.mkdir(parents=True, exist_ok=True)

    # Load PR URLs from author_bugs.csv
    pr_urls = [
        r["bug_url"] for r in csv.DictReader(AUTHOR_CSV.open())
        if "/pull/" in r["bug_url"]
    ]
    if not pr_urls:
        print("No PR URLs found in author_bugs.csv.")
        return

    # Load already-matched PRs so we don't overwrite confirmed entries
    existing: dict[str, dict] = {}
    if PR_MATCHES.exists():
        loaded = yaml.safe_load(PR_MATCHES.read_text()) or []
        existing = {e["pr_url"]: e for e in loaded}

    new_prs = [u for u in pr_urls if u not in existing]
    print(f"  {len(pr_urls)} PRs total, {len(existing)} already matched, "
          f"{len(new_prs)} to process")

    new_entries: list[dict] = []
    for pr_url in new_prs:
        html = _fetch_html(pr_url)
        if html is None:
            match = {"issue_url": None, "confidence": "low", "reason": "fetch failed"}
        else:
            match = _extract_match(pr_url, html)
        entry = {"pr_url": pr_url, **match}
        new_entries.append(entry)
        print(f"    → issue_url={entry['issue_url']}  [{entry['confidence']}]  {entry['reason']}")

    all_entries = list(existing.values()) + new_entries

    header = (
        "# PR-to-issue matches\n"
        "# Populated by: python main.py match-prs\n"
        "# Applied in pass 1 of: python main.py apply  (before labelling overrides)\n"
        "#\n"
        "# Fields:\n"
        "#   pr_url:     PR URL as found in author_bugs.csv\n"
        "#   issue_url:  linked issue URL, or null if none found\n"
        "#   confidence: high | medium | low\n"
        "#   reason:     what was found (or not found) in the HTML\n"
        "\n"
    )

    PR_MATCHES.write_text(
        header + yaml.dump(all_entries, allow_unicode=True, default_flow_style=False,
                           sort_keys=False)
    )
    print(f"Written {len(all_entries)} entries → {PR_MATCHES}")
