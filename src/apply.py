"""
Apply overrides to output/classified_{commit}.csv (in-place).

Two sequential passes:
  Pass 1 — PR matching  (data/generated/pr-matches.yaml)
    Sets related_url on PR rows whose linked issue was filed by the verified author.
  Pass 2 — Labelling    (data/static/patch.yaml)
    Applies label/CVE/reporter/archived-url/cve-ref corrections.

Run via: python main.py apply
"""

import csv
import yaml
from pathlib import Path

from client import git_short_commit

ROOT              = Path(__file__).parent.parent
PR_MATCHES_YAML   = ROOT / "data" / "generated" / "pr-matches.yaml"
AI_OVERRIDES_YAML = ROOT / "data" / "static" / "patch.yaml"
OUTPUT_DIR        = ROOT / "output"

FIELDS = ["project", "report_url", "related_url", "where_url_found", "date", "reporter", "cve_id", "notes"]

ACTIONS = {"exclude", "set_label", "set_cve_id", "set_reporter", "set_archived_url", "set_cve_ref", "set_date"}


AUTHOR_USERNAMES = {"seviezhou", "azhouad", "zhouhan"}


def _pass1_pr_matching(rows: list[dict]) -> tuple[list[dict], dict[str, int]]:
    """Set related_url on PR rows whose linked issue was filed by the verified author."""
    from reporter import get_reporters

    stats = {"pr_linked": 0}

    if not PR_MATCHES_YAML.exists():
        return rows, stats

    matches = yaml.safe_load(PR_MATCHES_YAML.read_text()) or []
    high_conf   = [m for m in matches if m.get("issue_url") and m.get("confidence") == "high"]
    pr_to_issue = {m["pr_url"]: m["issue_url"] for m in high_conf}

    # Use reporter already in classified_auto for known issues; API only for unknowns
    known_reporters = {row["report_url"]: row["reporter"] for row in rows}
    issue_urls_needing_fetch = [
        issue for issue in pr_to_issue.values()
        if issue not in known_reporters
    ]
    fetched = get_reporters(issue_urls_needing_fetch) if issue_urls_needing_fetch else {}
    reporters = {**fetched, **known_reporters}
    verified  = {pr: issue for pr, issue in pr_to_issue.items()
                 if reporters.get(issue) in AUTHOR_USERNAMES}

    kept: list[dict] = []
    for row in rows:
        url = row["report_url"]
        row = dict(row)
        if url in verified:
            row["related_url"] = verified[url]
            stats["pr_linked"] += 1
        kept.append(row)

    return kept, stats


def _pass2_labelling(rows: list[dict]) -> tuple[list[dict], dict[str, int]]:
    """Apply label/CVE/reporter/related_url overrides."""
    overrides = yaml.safe_load(AI_OVERRIDES_YAML.read_text())

    unknown_actions = {r["action"] for r in overrides} - ACTIONS
    if unknown_actions:
        raise ValueError(f"Unknown actions in overrides: {unknown_actions}")

    excludes      = {r["report_url"] for r in overrides if r["action"] == "exclude"}
    set_label     = {r["report_url"]: r["value"] for r in overrides if r["action"] == "set_label"}
    set_cve       = {r["report_url"]: r["value"] for r in overrides if r["action"] == "set_cve_id"}
    set_reporter  = {r["report_url"]: r["value"] for r in overrides if r["action"] == "set_reporter"}
    set_archived  = {r["report_url"]: r["value"] for r in overrides if r["action"] == "set_archived_url"}
    set_cve_ref   = {r["report_url"]: r["value"] for r in overrides if r["action"] == "set_cve_ref"}
    set_date      = {r["report_url"]: r["value"] for r in overrides if r["action"] == "set_date"}

    stats = {a: 0 for a in ACTIONS}
    kept: list[dict] = []

    for row in rows:
        url = row["report_url"]
        if url in excludes:
            stats["exclude"] += 1
            continue
        row = dict(row)
        if url in set_label:    row["where_url_found"] = set_label[url];    stats["set_label"] += 1
        if url in set_cve:      row["cve_id"]          = set_cve[url];      stats["set_cve_id"] += 1
        if url in set_reporter: row["reporter"]        = set_reporter[url]; stats["set_reporter"] += 1
        if url in set_archived:
            row["related_url"] = set_archived[url]
            row["notes"]       = "Archived copy (original deleted)"
            stats["set_archived_url"] += 1
        if url in set_cve_ref:
            row["notes"] = f"[CVE-REFERENCE] {set_cve_ref[url]}"
            stats["set_cve_ref"] += 1
        if url in set_date:
            row["date"] = set_date[url]
            stats["set_date"] += 1
        kept.append(row)

    return kept, stats


def apply_overrides() -> Path:
    commit = git_short_commit()
    classified_csv = OUTPUT_DIR / f"classified_{commit}.csv"
    if not classified_csv.exists():
        print(f"ERROR: {classified_csv} not found — run `python main.py generate` first")
        return classified_csv

    rows = list(csv.DictReader(classified_csv.open()))
    for row in rows:
        row.setdefault("notes", "")

    print("Pass 1: PR matching")
    rows, pr_stats = _pass1_pr_matching(rows)
    print(f"  PRs linked:     {pr_stats['pr_linked']}")

    print("Pass 2: Labelling overrides")
    rows, label_stats = _pass2_labelling(rows)

    output_csv = classified_csv

    with output_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    counts = {v: sum(1 for r in rows if r["where_url_found"] == v)
              for v in ("paper_artifact", "activity_history", "unknown")}
    print(f"Written {len(rows)} rows → {output_csv}")
    print(f"  paper_artifact:   {counts['paper_artifact']}")
    print(f"  activity_history: {counts['activity_history']}")
    print(f"  unknown:          {counts['unknown']}")
    print(f"  excluded:         {label_stats['exclude']}")
    print(f"  label updated:    {label_stats['set_label']}")
    print(f"  cve_id set:       {label_stats['set_cve_id']}")
    print(f"  reporter set:     {label_stats['set_reporter']}")
    print(f"  archived url set: {label_stats['set_archived_url']}")
    print(f"  cve-ref notes:    {label_stats['set_cve_ref']}")
    print(f"  date set:         {label_stats['set_date']}")
    return output_csv
