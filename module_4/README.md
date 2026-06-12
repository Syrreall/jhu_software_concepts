# Module 4 — Grad Cafe Analytics: Testing & Documentation

End-to-end tested, documented Grad Cafe analytics service built with Flask + PostgreSQL.

## Quick links

- **Live docs:** https://syrreal-jhu-software-concepts.readthedocs.io/en/latest/
- **GitHub:** git@github.com:Syrreall/jhu_software_concepts.git

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set environment variable

```bash
# Linux / macOS
export DATABASE_URL="host=localhost port=5432 dbname=gradcafe user=postgres password=yourpassword"

# Windows PowerShell
$env:DATABASE_URL = "host=localhost port=5432 dbname=gradcafe user=postgres password=yourpassword"
```

### 3. Seed the database (first time only)

```bash
cd src
python load_data.py
```

### 4. Run the Flask app

```bash
cd src
python -c "from flask_app import create_app; create_app().run(host='0.0.0.0', port=8080, debug=True)"
```

Then open http://localhost:8080/analysis

---

## Running tests

From the `module_4/` directory:

```bash
# Full suite with coverage
pytest

# By marker
pytest -m "web or buttons or analysis or db or integration"

# DB tests require DATABASE_URL pointing to a test database:
export DATABASE_URL="host=localhost port=5432 dbname=gradcafe_test user=postgres password=yourpassword"
pytest -m db
pytest -m integration
```

Coverage report is printed to the terminal. To save it:

```bash
pytest --cov=src --cov-report=term-missing 2>&1 | tee coverage_summary.txt
```

---

## Project structure

```
module_4/
├── src/                        # Application code
│   ├── flask_app.py            # Flask factory + routes
│   ├── db_config.py            # DATABASE_URL helper
│   ├── load_data.py            # insert_rows() + schema
│   ├── query_data.py           # run_queries()
│   ├── scrape.py               # scrape_gradcafe()
│   ├── clean.py                # clean_records()
│   ├── templates/analysis.html
│   └── static/css/style.css
├── tests/
│   ├── conftest.py             # Shared fixtures & fake data
│   ├── test_flask_page.py      # @web
│   ├── test_buttons.py         # @buttons
│   ├── test_analysis_format.py # @analysis
│   ├── test_db_insert.py       # @db
│   └── test_integration_end_to_end.py  # @integration
├── docs/                       # Sphinx source
├── pytest.ini
├── requirements.txt
└── README.md
```

---

## Architecture

| Layer | Files | Responsibility |
|---|---|---|
| Web | `flask_app.py`, `templates/` | Flask routes, rendering, busy-state management |
| ETL | `scrape.py`, `clean.py` | Scrape Grad Cafe, clean raw data |
| DB | `load_data.py`, `query_data.py`, `db_config.py` | Insert records, run SQL analysis |

---

## CI

GitHub Actions workflow: `.github/workflows/tests.yml`  
Starts PostgreSQL, runs the full pytest suite with coverage on every push.
