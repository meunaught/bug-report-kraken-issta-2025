"""
Build a raw per-project context file for projects that fail verification.

Driven by `python main.py verify`: for each project that fails a rule, lay out
everything for its reports — issue/SF JSON for the clean report body and fields,
issue HTML for the rest of the page (comments, maintainer notes) — as one
readable markdown file at cache/review/{project}.md.

No analysis is applied: no signature extraction, no duplicate detection, no
labelling hints. The file is raw evidence for the AI to read and reason over
when drafting data/static/patch.yaml. Issue HTML is fetched on demand and
cached; everything else is read from the existing cache.
"""

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import httpx

from client import ISSUE_JSON, PR_JSON, HTML_ISSUE, ROOT, url_slug, git_short_commit

PROJECTS_CSV = ROOT / "data" / "static" / "projects.csv"


def _classified_csv() -> Path:
    return ROOT / "output" / f"classified_{git_short_commit()}.csv"
CONTEXT_DIR    = ROOT / "cache" / "review"


# ── cache access ──────────────────────────────────────────────────────────────

def _load_json(url: str) -> dict | None:
    for base in (ISSUE_JSON, PR_JSON):
        path = base / url_slug(url)
        if path.exists():
            try:
                return json.loads(path.read_text())
            except json.JSONDecodeError:
                return None
    return None


def _html_text(url: str) -> str:
    """Plain-text of the issue page (fetched + cached if missing, tags stripped)."""
    path = HTML_ISSUE / url_slug(url, ".html")
    if not path.exists():
        try:
            r = httpx.get(url, follow_redirects=True, timeout=15,
                          headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(r.text, encoding="utf-8")
        except Exception:
            return ""
    raw = path.read_text(encoding="utf-8", errors="replace")
    raw = re.sub(r"(?is)<(script|style|svg|head|nav|footer)\b.*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    raw = re.sub(r"&[a-z#0-9]+;", " ", raw)
    raw = re.sub(r"[ \t]+", " ", raw)
    return re.sub(r"\n[ \t]*\n\s*\n+", "\n\n", raw).strip()


# ── report rendering (verbatim) ───────────────────────────────────────────────

def _render_report(row: dict) -> str:
    url   = row["report_url"]
    data  = _load_json(url)
    short = url.rstrip("/").split("/")[-1]

    if data and "ticket" in data:                       # SourceForge
        t = data["ticket"]
        title = t.get("summary", "")
        body  = t.get("description", "") or ""
        posts = t.get("discussion_thread", {}).get("posts", [])
        comments = "\n\n".join(
            f"[{p.get('author','')}] {(p.get('text','') or '').strip()}"
            for p in posts if (p.get("text") or "").strip()
        )
    elif data:                                           # GitHub
        title    = data.get("title", "")
        body     = data.get("body", "") or ""
        comments = ""                                    # comments live in the HTML page
    else:
        title = body = comments = ""

    parts = [
        f"## {short}  ·  {row.get('reporter') or '?'}  ·  "
        f"{(row.get('date') or '')[:10] or '?'}  ·  cve: {row.get('cve_id') or '—'}  ·  "
        f"label: {row['where_url_found'] or '—'}",
        f"<{url}>",
        f"**title:** {title or '—'}",
        "\n**body:**\n~~~\n" + (body.strip() or "(no body cached)") + "\n~~~",
    ]
    if comments:
        parts.append("\n**comments:**\n~~~\n" + comments.strip() + "\n~~~")

    page = _html_text(url)
    if page:
        parts.append("\n<details><summary>full cached page text</summary>\n\n~~~\n"
                     + page + "\n~~~\n</details>")

    return "\n".join(parts)


def build_context(project: str, rows: list[dict], paper: dict) -> Path:
    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    p = paper.get(project, {})
    found_bugs = sum(1 for r in rows if r["where_url_found"] == "paper_artifact")
    found_cves = len({r["cve_id"] for r in rows if r.get("cve_id")})

    header = (
        f"# {project} — paper: {p.get('bugs','?')} bugs / {p.get('cves','?')} CVEs   |   "
        f"found: {len(rows)} reports / {found_cves} CVEs (paper_artifact={found_bugs})\n"
    )
    blocks = [_render_report(r) for r in sorted(rows, key=lambda r: r["report_url"])]

    out = CONTEXT_DIR / f"{project}.md"
    out.write_text(header + "\n" + "\n\n---\n\n".join(blocks) + "\n")
    return out


def generate_context_for(projects: list[str]) -> list[Path]:
    """Build cache/review/{project}.md for each named project. Called by verify."""
    if not projects:
        return []
    rows = list(csv.DictReader(_classified_csv().open()))
    paper = {r["project"]: {"bugs": int(r["bugs"]), "cves": int(r["cves"])}
             for r in csv.DictReader(PROJECTS_CSV.open())}

    want = set(projects)
    by_project: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row["project"] in want:
            by_project[row["project"]].append(row)

    written: list[Path] = []
    for project in sorted(want):
        proj_rows = by_project.get(project, [])
        if not proj_rows:
            continue
        out = build_context(project, proj_rows, paper)
        written.append(out)
        print(f"  context → {out.relative_to(ROOT)}  ({len(proj_rows)} reports)")
    return written


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    generate_context_for(sys.argv[1:])
