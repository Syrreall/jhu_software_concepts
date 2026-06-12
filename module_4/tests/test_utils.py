"""
test_utils.py
Coverage top-up tests for helper functions, edge cases, and untested paths.
Covers: clean.py (100%), db_config.py RuntimeError, load_data helpers,
        load_data() function, flask_app pct_filter(None) and background thread,
        scrape.scrape_gradcafe() success and failure paths.
"""

import json
import threading
from unittest.mock import MagicMock, mock_open, patch

import pytest

from fake_data import FAKE_RECORD, FAKE_RESULTS


# ---------------------------------------------------------------------------
# clean.py — full coverage
# ---------------------------------------------------------------------------

@pytest.mark.web
def test_clean_text_strips_html():
    from clean import _clean_text
    assert _clean_text("<b>Hello</b>  World") == "Hello World"


@pytest.mark.web
def test_clean_text_unescapes_entities():
    from clean import _clean_text
    assert _clean_text("M&amp;T") == "M&T"


@pytest.mark.web
def test_clean_text_none_returns_none():
    from clean import _clean_text
    assert _clean_text(None) is None


@pytest.mark.web
def test_clean_text_empty_string_returns_none():
    from clean import _clean_text
    assert _clean_text("   ") is None


@pytest.mark.web
def test_clean_gpa_valid():
    from clean import _clean_gpa
    assert _clean_gpa("3.75") == "3.75"


@pytest.mark.web
def test_clean_gpa_strips_prefix():
    from clean import _clean_gpa
    assert _clean_gpa("GPA 3.90") == "3.90"


@pytest.mark.web
def test_clean_gpa_none_returns_none():
    from clean import _clean_gpa
    assert _clean_gpa(None) is None


@pytest.mark.web
def test_clean_gpa_out_of_range_returns_none():
    from clean import _clean_gpa
    assert _clean_gpa("5.00") is None


@pytest.mark.web
def test_clean_gpa_invalid_string_returns_none():
    from clean import _clean_gpa
    assert _clean_gpa("not-a-number") is None


@pytest.mark.web
def test_clean_gre_valid_quantitative():
    from clean import _clean_gre
    assert _clean_gre("165") == "165"


@pytest.mark.web
def test_clean_gre_valid_combined():
    from clean import _clean_gre
    assert _clean_gre("320") == "320"


@pytest.mark.web
def test_clean_gre_none_returns_none():
    from clean import _clean_gre
    assert _clean_gre(None) is None


@pytest.mark.web
def test_clean_gre_out_of_range_returns_none():
    from clean import _clean_gre
    assert _clean_gre("999") is None


@pytest.mark.web
def test_clean_gre_invalid_string_returns_none():
    from clean import _clean_gre
    assert _clean_gre("abc") is None


@pytest.mark.web
def test_clean_record_returns_dict():
    from clean import clean_record
    result = clean_record(FAKE_RECORD)
    assert isinstance(result, dict)
    assert result["program"] is not None


@pytest.mark.web
def test_clean_records_list():
    from clean import clean_records
    results = clean_records([FAKE_RECORD, FAKE_RECORD])
    assert len(results) == 2
    assert all(isinstance(r, dict) for r in results)


# ---------------------------------------------------------------------------
# db_config.py — RuntimeError when DATABASE_URL is unset
# ---------------------------------------------------------------------------

