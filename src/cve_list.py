import re

from client import github_get

README_URL = "https://raw.githubusercontent.com/seviezhou/Kraken/main/README.md"


def fetch_cve_list() -> list[str]:
    response = github_get(README_URL)
    response.raise_for_status()
    return _parse_cve_list(response.text)


def _parse_cve_list(readme: str) -> list[str]:
    # Find the ## Trophy section
    trophy_match = re.search(r"^## Trophy\b.*$", readme, re.MULTILINE)
    if not trophy_match:
        raise ValueError("Could not find '## Trophy' section in README")

    after_trophy = readme[trophy_match.end():]

    # Extract the first fenced code block after the Trophy header
    block_match = re.search(r"```[^\n]*\n(.*?)```", after_trophy, re.DOTALL)
    if not block_match:
        raise ValueError("Could not find fenced code block under Trophy section")

    block = block_match.group(1)
    cve_ids = re.findall(r"CVE-\d{4}-\d+", block)
    return cve_ids


if __name__ == "__main__":
    cves = fetch_cve_list()
    print(f"Found {len(cves)} CVE IDs")
    for cve in cves:
        print(cve)
