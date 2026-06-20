import csv
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from fetch_cves import cve_json_url

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
DATA_DIR      = Path(__file__).parent.parent / "data"
JOINED_CSV    = DATA_DIR / "generated" / "joined.csv"
PROJECTS_CSV  = DATA_DIR / "projects.csv"
OUTPUT_DIR    = Path(__file__).parent.parent / "tex" / "generated"
OUTPUT_PATH   = OUTPUT_DIR / "table_cves.tex"
SUMMARY_PATH  = OUTPUT_DIR / "table_summary.tex"
ORPHAN_PATH      = OUTPUT_DIR / "table_orphan_cves.tex"
COMPARISON_PATH  = OUTPUT_DIR / "table_comparison.tex"

# Per-project bug and CVE counts as reported in the KRAKEN supplement material (Table 1).
# Key: our internal project key; value: (paper_bugs, paper_cves).
_PAPER_STATS: dict[str, tuple[int, int]] = {
    "advancecomp":   (3,  0),
    "asn1c":         (4,  0),
    "bento4":        (6,  4),
    "cpp-peglib":    (2,  2),
    "dmg2img":       (7,  2),
    "faad2":         (6,  6),
    "fast_ber":      (1,  1),
    "faust":         (1,  1),
    "ffmpeg":        (3,  1),
    "fig2dev":       (1,  1),
    "giflib":        (1,  1),
    "gocr":          (4,  3),
    "gpac":          (12, 9),
    "gravity":       (7,  5),
    "hcxtools":      (1,  1),
    "heif":          (4,  3),
    "jhead":         (2,  0),
    "json-c":        (1,  1),
    "libelfin":      (1,  1),
    "libgig":        (1,  1),
    "libiff":        (2,  1),
    "libjpeg":       (19, 7),
    "libmaxminddb":  (1,  1),
    "libnsfdb":      (3,  0),
    "libraw":        (3,  1),
    "libredwg":      (12, 9),
    "libslax":       (4,  4),
    "libxsmm":       (5,  2),
    "lief":          (1,  1),
    "nasm":          (2,  0),
    "ncurses":       (2,  1),
    "pbrt-v3":       (1,  1),
    "pdftools":      (6,  6),
    "retdec":        (1,  1),
    "sela":          (9,  9),
    "sox":           (3,  0),
    "swftools":      (50, 32),
}

# Display names that differ from the lowercase project key used internally.
_DISPLAY_NAME: dict[str, str] = {
    "bento4":      "Bento4",
    "cpp-peglib":  "cpp-peglib",
    "fast_ber":    r"fast\_ber",
    "json-c":      "json-c",
}

# Characters that must be escaped in LaTeX text (not inside \href{} URLs).
_TEX_ESCAPE = str.maketrans({"_": r"\_", "#": r"\#", "&": r"\&", "%": r"\%"})


def tex_escape(s: str) -> str:
    return s.translate(_TEX_ESCAPE)


@dataclass
class Row:
    cve_id: str
    json_url: str
    project_key: str   # raw name — used for grouping
    display_name: str  # LaTeX-formatted name — used in table output
    bug_url: str
    label: str


def build_rows() -> list[Row]:
    rows: list[Row] = []

    with JOINED_CSV.open() as f:
        for rec in csv.DictReader(f):
            cve_id      = rec["cve_id"]
            project_key = rec["project"]
            display     = _DISPLAY_NAME.get(project_key) or tex_escape(project_key)
            rows.append(Row(
                cve_id=cve_id,
                json_url=cve_json_url(cve_id) if cve_id else "",
                project_key=project_key,
                display_name=display,
                bug_url=rec["bug_url"],
                label=tex_escape(rec["label"]),
            ))

    return rows


def group_rows(rows: list[Row]) -> list[tuple[str, list[Row]]]:
    """Return [(display_name, [Row, ...]), ...] sorted alphabetically by project."""
    groups: dict[str, list[Row]] = {}
    for row in rows:
        groups.setdefault(row.project_key, []).append(row)
    return [
        (rows_list[0].display_name, rows_list)
        for _, rows_list in sorted(groups.items())
    ]


def _jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )


@dataclass
class SummaryRow:
    display_name: str
    bugs_filed: int
    with_cve: int
    without_cve: int
    platform: str


