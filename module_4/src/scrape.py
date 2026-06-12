"""
scrape.py
Grad Cafe web scraper — public API for module_4.

Public API
----------
scrape_gradcafe() -> list[dict]
    Scrape the Grad Cafe survey pages and return records as a list of dicts.
    In tests this function is replaced via create_app(scraper_fn=...).

Implementation uses Selenium (headless Chrome) + BeautifulSoup.
Requires: selenium, beautifulsoup4, chromedriver on PATH.
"""

import json
import subprocess
from pathlib import Path


def scrape_gradcafe() -> list[dict]:
    """
    Scrape Grad Cafe for applicant records.

    Returns
    -------
    list[dict]
        Each dict contains keys: program, comments, date_added, url, status,
        term, US/International, GPA, GRE, GRE_V, GRE_AW, Degree,
        llm-generated-program, llm-generated-university.

    Raises
    ------
    RuntimeError
        If the scrape script exits with a non-zero status.
    """
    module2_dir = Path(__file__).parent.parent.parent / "module_2"
    scrape_script = module2_dir / "scrape.py"
    output_file = module2_dir / "applicant_data.json"

    result = subprocess.run(
        ["python", str(scrape_script)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Scraper failed:\n{result.stderr}")

    with open(output_file, "r", encoding="utf-8") as f:
        return json.load(f)
