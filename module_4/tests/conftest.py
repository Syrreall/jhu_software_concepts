"""
conftest.py
Shared pytest fixtures for the Grad Cafe test suite.
"""

import os
import sys
import threading
from pathlib import Path

import psycopg
import pytest

# Make src/ and tests/ importable when running pytest from module_4/
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from flask_app import create_app
from load_data import CREATE_TABLE, insert_rows
from query_data import EXPECTED_KEYS
from fake_data import FAKE_RECORD, FAKE_RECORD_2, FAKE_RESULTS


# ---------------------------------------------------------------------------
# Flask fixtures (no real DB — all functions are faked)
# ---------------------------------------------------------------------------

def _make_state(busy: bool = False) -> dict:
    return {"busy": busy, "lock": threading.Lock()}


@pytest.fixture
def app():
    """Flask app with all external calls faked (no DATABASE_URL needed)."""
    application = create_app(
        config={"TESTING": True},
        conn_string="fake",
        scraper_fn=lambda: [FAKE_RECORD],
        loader_fn=lambda records, conn: len(records),
        query_fn=lambda conn: dict(FAKE_RESULTS),
        state=_make_state(busy=False),
    )
    return application


@pytest.fixture
def client(app):
    """Test client backed by the faked app."""
    with app.test_client() as c:
        yield c


@pytest.fixture
def busy_app():
    """Flask app whose state starts as busy (simulates in-progress pull)."""
    application = create_app(
        config={"TESTING": True},
        conn_string="fake",
        scraper_fn=lambda: [FAKE_RECORD],
        loader_fn=lambda records, conn: len(records),
        query_fn=lambda conn: dict(FAKE_RESULTS),
        state=_make_state(busy=True),
    )
    return application


@pytest.fixture
def busy_client(busy_app):
    """Test client backed by the busy app."""
    with busy_app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Database fixtures (require DATABASE_URL to be set)
# ---------------------------------------------------------------------------

def _get_test_conn_string():
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set — skipping DB test")
    return url


@pytest.fixture(scope="session")
def db_conn_string():
    """Session-scoped connection string for the test database."""
    return _get_test_conn_string()


@pytest.fixture
def empty_db(db_conn_string):
    """
    Ensure the applicants table exists and is empty before each DB test.
    Cleans up after the test as well.
    """
    with psycopg.connect(db_conn_string) as conn:
        conn.execute(CREATE_TABLE)
        conn.execute("DELETE FROM applicants;")
        conn.commit()
    yield db_conn_string
    with psycopg.connect(db_conn_string) as conn:
        conn.execute("DELETE FROM applicants;")
        conn.commit()


@pytest.fixture
def db_app(db_conn_string, empty_db):
    """Flask app that uses the real test DB but a fake scraper."""
    os.environ["DATABASE_URL"] = db_conn_string
    application = create_app(
        config={"TESTING": True},
        scraper_fn=lambda: [FAKE_RECORD, FAKE_RECORD_2],
        state=_make_state(busy=False),
    )
    return application


@pytest.fixture
def db_client(db_app):
    """Test client backed by the real-DB app."""
    with db_app.test_client() as c:
        yield c
