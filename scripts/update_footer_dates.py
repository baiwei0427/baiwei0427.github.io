#!/usr/bin/env python3
"""Update the footer 'Last updated' text in all HTML pages."""

import os
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HTML_PATTERN = re.compile(r"Last updated:\s*[^<\n]+")


def get_last_updated_label() -> str:
    """Return the latest commit date in the repository in 'Month D, YYYY' format."""
    result = subprocess.run(
        [
            "git",
            "log",
            "-1",
            "--date=format-local:%B %d, %Y %H:%M PST",
            "--pretty=format:%ad",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def update_html_files(last_updated: str) -> int:
    updated_files = 0
    for path in REPO_ROOT.glob("*.html"):
        text = path.read_text(encoding="utf-8")
        new_text, count = HTML_PATTERN.subn(f"Last updated: {last_updated}", text)
        if count:
            path.write_text(new_text, encoding="utf-8")
            updated_files += 1
            print(f"Updated {path.name}")
    return updated_files


def main() -> None:
    last_updated = get_last_updated_label()
    updated_files = update_html_files(last_updated)
    print(f"Updated {updated_files} HTML file(s) with last commit date {last_updated}.")


if __name__ == "__main__":
    main()
