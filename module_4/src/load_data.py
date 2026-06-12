"""
load_data.py
Loads and inserts Grad Cafe applicant records into PostgreSQL.

Public API
----------
insert_rows(records, conn_string) -> int
    Insert a list of record dicts into the applicants table.
    Returns the number of rows actually inserted (duplicates are skipped).

load_data(data_file, conn_string) -> None
    One-shot bulk load from a JSON file (used for initial seeding).
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import psycopg

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS applicants (
    p_id                  SERIAL PRIMARY KEY,
    program               TEXT,
    comments              TEXT,
    date_added            DATE,
    url                   TEXT UNIQUE,
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

# Kept for backwards compatibility — the UNIQUE constraint on url is defined inline above.
CREATE_INDEX = ""

INSERT_ROW = """
INSERT INTO applicants
    (program, comments, date_added, url, status, term,
     us_or_international, gpa, gre, gre_v, gre_aw, degree,
     llm_generated_program, llm_generated_university)
VALUES
    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (url) DO NOTHING;
"""

DATE_FORMATS = [
    "%B %d, %Y",
    "%b %d, %Y",
    "%Y-%m-%d",
    "%m/%d/%Y",
]


def _parse_date(value: Optional[str]):
    """Parse a date string into a Python date, or None if unparseable."""
    if not value:
        return None
    value = re.sub(r"(?i)added on\s*", "", value).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_float(value) -> Optional[float]:
    """Safely convert a value to float, stripping 'GPA' prefix if present."""
    if value is None:
        return None
    try:
        return float(str(value).replace("GPA", "").strip())
    except (ValueError, TypeError):
        return None


def insert_rows(records: list, conn_string: str) -> int:
    """
    Insert applicant records into the database, skipping duplicates by URL.

    Parameters
    ----------
    records:
        List of dicts with applicant fields matching the applicants schema.
    conn_string:
        psycopg connection string (from DATABASE_URL).

    Returns
    -------
    int
        Number of rows inserted (duplicates are silently skipped via ON CONFLICT DO NOTHING).
    """
    inserted = 0
    with psycopg.connect(conn_string) as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE)
            conn.commit()
            for row in records:
                try:
                    cur.execute(INSERT_ROW, (
                        row.get("program"),
                        row.get("comments"),
                        _parse_date(row.get("date_added")),
                        row.get("url"),
                        row.get("status"),
                        row.get("term"),
                        row.get("US/International") or row.get("us_or_international"),
                        _parse_float(row.get("GPA") or row.get("gpa")),
                        _parse_float(row.get("GRE") or row.get("gre")),
                        _parse_float(row.get("GRE_V") or row.get("gre_v")),
                        _parse_float(row.get("GRE_AW") or row.get("gre_aw")),
                        row.get("Degree") or row.get("degree"),
                        row.get("llm-generated-program") or row.get("llm_generated_program"),
                        row.get("llm-generated-university") or row.get("llm_generated_university"),
                    ))
                    inserted += cur.rowcount
                except Exception:
                    pass
            conn.commit()
    return inserted


def load_data(data_file: Path, conn_string: str) -> None:
    """
    Bulk-load all records from a JSON file into the database.

    Parameters
    ----------
    data_file:
        Path to a JSON file containing a list of applicant record dicts.
    conn_string:
        psycopg connection string.
    """
    with open(data_file, "r", encoding="utf-8") as f:
        records = json.load(f)
    count = insert_rows(records, conn_string)
    print(f"Inserted {count} rows from {data_file}.")
