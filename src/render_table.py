import csv
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from fetch_cves import cve_json_url

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
DATA_DIR      = Path(__file__).parent.parent / "data"
CVES_CSV      = DATA_DIR / "generated" / "cves.csv"
OUTPUT_DIR    = Path(__file__).parent.parent / "tex" / "generated"
OUTPUT_PATH   = OUTPUT_DIR / "table_cves.tex"
SUMMARY_PATH  = OUTPUT_DIR / "table_summary.tex"

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
    project_key: str   # raw name — used for joining with CSV
    project: str       # LaTeX-escaped name — used in table output
    bug_url: str
    label: str


def build_rows() -> list[Row]:
    rows: list[Row] = []

    with CVES_CSV.open() as f:
        for rec in csv.DictReader(f):
            cve_id      = rec["cve_id"]
            project_key = rec["project"]
            rows.append(Row(
                cve_id=cve_id,
                json_url=cve_json_url(cve_id),
                project_key=project_key,
                project=tex_escape(project_key),
                bug_url=rec["bug_url"],
                label=tex_escape(rec["label"]),
            ))

    return rows


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
    version: str
    bugs: int
    cves: int
    links_found: int
    platform: str


def render_summary(cve_rows: list[Row]) -> None:
    # Count resolved links per project (CVEs that have at least one URL).
    links_per_project: dict[str, set[str]] = {}
    for row in cve_rows:
        if row.bug_url:
            links_per_project.setdefault(row.project_key, set()).add(row.cve_id)

    # Load static project metadata.
    projects_csv = DATA_DIR / "projects.csv"
    summary_rows: list[SummaryRow] = []

    with projects_csv.open() as f:
        for p in csv.DictReader(f):
            key = p["project"]
            display = _DISPLAY_NAME.get(key, key)
            links_found = len(links_per_project.get(key, set()))
            summary_rows.append(SummaryRow(
                display_name=display,
                version=tex_escape(p["version"]),
                bugs=int(p["bugs"]),
                cves=int(p["cves"]),
                links_found=links_found,
                platform=tex_escape(p["platform"]),
            ))

    total_bugs  = sum(r.bugs for r in summary_rows)
    total_cves  = sum(r.cves for r in summary_rows)
    total_links = sum(r.links_found for r in summary_rows)

    env = _jinja_env()
    output = env.get_template("table_summary.tex.j2").render(
        rows=summary_rows,
        total_bugs=total_bugs,
        total_cves=total_cves,
        total_links=total_links,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(output)
    print(f"Written {len(summary_rows)} projects → {SUMMARY_PATH}  "
          f"(links: {total_links}/{total_cves} CVEs)")


def render(total_cves: int) -> None:
    rows = build_rows()

    env = _jinja_env()
    output = env.get_template("table_cves.tex.j2").render(rows=rows, total_cves=total_cves)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(output)
    print(f"Written {len(rows)} rows → {OUTPUT_PATH}")

    render_summary(rows)


if __name__ == "__main__":
    from fetch_cve_list import fetch_cve_list

    cve_ids = fetch_cve_list()
    render(cve_ids)
