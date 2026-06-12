"""
test_db_insert.py
Tests for database inserts, idempotency, and the query function.
Requires DATABASE_URL to point to a running PostgreSQL instance.
All tests are skipped automatically when DATABASE_URL is not set.
"""

import pytest
import psycopg

from load_data import insert_rows, CREATE_TABLE
from query_data import run_queries, EXPECTED_KEYS


# ---------------------------------------------------------------------------
# Insert on pull
# ---------------------------------------------------------------------------

@pytest.mark.db
def test_insert_adds_rows(empty_db):
    """After insert_rows(), the table contains the inserted records."""
    from fake_data import FAKE_RECORD
    conn_str = empty_db

    count = insert_rows([FAKE_RECORD], conn_str)
    assert count == 1

    with psycopg.connect(conn_str) as conn:
        row = conn.execute("SELECT COUNT(*) FROM applicants;").fetchone()
    assert row[0] == 1


@pytest.mark.db
def test_inserted_row_has_required_fields(empty_db):
    """Inserted rows contain non-null values for required schema fields."""
    from fake_data import FAKE_RECORD
    conn_str = empty_db

    insert_rows([FAKE_RECORD], conn_str)

    with psycopg.connect(conn_str) as conn:
        row = conn.execute(
            "SELECT program, status, term, degree, url FROM applicants LIMIT 1;"
        ).fetchone()

    program, status, term, degree, url = row
    assert program is not None
    assert status is not None
    assert term is not None
    assert degree is not None
    assert url is not None


@pytest.mark.db
def test_insert_multiple_rows(empty_db):
    """insert_rows() correctly inserts multiple distinct records."""
    from fake_data import FAKE_RECORD, FAKE_RECORD_2
    conn_str = empty_db

    count = insert_rows([FAKE_RECORD, FAKE_RECORD_2], conn_str)
    assert count == 2

    with psycopg.connect(conn_str) as conn:
        total = conn.execute("SELECT COUNT(*) FROM applicants;").fetchone()[0]
    assert total == 2


# ---------------------------------------------------------------------------
# Idempotency / uniqueness
# ---------------------------------------------------------------------------

@pytest.mark.db
def test_duplicate_url_not_inserted(empty_db):
    """Inserting the same record twice does not create duplicate rows."""
    from fake_data import FAKE_RECORD
    conn_str = empty_db

    insert_rows([FAKE_RECORD], conn_str)
    insert_rows([FAKE_RECORD], conn_str)  # second call — should be a no-op

    with psycopg.connect(conn_str) as conn:
        total = conn.execute("SELECT COUNT(*) FROM applicants;").fetchone()[0]
    assert total == 1, "Duplicate URL must not create a second row"


@pytest.mark.db
def test_overlapping_batch_no_duplicates(empty_db):
    """A batch with one new and one already-existing record inserts only the new one."""
    from fake_data import FAKE_RECORD, FAKE_RECORD_2
    conn_str = empty_db

    insert_rows([FAKE_RECORD], conn_str)
    insert_rows([FAKE_RECORD, FAKE_RECORD_2], conn_str)  # FAKE_RECORD is a duplicate

    with psycopg.connect(conn_str) as conn:
        total = conn.execute("SELECT COUNT(*) FROM applicants;").fetchone()[0]
    assert total == 2


# ---------------------------------------------------------------------------
# Query function
# ---------------------------------------------------------------------------

@pytest.mark.db
def test_query_returns_expected_keys(empty_db):
    """run_queries() returns a dict containing all EXPECTED_KEYS."""
    conn_str = empty_db
    result = run_queries(conn_str)
    for key in EXPECTED_KEYS:
        assert key in result, f"Missing key: {key}"


@pytest.mark.db
def test_query_returns_dict(empty_db):
    """run_queries() return type is a dict."""
    conn_str = empty_db
    result = run_queries(conn_str)
    assert isinstance(result, dict)


@pytest.mark.db
def test_query_numeric_values_are_numbers(empty_db):
    """Numeric query results are int or float (or None), not strings."""
    from fake_data import FAKE_RECORD
    conn_str = empty_db
    insert_rows([FAKE_RECORD], conn_str)

    result = run_queries(conn_str)
    assert isinstance(result["q1_fall_2026_count"], int)
    assert isinstance(result["q2_pct_international"], float)


@pytest.mark.db
def test_query_top_programs_is_list(empty_db):
    """q10_top_programs is a list of dicts."""
    conn_str = empty_db
    result = run_queries(conn_str)
    assert isinstance(result["q10_top_programs"], list)


@pytest.mark.db
def test_query_acceptance_by_degree_is_list(empty_db):
    """q11_acceptance_by_degree is a list of dicts."""
    conn_str = empty_db
    result = run_queries(conn_str)
    assert isinstance(result["q11_acceptance_by_degree"], list)
