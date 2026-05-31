"""
scrape.py
Grad Cafe web scraper: urllib (URL management) + Selenium (rendering) + BeautifulSoup (parsing).
"""

import json
import re
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# ── Constants ──────────────────────────────────────────────────────────────────
BASE_URL = "https://www.thegradcafe.com"
SURVEY_URL = f"{BASE_URL}/survey/"
ROBOTS_URL = f"{BASE_URL}/robots.txt"
OUTPUT_FILE = "applicant_data.json"
TARGET_ENTRIES = 30_000
PER_PAGE = 25
REQUEST_DELAY = 2.5   # seconds between page requests (polite scraping)


# ── robots.txt ─────────────────────────────────────────────────────────────────
def check_robots_txt() -> tuple[bool, str]:
    """
    Fetch robots.txt and verify that /survey/ is allowed for all agents.
    Returns (is_allowed, raw_robots_txt_content).
    """
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(ROBOTS_URL)
    rp.read()

    with urllib.request.urlopen(ROBOTS_URL) as resp:
        raw = resp.read().decode("utf-8")

    allowed = rp.can_fetch("*", SURVEY_URL)
    return allowed, raw


# ── URL management ─────────────────────────────────────────────────────────────
def build_url(page: int, per_page: int = PER_PAGE) -> str:
    """Construct a paginated Grad Cafe survey URL using urllib.parse."""
    params = urllib.parse.urlencode({"q": "", "per_page": per_page, "page": page})
    return f"{SURVEY_URL}?{params}"


def inspect_url(url: str) -> dict:
    """Break a URL into components for inspection/debugging."""
    parsed = urllib.parse.urlparse(url)
    return {
        "scheme": parsed.scheme,
        "netloc": parsed.netloc,
        "path": parsed.path,
        "query_params": dict(urllib.parse.parse_qsl(parsed.query)),
    }


