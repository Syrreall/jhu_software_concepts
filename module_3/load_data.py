"""
load_data.py
Loads cleaned Grad Cafe data from module_2 into a PostgreSQL database.
"""

import json
import re
from datetime import datetime
from pathlib import Path

import psycopg
from db_config import get_conn_string

DATA_FILE = Path(__file__).parent.parent / "module_2" / "llm_extend_applicant_data.json"

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS applicants (
    p_id                  SERIAL PRIMARY KEY,
    program               TEXT,
    comments              TEXT,
    date_added            DATE,
    url                   TEXT,
    status                TEXT,
    term                  TEXT,
    us_or_international   TEXT,
    gpa                   FLOAT,
    gre                   FLOAT,
    gre_v                 FLOAT,
    gre_aw                FLOAT,
    degree                TEXT,
    llm_generated_program      TEXT,
    llm_generated_university   TEXT
);
"""

INSERT_ROW = """
INSERT INTO applicants
    (program, comments, date_added, url, status, term,
     us_or_international, gpa, gre, gre_v, gre_aw, degree,
     llm_generated_program, llm_generated_university)
VALUES
    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
"""

DATE_FORMATS = [
    "%B %d, %Y",   # May 31, 2026
    "%b %d, %Y",   # May 31, 2026 (abbrev)
    "%Y-%m-%d",    # 2026-05-31
    "%m/%d/%Y",    # 05/31/2026
]


def _parse_date(value: str | None):
    """Parse a date string into a Python date object."""
    if not value:
        return None
    # Strip "Added on" prefix
    value = re.sub(r"(?i)added on\s*", "", value).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_float(value) -> float | None:
    """Safely convert a value to float."""
    if value is None:
        return None
    try:
        return float(str(value).replace("GPA", "").strip())
    except (ValueError, TypeError):
        return None


def load_data(data_file: Path = DATA_FILE) -> None:
    """Load all applicant records from JSON into the PostgreSQL database."""
    print(f"Loading data from {data_file}...")
    with open(data_file, "r", encoding="utf-8") as f:
        records = json.load(f)
    print(f"Found {len(records)} records.")

    with psycopg.connect(get_conn_string()) as conn:
        with conn.cursor() as cur:
            # Create table if it doesn't exist
            cur.execute(CREATE_TABLE)
            conn.commit()

            # Check for existing entries to avoid duplicates
            cur.execute("SELECT COUNT(*) FROM applicants;")
            existing = cur.fetchone()[0]
            if existing > 0:
                print(f"Table already has {existing} rows. Skipping load.")
                print("To reload, run: DROP TABLE applicants; in psql then rerun.")
                return

            # Insert all records
            inserted = 0
            errors = 0
            for row in records:
                try:
                    cur.execute(INSERT_ROW, (
                        row.get("program"),
                        row.get("comments"),
                        _parse_date(row.get("date_added")),
                        row.get("url"),
                        row.get("status"),
                        row.get("term"),
                        row.get("US/International"),
                        _parse_float(row.get("GPA")),
                        _parse_float(row.get("GRE")),
                        _parse_float(row.get("GRE_V")),
                        _parse_float(row.get("GRE_AW")),
                        row.get("Degree"),
                        row.get("llm-generated-program"),
                        row.get("llm-generated-university"),
                    ))
                    inserted += 1
                except Exception as e:
                    errors += 1
                    if errors <= 5:
                        print(f"  Row error: {e}")

            conn.commit()
            print(f"Inserted {inserted} rows ({errors} errors).")


if __name__ == "__main__":
    load_data()