@pytest.mark.db
def test_get_conn_string_raises_without_env(monkeypatch):
    """get_conn_string() raises RuntimeError when DATABASE_URL is not set."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from db_config import get_conn_string
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        get_conn_string()


# ---------------------------------------------------------------------------
# load_data.py — _parse_date edge cases
# ---------------------------------------------------------------------------

@pytest.mark.db
def test_parse_date_none_returns_none():
    from load_data import _parse_date
    assert _parse_date(None) is None


@pytest.mark.db
def test_parse_date_empty_string_returns_none():
    from load_data import _parse_date
    assert _parse_date("") is None


@pytest.mark.db
def test_parse_date_strips_added_on_prefix():
    from load_data import _parse_date
    result = _parse_date("Added on March 15, 2026")
    assert result is not None


@pytest.mark.db
def test_parse_date_unparseable_returns_none():
    from load_data import _parse_date
    assert _parse_date("not-a-real-date-xyzzy") is None


@pytest.mark.db
def test_parse_float_none_returns_none():
    from load_data import _parse_float
    assert _parse_float(None) is None


@pytest.mark.db
def test_parse_float_invalid_string_returns_none():
    from load_data import _parse_float
    assert _parse_float("not-a-number") is None


# ---------------------------------------------------------------------------
# load_data.py — insert_rows exception path (lines 127-128)
# ---------------------------------------------------------------------------

@pytest.mark.db
def test_insert_rows_skips_erroring_records(monkeypatch):
    """Records that cause DB errors are skipped without aborting the batch."""

    class _FakeCursor:
        rowcount = 0

        def execute(self, sql, params=None):
            if sql and "INSERT" in sql:
                raise Exception("injected insert error")

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    class _FakeConn:
        def cursor(self):
            return _FakeCursor()

        def commit(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    import load_data as ld
    monkeypatch.setattr(ld.psycopg, "connect", lambda *a, **k: _FakeConn())
    result = ld.insert_rows([{"url": "http://x.com"}], "fake")
    assert result == 0


# ---------------------------------------------------------------------------
# load_data.py — load_data() function (lines 144-147)
# ---------------------------------------------------------------------------

@pytest.mark.db
def test_load_data_from_json_file(tmp_path, empty_db):
    """load_data() reads a JSON file and inserts its records into the DB."""
    import psycopg
    from load_data import load_data

    data_file = tmp_path / "test_records.json"
    data_file.write_text(json.dumps([FAKE_RECORD]))

    load_data(data_file, empty_db)

    with psycopg.connect(empty_db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM applicants;").fetchone()[0]
    assert count == 1


# ---------------------------------------------------------------------------
# flask_app.py — pct_filter(None) renders "—" (line 84)
# ---------------------------------------------------------------------------

@pytest.mark.analysis
def test_pct_filter_none_renders_dash():
    """When a percentage value is None, pct_filter renders '—' not a crash."""
    from flask_app import create_app

    results = dict(FAKE_RESULTS)
    results["q2_pct_international"] = None

    app = create_app(
        config={"TESTING": True},
        conn_string="fake",
        query_fn=lambda conn: results,
        scraper_fn=lambda: [],
        loader_fn=lambda r, c: 0,
    )
    with app.test_client() as c:
        rv = c.get("/analysis")
    assert rv.status_code == 200
    assert "—" in rv.data.decode("utf-8")


# ---------------------------------------------------------------------------
# flask_app.py — background thread path (line 122)
# ---------------------------------------------------------------------------

@pytest.mark.buttons
def test_pull_data_background_thread_executes():
    """Without TESTING mode, /pull-data starts a background thread that runs the loader."""
    from flask_app import create_app

    done = threading.Event()

    def fake_loader(records, conn):
        done.set()
        return len(records)

    # TESTING is NOT set — triggers the background thread path
    app = create_app(
        conn_string="fake",
        scraper_fn=lambda: [FAKE_RECORD],
        loader_fn=fake_loader,
        query_fn=lambda conn: {},
    )
    with app.test_client() as c:
        rv = c.post("/pull-data")

    assert rv.status_code == 200
    assert done.wait(timeout=3.0), "Background thread did not complete in time"


# ---------------------------------------------------------------------------
# scrape.py — scrape_gradcafe() success and failure paths (lines 36-49)
# ---------------------------------------------------------------------------

@pytest.mark.web
def test_scrape_gradcafe_success(monkeypatch, tmp_path):
    """scrape_gradcafe() calls the scraper script and parses the output JSON."""
    import scrape

    fake_records = [{"url": "http://gradcafe.com/1", "program": "CS"}]
    json_content = json.dumps(fake_records)

    mock_proc = MagicMock()
    mock_proc.returncode = 0

    monkeypatch.setattr(scrape.subprocess, "run", lambda *a, **k: mock_proc)

    m = mock_open(read_data=json_content)
    with patch("builtins.open", m):
        result = scrape.scrape_gradcafe()

    assert result == fake_records


@pytest.mark.web
def test_scrape_gradcafe_raises_on_nonzero_exit(monkeypatch):
    """scrape_gradcafe() raises RuntimeError when the scraper script fails."""
    import scrape

    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.stderr = "Chromedriver not found"

    monkeypatch.setattr(scrape.subprocess, "run", lambda *a, **k: mock_proc)

    with pytest.raises(RuntimeError, match="Scraper failed"):
        scrape.scrape_gradcafe()
