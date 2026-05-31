Name: Syrreal Watson | JHED: lwatso28
Module: Module 2 — Web Scraping Grad Cafe
Due Date: (see Canvas)

================================================================================
ROBOTS.TXT COMPLIANCE
================================================================================
Before any scraping begins, scrape.py calls check_robots_txt(), which uses
urllib.robotparser to fetch https://www.thegradcafe.com/robots.txt and verify
that the /survey/ path is allowed for all user agents (*).

A screenshot of the robots.txt page is saved as screenshot.jpg in this folder.

The scraper complies with robots.txt by:
  - Only accessing paths explicitly permitted (/survey/)
  - Using polite 2.5-second delays between every page request
  - Stopping immediately if the site returns an error, timeout, or empty pages
  - Never bypassing logins, CAPTCHAs, or rate limits

================================================================================
APPROACH
================================================================================
This solution uses a hybrid urllib + Selenium + BeautifulSoup workflow:

1. urllib.robotparser — checks robots.txt before any request is made.
2. urllib.parse      — constructs and inspects all Grad Cafe URLs.
3. Selenium (Chrome) — loads each paginated survey page in a headless browser
                       so that JavaScript-rendered content is fully visible.
4. BeautifulSoup     — parses the rendered HTML to extract applicant rows.

Scraping (scrape.py):
  - build_url(page) constructs: https://www.thegradcafe.com/survey/?q=&per_page=25&page=N
  - Selenium waits for table rows to appear before parsing (explicit waits).
  - Each row is parsed by _parse_entry() which extracts all available fields.
  - Progress is saved to applicant_data.json every 50 pages.
  - Scraping stops after 3 consecutive empty pages or if the site blocks.

Cleaning (clean.py):
  - Removes HTML tags and entities from all text fields.
  - Validates GPA (0.00–4.00), GRE total (260–340), GRE V (130–170), AW (0.0–6.0).
  - Normalizes status to: Accepted / Rejected / Wait listed / Interview.
  - Normalizes degree to: Masters / PhD.
  - Preserves the original raw_text field for traceability.

LLM Standardization (llm_hosting/llm_hosting/app.py):
  - Uses TinyLlama 1.1B (GGUF, CPU-only) via llama-cpp-python.
  - Reads the combined "program" field (e.g. "Computer Science, MIT") and splits
    it into standardized program name and university name.
  - Outputs llm-generated-program and llm-generated-university fields.
  - Run: python llm_hosting/llm_hosting/app.py --file applicant_data.json > llm_extend_applicant_data.json

Browser/driver: Chrome + Selenium Manager (auto-downloads ChromeDriver).

Scraping approximately 1,200 pages at 2.5 s/page takes ~50 minutes.

================================================================================
SETUP & RUN
================================================================================
Requirements: Python 3.10+, Google Chrome installed.

1. Navigate to module_2:
       cd module_2

2. Create and activate a virtual environment:
       python -m venv venv
       venv\Scripts\activate          # Windows
       source venv/bin/activate       # macOS/Linux

3. Install scraper dependencies:
       pip install -r requirements.txt

4. Run the scraper (saves to applicant_data.json):
       python scrape.py

5. Run the cleaner (saves to applicant_data_cleaned.json):
       python clean.py

6. Run LLM standardization:
       cd llm_hosting/llm_hosting
       pip install -r requirements.txt
       python app.py --file ../../applicant_data.json > ../../llm_extend_applicant_data.json
       cd ../..

================================================================================
KNOWN BUGS / NOTES
================================================================================
- GradCafe's HTML structure may change. If scrape.py returns 0 entries, inspect
  driver.page_source in _parse_page() to identify the current CSS selectors.
- GRE scores are not always present in Grad Cafe entries; None is used for missing values.
- The LLM standardization step can take several hours for 30,000 records on CPU.
  Parallelizing with multiprocessing is recommended (see app.py N_THREADS env var).
