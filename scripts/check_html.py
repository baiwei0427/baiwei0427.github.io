#!/usr/bin/env python3

import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup


REPO_ROOT = Path(__file__).resolve().parents[1]
HTML_FILES = sorted(REPO_ROOT.rglob("*.html"))


def is_external_or_special(url: str) -> bool:
    if not url or url.startswith("#"):
        return True
    return bool(re.match(r"^(?:[a-z][a-z0-9+.-]*:|//)", url))


def resolve_target(path: Path, url: str) -> Path | None:
    clean = url.split("#", 1)[0].split("?", 1)[0]
    if not clean or clean.startswith("/"):
        target = (REPO_ROOT / clean.lstrip("/")).resolve()
    else:
        target = (path.parent / clean).resolve()

    try:
        target.relative_to(REPO_ROOT)
    except ValueError:
        return None

    return target


def main() -> int:
    errors = []

    for html_file in HTML_FILES:
        try:
            text = html_file.read_text(encoding="utf-8")
            BeautifulSoup(text, "html5lib")
        except Exception as exc:
            errors.append(f"{html_file.relative_to(REPO_ROOT)}: HTML parse error - {exc}")
            continue

        soup = BeautifulSoup(text, "html5lib")
        for tag in soup.find_all(True):
            for attr in ("href", "src"):
                value = tag.get(attr)
                if not value or is_external_or_special(value):
                    continue

                target = resolve_target(html_file, value)
                if target is None:
                    continue

                if not target.exists():
                    errors.append(f"{html_file.relative_to(REPO_ROOT)}: missing local link target '{value}'")

    if errors:
        print("HTML validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Checked {len(HTML_FILES)} HTML file(s) successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
