"""
Apply overrides to output/classified_auto.csv → output/classified_human_{commit}.csv

Two sequential passes:
  Pass 1 — PR matching  (data/generated/pr-matches.yaml)
    Excludes PR rows; sets related_url on matched issue rows.
  Pass 2 — Labelling    (data/ai/ai-overrides.yaml, data/overrides.yaml)
    Applies label/CVE/reporter/related_url corrections on the PR-cleaned dataset.

Run via: python main.py apply
"""

import csv
import yaml
from pathlib import Path

from client import git_short_commit

ROOT              = Path(__file__).parent.parent
CLASSIFIED_CSV    = ROOT / "output" / "classified_auto.csv"
PR_MATCHES_YAML   = ROOT / "data" / "generated" / "pr-matches.yaml"
AI_OVERRIDES_YAML = ROOT / "data" / "ai" / "ai-overrides.yaml"
OVERRIDES_YAML    = ROOT / "data" / "overrides.yaml"
OUTPUT_DIR        = ROOT / "output"

FIELDS = ["project", "report_url", "related_url", "where_url_found", "reporter", "cve_id", "notes"]

ACTIONS = {"exclude", "set_label", "set_cve_id", "set_reporter", "set_related_url"}


def _pass1_pr_matching(rows: list[dict]) -> tuple[list[dict], dict[str, int]]:
    """Exclude PR rows and set related_url on matched issue rows."""
    stats = {"pr_excluded": 0, "issue_linked": 0}

    if not PR_MATCHES_YAML.exists():
        return rows, stats

    matches = yaml.safe_load(PR_MATCHES_YAML.read_text()) or []
    high_conf    = [m for m in matches if m.get("issue_url") and m.get("confidence") == "high"]
    pr_excludes  = {m["pr_url"] for m in high_conf}
    issue_to_pr  = {m["issue_url"]: m["pr_url"] for m in high_conf}

    kept: list[dict] = []
    for row in rows:
        url = row["report_url"]
        if url in pr_excludes:
            stats["pr_excluded"] += 1
            continue
        row = dict(row)
        if url in issue_to_pr:
            row["related_url"] = issue_to_pr[url]
            row["notes"] = "PR by author"
            stats["issue_linked"] += 1
        kept.append(row)

    return kept, stats


def _pass2_labelling(rows: list[dict]) -> tuple[list[dict], dict[str, int]]:
    """Apply label/CVE/reporter/related_url overrides."""
    overrides = (
        yaml.safe_load(AI_OVERRIDES_YAML.read_text()) +
        yaml.safe_load(OVERRIDES_YAML.read_text())
    )

    unknown_actions = {r["action"] for r in overrides} - ACTIONS
    if unknown_actions:
        raise ValueError(f"Unknown actions in overrides: {unknown_actions}")

    excludes     = {r["report_url"] for r in overrides if r["action"] == "exclude"}
    set_label    = {r["report_url"]: r["value"] for r in overrides if r["action"] == "set_label"}
    set_cve      = {r["report_url"]: r["value"] for r in overrides if r["action"] == "set_cve_id"}
    set_reporter = {r["report_url"]: r["value"] for r in overrides if r["action"] == "set_reporter"}
    set_related  = {r["report_url"]: r["value"] for r in overrides if r["action"] == "set_related_url"}
    set_notes    = {r["report_url"]: r["note"] for r in overrides if r["action"] == "set_related_url" and r.get("note")}

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
        if url in set_related:  row["related_url"]     = set_related[url];  stats["set_related_url"] += 1
        if url in set_notes:    row["notes"]           = set_notes[url]
        kept.append(row)

    return kept, stats


def apply_overrides() -> Path:
    rows = list(csv.DictReader(CLASSIFIED_CSV.open()))
    for row in rows:
        row.setdefault("notes", "")

    print("Pass 1: PR matching")
    rows, pr_stats = _pass1_pr_matching(rows)
    print(f"  PRs excluded:   {pr_stats['pr_excluded']}")
    print(f"  Issues linked:  {pr_stats['issue_linked']}")

    print("Pass 2: Labelling overrides")
    rows, label_stats = _pass2_labelling(rows)

    commit = git_short_commit()
    output_csv = OUTPUT_DIR / f"classified_human_{commit}.csv"

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
    print(f"  related_url set:  {label_stats['set_related_url']}")
    return output_csv
