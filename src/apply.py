"""
Apply data/overrides.yaml to output/classified_auto.csv
→ output/classified_human_{commit}.csv

Run via: python main.py apply
"""

import csv
import yaml
from pathlib import Path

from client import git_short_commit

ROOT           = Path(__file__).parent.parent
CLASSIFIED_CSV = ROOT / "output" / "classified_auto.csv"
OVERRIDES_YAML = ROOT / "data" / "overrides.yaml"
OUTPUT_DIR     = ROOT / "output"

FIELDS = ["project", "report_url", "where_url_found", "reporter", "cve_id", "related_url"]

ACTIONS = {"exclude", "set_label", "set_cve_id", "set_reporter", "set_related_url"}


def apply_overrides() -> Path:
    overrides = yaml.safe_load(OVERRIDES_YAML.read_text())

    unknown_actions = {r["action"] for r in overrides} - ACTIONS
    if unknown_actions:
        raise ValueError(f"Unknown actions in overrides.yaml: {unknown_actions}")

    excludes     = {r["report_url"] for r in overrides if r["action"] == "exclude"}
    set_label    = {r["report_url"]: r["value"] for r in overrides if r["action"] == "set_label"}
    set_cve      = {r["report_url"]: r["value"] for r in overrides if r["action"] == "set_cve_id"}
    set_reporter = {r["report_url"]: r["value"] for r in overrides if r["action"] == "set_reporter"}
    set_related  = {r["report_url"]: r["value"] for r in overrides if r["action"] == "set_related_url"}

    rows = list(csv.DictReader(CLASSIFIED_CSV.open()))
    kept = []
    stats = {a: 0 for a in ACTIONS}

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
        kept.append(row)

    commit = git_short_commit()
    output_csv = OUTPUT_DIR / f"classified_human_{commit}.csv"

    with output_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(kept)

    counts = {v: sum(1 for r in kept if r["where_url_found"] == v)
              for v in ("paper_artifact", "activity_history", "unknown")}
    print(f"Written {len(kept)} rows → {output_csv}")
    print(f"  paper_artifact:   {counts['paper_artifact']}")
    print(f"  activity_history: {counts['activity_history']}")
    print(f"  unknown:          {counts['unknown']}")
    print(f"  excluded:         {stats['exclude']}")
    print(f"  label updated:    {stats['set_label']}")
    print(f"  cve_id set:       {stats['set_cve_id']}")
    print(f"  reporter set:     {stats['set_reporter']}")
    print(f"  related_url set:  {stats['set_related_url']}")
    return output_csv
