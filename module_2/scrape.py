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
REQUEST_DELAY = 1.0   # seconds between page requests (polite scraping)


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
    if re.search(r"\bmasters?\b|\bm\.s\.?\b|\bm\.a\.?\b|\bmeng\b|\bmba\b|\bm\.eng\.?\b|\bmfa\b", t):
        return "Masters"
    return None


def _parse_entry(row) -> dict | None:
    """
    Extract all available fields from a single rendered table row.
    GradCafe column order: University | Program | Degree | Date Added | Status | Comments
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

    texts = [c.get_text(separator=" ", strip=True) for c in cells]

    # Entry URL — look for a link pointing to a result page
    entry_url = None
    for a in row.find_all("a", href=True):
        href = a["href"]
        if "/result/" in href or "/survey/" in href:
            entry_url = BASE_URL + href if href.startswith("/") else href
            break

    # --- Positional extraction based on observed GradCafe column order ---
    # Actual structure: University | Program+Degree | Date Added | Status | Comments
    university = texts[0] if len(texts) > 0 else None

    # Cell 1 combines program name and degree (e.g. "Bioinformatics Masters")
    cell1 = texts[1] if len(texts) > 1 else ""
    degree = _normalize_degree(cell1)
    # Strip the degree keyword to get the clean program name
    program_name = re.sub(
        r"\b(PhD|Ph\.D\.?|Masters?|M\.S\.?|M\.A\.?|M\.Eng\.?|MBA|MFA|MEng|Doctoral)\b",
        "", cell1, flags=re.I,
    ).strip().strip(",").strip()

    date_added = texts[2] if len(texts) > 2 else None

    # Status cell often includes the decision date (e.g. "Rejected on May 31")
    status_raw = texts[3] if len(texts) > 3 else ""
    status = _normalize_status(status_raw)

    # Pull accept/reject date out of the status string
    accept_reject_date = None
    m = re.search(r"(?:on|via email on|via)\s+(.+)", status_raw, re.I)
    if m:
        accept_reject_date = m.group(1).strip()

    # Comments — last cell; filter out placeholder GradCafe link text
    comments_raw = texts[4] if len(texts) > 4 else None
    comments = None
    if comments_raw and not re.match(r"^\d*\s*total comments?$", comments_raw, re.I):
        comments = comments_raw

    # Season / term — scan all cells
    term = None
    for text in texts:
        m = re.search(r"\b(Fall|Spring|Summer|Winter)\s+20\d{2}\b", text, re.I)
        if m:
            term = m.group(0)
            break

    # GPA, GRE — scan all cells (may appear in any column depending on entry)
    gpa = None
    gre_total = gre_v = gre_aw = None
    applicant_type = None

    for text in texts:
        if not gpa and re.search(r"\bGPA\b|\b[0-3]\.\d{2}\b|4\.0\b", text, re.I):
            gpa = _extract_gpa(text)
        if not gre_total and re.search(r"\bGRE\b", text, re.I):
            gre_total, gre_v, gre_aw = _extract_gre(text)
        if not applicant_type:
            if re.search(r"\binternational\b", text, re.I):
                applicant_type = "International"
            elif re.search(r"\bamerican\b|\bdomestic\b|\bU\.?S\.?\b", text, re.I):
                applicant_type = "American"

    # Skip rows with no meaningful content
    if not university and not entry_url:
        return None

    # Combine program + university for LLM standardization (matches sample_data.json format)
    program_combined = (
        f"{program_name}, {university}" if program_name and university else (program_name or university)
    )

    return {
        "program": program_combined,        # combined field for LLM to split
        "university_raw": university,        # raw university column
        "program_raw": program_name,         # raw program column
        "status": status,
        "accept_reject_date": accept_reject_date,
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
        "raw_text": raw_text,
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
    start_page: int = 1,
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

    # Resume from existing data if present
    all_entries: list[dict] = []
    if start_page > 1:
        try:
            all_entries = load_data(output_file)
            print(f"Resuming from page {start_page} with {len(all_entries)} existing entries.")
        except FileNotFoundError:
            pass

    driver = _setup_driver()
    page = start_page
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
                print(f"[Page {page}] +{len(entries)} entries -> total {len(all_entries)}")

            # Checkpoint save every 50 pages
            if page % 50 == 0:
                save_data(all_entries, output_file)
                print(f"  >> Checkpoint: {len(all_entries)} entries written to {output_file}")

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
    import sys
    # Pass a page number as argument to resume: python scrape.py 1057
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    scrape_data(start_page=start)
