"""
test_integration_end_to_end.py
End-to-end integration tests: pull → update → render, and multiple-pull idempotency.
Requires DATABASE_URL. Skipped automatically when not set.
"""

import re

import psycopg
import pytest
from bs4 import BeautifulSoup

from load_data import insert_rows


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row_count(conn_str: str) -> int:
    with psycopg.connect(conn_str) as conn:
        return conn.execute("SELECT COUNT(*) FROM applicants;").fetchone()[0]


# ---------------------------------------------------------------------------
# Full pull → update → render flow
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_pull_inserts_rows_into_db(db_client, empty_db):
    """POST /pull-data (with fake scraper) inserts rows into the DB."""
    assert _row_count(empty_db) == 0
    rv = db_client.post("/pull-data")
    assert rv.status_code == 200
    assert _row_count(empty_db) == 2  # FAKE_RECORD + FAKE_RECORD_2


@pytest.mark.integration
def test_update_analysis_returns_ok_after_pull(db_client, empty_db):
    """After a successful pull, POST /update-analysis returns 200."""
    db_client.post("/pull-data")
    rv = db_client.post("/update-analysis")
    assert rv.status_code == 200
    assert rv.get_json()["ok"] is True


@pytest.mark.integration
def test_analysis_page_shows_updated_data_after_pull(db_client, empty_db):
    """After pull, GET /analysis renders the page with data and Answer: labels."""
    db_client.post("/pull-data")
    rv = db_client.get("/analysis")
    assert rv.status_code == 200
    assert b"Answer:" in rv.data


@pytest.mark.integration
def test_analysis_page_percentages_two_decimals_after_pull(db_client, empty_db):
    """After pull, percentages on /analysis are formatted with two decimals."""
    db_client.post("/pull-data")
    rv = db_client.get("/analysis")
    text = rv.data.decode("utf-8")
    pcts = re.findall(r"(\d+\.\d+)%", text)
    for pct in pcts:
        assert len(pct.split(".")[1]) == 2, f"'{pct}%' is not two-decimal"


@pytest.mark.integration
def test_pull_update_render_full_flow(db_client, empty_db):
    """Complete: pull → update-analysis → render all succeed in sequence."""
    rv1 = db_client.post("/pull-data")
    assert rv1.status_code == 200

    rv2 = db_client.post("/update-analysis")
    assert rv2.status_code == 200

    rv3 = db_client.get("/analysis")
    assert rv3.status_code == 200
    assert b"Analysis" in rv3.data
    assert b"Answer:" in rv3.data


# ---------------------------------------------------------------------------
# Multiple pulls — idempotency
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_two_pulls_with_same_data_no_duplicates(db_client, empty_db):
    """Pulling the same data twice keeps row count consistent (no duplicates)."""
    db_client.post("/pull-data")
    count_after_first = _row_count(empty_db)

    db_client.post("/pull-data")
    count_after_second = _row_count(empty_db)

    assert count_after_second == count_after_first, (
        f"Row count changed on second pull: {count_after_first} → {count_after_second}"
    )


@pytest.mark.integration
def test_two_pulls_returns_ok_both_times(db_client, empty_db):
    """Both POST /pull-data calls succeed when state resets between them."""
    rv1 = db_client.post("/pull-data")
    rv2 = db_client.post("/pull-data")
    assert rv1.status_code == 200
    assert rv2.status_code == 200