def render_summary() -> None:
    # Load platform info from static projects.csv (fallback: GitHub Issues).
    platform_map: dict[str, str] = {}
    with PROJECTS_CSV.open() as f:
        for p in csv.DictReader(f):
            platform_map[p["project"]] = p["platform"]

    # Aggregate joined.csv: per project, count unique bug_urls with/without CVE.
    bugs_with: dict[str, set[str]]    = {}
    bugs_without: dict[str, set[str]] = {}

    with JOINED_CSV.open() as f:
        for r in csv.DictReader(f):
            proj = r["project"]
            url  = r["bug_url"]
            if r["cve_id"]:
                bugs_with.setdefault(proj, set()).add(url)
            else:
                bugs_without.setdefault(proj, set()).add(url)

    all_projects = sorted(
        bugs_with.keys() | bugs_without.keys(),
        key=lambda p: _DISPLAY_NAME.get(p, p).lower(),
    )

    summary_rows: list[SummaryRow] = []
    for proj in all_projects:
        with_set    = bugs_with.get(proj, set())
        without_set = bugs_without.get(proj, set())
        # A bug that matched a CVE should not also count as without-CVE.
        without_set -= with_set
        # _DISPLAY_NAME values are already LaTeX-formatted; only escape raw keys.
        display_name = _DISPLAY_NAME.get(proj) or tex_escape(proj)
        summary_rows.append(SummaryRow(
            display_name=display_name,
            bugs_filed=len(with_set) + len(without_set),
            with_cve=len(with_set),
            without_cve=len(without_set),
            platform=tex_escape(platform_map.get(proj, "GitHub Issues")),
        ))

    total_filed   = sum(r.bugs_filed  for r in summary_rows)
    total_with    = sum(r.with_cve    for r in summary_rows)
    total_without = sum(r.without_cve for r in summary_rows)

    env = _jinja_env()
    output = env.get_template("table_summary.tex.j2").render(
        rows=summary_rows,
        total_filed=total_filed,
        total_with=total_with,
        total_without=total_without,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(output)
    print(f"Written {len(summary_rows)} projects → {SUMMARY_PATH}")


@dataclass
class OrphanRow:
    cve_id: str
    json_url: str
    project: str
    display_name: str
    bug_url: str
    label: str


def compute_orphans(cve_ids: list[str], joined_rows: list[Row]) -> list[OrphanRow]:
    """CVE-referenced URLs that did not match any author-search bug."""
    from extract_refs import extract_refs
    from build_joined_csv import _normalize

    joined_urls = {_normalize(r.bug_url) for r in joined_rows if r.cve_id}

    orphans: list[OrphanRow] = []
    seen: set[str] = set()
    for cve_id in cve_ids:
        for ref in extract_refs(cve_id):
            key = _normalize(ref.url)
            if key not in joined_urls and key not in seen:
                seen.add(key)
                # infer project from URL
                import re
                m = re.search(r"github\.com/[^/]+/([^/]+)", ref.url)
                proj = m.group(1).lower() if m else ""
                display = _DISPLAY_NAME.get(proj) or tex_escape(proj) if proj else "ncurses"
                # For GNU mailing list posts include the year-month from the URL as the label.
                label = ref.label
                ml_m = re.search(r"/(\d{4}-\d{2})/", ref.url)
                if ml_m:
                    label = f"ML Post ({ml_m.group(1)})"
                orphans.append(OrphanRow(
                    cve_id=cve_id,
                    json_url=cve_json_url(cve_id),
                    project=proj or "ncurses",
                    display_name=display,
                    bug_url=ref.url,
                    label=tex_escape(label),
                ))
    orphans.sort(key=lambda r: (r.project, r.cve_id))
    return orphans


@dataclass
class ComparisonRow:
    display_name: str
    paper_bugs: int
    found_bugs: int
    paper_cves: int
    found_cves: int


def render_comparison(rows: list[Row]) -> None:
    # Per-project counts from our data.
    found_bugs: dict[str, set[str]] = {}
    found_cves: dict[str, set[str]] = {}
    for r in rows:
        found_bugs.setdefault(r.project_key, set()).add(r.bug_url)
        if r.cve_id:
            found_cves.setdefault(r.project_key, set()).add(r.cve_id)

    comp_rows: list[ComparisonRow] = []
    for proj, (paper_bugs, paper_cves) in sorted(_PAPER_STATS.items()):
        display = _DISPLAY_NAME.get(proj) or tex_escape(proj)
        comp_rows.append(ComparisonRow(
            display_name=display,
            paper_bugs=paper_bugs,
            found_bugs=len(found_bugs.get(proj, set())),
            paper_cves=paper_cves,
            found_cves=len(found_cves.get(proj, set())),
        ))

    env = _jinja_env()
    output = env.get_template("table_comparison.tex.j2").render(rows=comp_rows)
    COMPARISON_PATH.write_text(output)
    print(f"Written {len(comp_rows)} comparison rows → {COMPARISON_PATH}")


def render_orphans(cve_ids: list[str], joined_rows: list[Row]) -> None:
    orphans = compute_orphans(cve_ids, joined_rows)
    env = _jinja_env()
    output = env.get_template("table_orphan_cves.tex.j2").render(orphans=orphans)
    ORPHAN_PATH.write_text(output)
    print(f"Written {len(orphans)} orphan CVE rows → {ORPHAN_PATH}")


def render(cve_ids: list[str]) -> None:
    from build_joined_csv import build_joined_csv
    build_joined_csv(cve_ids)

    rows = build_rows()
    total_bugs = len({r.bug_url for r in rows})
    total_with_cve = sum(1 for r in rows if r.cve_id)
    groups = group_rows(rows)

    env = _jinja_env()
    output = env.get_template("table_cves.tex.j2").render(
        groups=groups,
        total_cves=total_with_cve,
        total_bugs=total_bugs,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(output)
    print(f"Written {len(rows)} rows → {OUTPUT_PATH}")

    render_summary()
    render_orphans(cve_ids, rows)
    render_comparison(rows)


if __name__ == "__main__":
    from fetch_cve_list import fetch_cve_list

    cve_ids = fetch_cve_list()
    render(cve_ids)
