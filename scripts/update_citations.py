#!/usr/bin/env python3
"""Fetch total citation count from Google Scholar and save to data/scholar.json."""

import json
import os
import sys
import time
import random

import requests
from bs4 import BeautifulSoup

SCHOLAR_URL = "https://scholar.google.com.hk/citations?user=2zjLkpcAAAAJ"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "scholar.json")
MAX_RETRIES = 3
RETRY_BASE_DELAY = 5  # seconds

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_citation_count() -> int:
    """Fetch total citation count from Google Scholar profile page."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(SCHOLAR_URL, headers=HEADERS, timeout=30)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # Citation count is in the table with id "gsc_rsb_st".
            # The first row's second cell contains the "All" citation count.
            table = soup.find("table", id="gsc_rsb_st")
            if table is None:
                raise ValueError("Could not find citation stats table on page")

            rows = table.find_all("tr")
            if len(rows) < 2:
                raise ValueError("Unexpected table structure")

            cells = rows[1].find_all("td")
            if len(cells) < 2:
                raise ValueError("Unexpected row structure")

            count = int(cells[1].text.strip())
            return count

        except Exception as exc:
            print(f"Attempt {attempt}/{MAX_RETRIES} failed: {exc}", file=sys.stderr)
            if attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * attempt + random.uniform(0, 2)
                print(f"Retrying in {delay:.1f}s ...", file=sys.stderr)
                time.sleep(delay)

    # All retries exhausted — exit without modifying the file
    print("All retries exhausted. Exiting without updating scholar.json.", file=sys.stderr)
    sys.exit(1)


def main():
    count = fetch_citation_count()
    today = time.strftime("%Y-%m-%d")

    data = {
        "citation_count": count,
        "updated": today,
        "status": "ok",
    }

    output = os.path.normpath(OUTPUT_PATH)
    os.makedirs(os.path.dirname(output), exist_ok=True)

    with open(output, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    print(f"Updated scholar.json: {count} citations as of {today}")


if __name__ == "__main__":
    main()