# ── WebDriver ──────────────────────────────────────────────────────────────────
def _setup_driver() -> webdriver.Chrome:
    """Configure and return a headless Chrome WebDriver."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    # Realistic user-agent to avoid immediate bot detection
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(options=options)


# ── Parsing helpers ────────────────────────────────────────────────────────────
def _extract_gpa(text: str) -> str | None:
    """Pull a GPA value from raw text (e.g. 'GPA 3.88' → '3.88')."""
    m = re.search(r"(?:GPA\s*)?([0-3]\.\d{1,2}|4\.0{1,2})", text, re.I)
    return m.group(1) if m else None


def _extract_gre(text: str) -> tuple[str | None, str | None, str | None]:
    """Extract GRE total, verbal (V), and AW scores from raw text."""
    gre_total = gre_v = gre_aw = None

    m = re.search(r"\bGRE[:\s]*(\d{3,4})\b", text, re.I)
    if m:
        gre_total = m.group(1)

    m = re.search(r"\bV(?:erbal)?[:\s]*(\d{2,3})\b", text, re.I)
    if m:
        gre_v = m.group(1)

    m = re.search(r"\bAW[:\s]*([\d.]+)\b", text, re.I)
    if m:
        gre_aw = m.group(1)

    return gre_total, gre_v, gre_aw


def _normalize_status(text: str) -> str | None:
    """Map raw decision text to a canonical status label."""
    t = (text or "").lower()
    if "accept" in t:
        return "Accepted"
    if "reject" in t:
        return "Rejected"
    if "waitlist" in t or "wait list" in t or "wait-list" in t:
        return "Wait listed"
    if "interview" in t:
        return "Interview"
    return text.strip() if text.strip() else None


def _normalize_degree(text: str) -> str | None:
    """Normalize degree strings to 'Masters' or 'PhD'."""
    t = (text or "").lower()
    if re.search(r"\bphd\b|\bph\.d\b|\bdoctoral?\b", t):
        return "PhD"
    if re.search(r"\bmaster\b|\bm\.s\b|\bm\.a\b|\bmeng\b|\bmba\b|\bm\.eng\b|\bmfa\b", t):
        return "Masters"
    return None


def _parse_entry(row) -> dict | None:
    """
    Extract all available fields from a single rendered table row.
    Returns a structured dict or None if the row is a header or empty.
    """
    # Skip header rows (contain <th> elements)
    if row.find("th"):
        return None

    cells = row.find_all("td")
    if not cells or len(cells) < 2:
        return None

    raw_text = row.get_text(separator=" | ", strip=True)
    if not raw_text:
        return None

    # Build a flat list of cell texts for positional access
    texts = [c.get_text(separator=" ", strip=True) for c in cells]

    # Entry URL — look for a link pointing to a result page
    entry_url = None
    for a in row.find_all("a", href=True):
        href = a["href"]
        if "/result/" in href or "/survey/" in href:
            entry_url = BASE_URL + href if href.startswith("/") else href
            break

    # --- Core fields (positional, typical GradCafe column order) ---
    # Column 0: Institution / Program (often combined as "Program, University")
    program = texts[0] if texts else None

    # Column 1: Decision/Status
    status_raw = texts[1] if len(texts) > 1 else ""
    status = _normalize_status(status_raw)

    # Column 2+: scan remaining cells for term, GPA, GRE, comments, etc.
    term = None
    gpa = None
    gre_total = gre_v = gre_aw = None
    degree = None
    applicant_type = None
    comments = None
    date_added = None

    for text in texts[2:]:
        # Season / term
        if not term:
            m = re.search(r"\b(Fall|Spring|Summer|Winter)\s+20\d{2}\b", text, re.I)
            if m:
                term = m.group(0)

        # Date added
        if not date_added:
            m = re.search(
                r"\b(Added on .+?\d{4}|\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{1,2},?\s+\d{4}|\d{4}-\d{2}-\d{2})\b",
                text,
            )
            if m:
                date_added = m.group(0)

        # GPA
        if not gpa and re.search(r"\bGPA\b|\b\d\.\d{2}\b", text, re.I):
            gpa = _extract_gpa(text)

        # GRE
        if not gre_total and re.search(r"\bGRE\b", text, re.I):
            gre_total, gre_v, gre_aw = _extract_gre(text)

        # Degree
        if not degree:
            degree = _normalize_degree(text)

        # Applicant type
        if not applicant_type:
            if re.search(r"\binternational\b", text, re.I):
                applicant_type = "International"
            elif re.search(r"\bamerican\b|\bdomestic\b|\bU\.?S\.?\b", text, re.I):
                applicant_type = "American"

    # Comments are typically in the last cell if not already used
    if len(texts) > 3:
        comments = texts[-1]

    # Skip rows that yield nothing useful
    if not program and not entry_url:
        return None

    return {
        "program": program,
        "status": status,
        "term": term,
        "date_added": date_added,
        "url": entry_url,
        "Degree": degree,
        "US/International": applicant_type,
        "GPA": gpa,
        "GRE": gre_total,
        "GRE_V": gre_v,
        "GRE_AW": gre_aw,
        "comments": comments,
        "raw_text": raw_text,  # preserved for traceability
    }


def _parse_page(html: str) -> list[dict]:
    """Parse all applicant entries from a fully rendered page."""
    soup = BeautifulSoup(html, "lxml")
    entries = []

    # Try progressively broader selectors to handle layout variations
    rows = (
        soup.select("table tbody tr")
        or soup.select("table tr")
        or soup.select("[class*='row']")
        or soup.select("[class*='result']")
    )

    for row in rows:
        entry = _parse_entry(row)
        if entry:
            entries.append(entry)

    return entries


# ── Main scraping loop ─────────────────────────────────────────────────────────
def scrape_data(
    target: int = TARGET_ENTRIES,
    delay: float = REQUEST_DELAY,
    output_file: str = OUTPUT_FILE,
) -> list[dict]:
    """
    Iterates paginated Grad Cafe survey pages using Selenium + BeautifulSoup.
    Saves incremental progress every 50 pages.
    Stops if the site blocks, rate-limits, or returns empty pages.
    """
    # 1. Verify robots.txt before scraping anything
    allowed, _ = check_robots_txt()
    if not allowed:
        raise PermissionError("robots.txt disallows scraping /survey/. Aborting.")
    print("robots.txt check passed — /survey/ is permitted.")

    all_entries: list[dict] = []
    driver = _setup_driver()
    page = 1
    consecutive_empty = 0

    try:
        while len(all_entries) < target:
            url = build_url(page)
            print(f"[Page {page}] {url}  |  total so far: {len(all_entries)}")

            try:
                driver.get(url)
                # Wait up to 20 s for any table row or result element to appear
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "table tr, [class*='row'], [class*='result']")
                    )
                )
                time.sleep(1.0)  # allow JS hydration to finish
            except TimeoutException:
                print(f"[Page {page}] Timeout — site may be rate-limiting. Stopping.")
                break
            except WebDriverException as exc:
                print(f"[Page {page}] Driver error: {exc}. Stopping.")
                break

            entries = _parse_page(driver.page_source)

            if not entries:
                consecutive_empty += 1
                print(f"[Page {page}] No entries parsed (empty #{consecutive_empty}).")
                if consecutive_empty >= 3:
                    print("3 consecutive empty pages — assuming end of data. Stopping.")
                    break
            else:
                consecutive_empty = 0
                all_entries.extend(entries)
                print(f"[Page {page}] +{len(entries)} entries  →  total {len(all_entries)}")

            # Checkpoint save every 50 pages
            if page % 50 == 0:
                save_data(all_entries, output_file)
                print(f"  ↳ Checkpoint: {len(all_entries)} entries written to {output_file}")

            page += 1
            time.sleep(delay)  # polite delay between requests

    finally:
        driver.quit()
        save_data(all_entries, output_file)
        print(f"\nScraping complete. {len(all_entries)} entries saved to {output_file}.")

    return all_entries


# ── Persistence ────────────────────────────────────────────────────────────────
def save_data(data: list[dict], filename: str = OUTPUT_FILE) -> None:
    """Serialize applicant list to a JSON file."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_data(filename: str = OUTPUT_FILE) -> list[dict]:
    """Deserialize applicant list from a JSON file."""
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    scrape_data()
