"""
test_buttons.py
Tests for the /pull-data and /update-analysis button endpoints,
including busy-state gating and error-path behavior.
"""

import threading

import pytest

from flask_app import create_app


# ---------------------------------------------------------------------------
# POST /pull-data — happy path
# ---------------------------------------------------------------------------

@pytest.mark.buttons
def test_pull_data_returns_200(client):
    """POST /pull-data returns HTTP 200 when not busy."""
    rv = client.post("/pull-data")
    assert rv.status_code == 200


@pytest.mark.buttons
def test_pull_data_returns_ok_true(client):
    """POST /pull-data body includes {"ok": true} when not busy."""
    rv = client.post("/pull-data")
    assert rv.get_json()["ok"] is True


@pytest.mark.buttons
def test_pull_data_triggers_loader(tmp_path):
    """POST /pull-data calls the injected loader with the records from the scraper."""
    called_with = []

    def fake_loader(records, conn):
        called_with.extend(records)
        return len(records)

    app = create_app(
        config={"TESTING": True},
        conn_string="fake",
        scraper_fn=lambda: [{"url": "http://example.com/1", "program": "CS"}],
        loader_fn=fake_loader,
        query_fn=lambda conn: {},
    )
    with app.test_client() as c:
        c.post("/pull-data")

    assert len(called_with) == 1
    assert called_with[0]["url"] == "http://example.com/1"


# ---------------------------------------------------------------------------
# POST /update-analysis — happy path
# ---------------------------------------------------------------------------

@pytest.mark.buttons
def test_update_analysis_returns_200_when_not_busy(client):
    """POST /update-analysis returns 200 when no pull is running."""
    rv = client.post("/update-analysis")
    assert rv.status_code == 200


@pytest.mark.buttons
def test_update_analysis_returns_ok_true(client):
    """POST /update-analysis body includes {"ok": true} when not busy."""
    rv = client.post("/update-analysis")
    assert rv.get_json()["ok"] is True


# ---------------------------------------------------------------------------
# Busy-state gating
# ---------------------------------------------------------------------------

@pytest.mark.buttons
def test_update_analysis_returns_409_when_busy(busy_client):
    """POST /update-analysis returns 409 while a pull is in progress."""
    rv = busy_client.post("/update-analysis")
    assert rv.status_code == 409


@pytest.mark.buttons
def test_update_analysis_returns_busy_true_when_busy(busy_client):
    """POST /update-analysis body includes {"busy": true} when a pull is running."""
    rv = busy_client.post("/update-analysis")
    assert rv.get_json()["busy"] is True


@pytest.mark.buttons
def test_pull_data_returns_409_when_busy(busy_client):
    """POST /pull-data returns 409 when a pull is already in progress."""
    rv = busy_client.post("/pull-data")
    assert rv.status_code == 409


@pytest.mark.buttons
def test_pull_data_returns_busy_true_when_busy(busy_client):
    """POST /pull-data body includes {"busy": true} when already running."""
    rv = busy_client.post("/pull-data")
    assert rv.get_json()["busy"] is True


@pytest.mark.buttons
def test_update_analysis_performs_no_update_when_busy(busy_client):
    """POST /update-analysis must not call query_fn when busy."""
    query_calls = []

    app = create_app(
        config={"TESTING": True},
        conn_string="fake",
        scraper_fn=lambda: [],
        loader_fn=lambda r, c: 0,
        query_fn=lambda conn: query_calls.append(1) or {},
        state={"busy": True, "lock": threading.Lock()},
    )
    with app.test_client() as c:
        rv = c.post("/update-analysis")

    assert rv.status_code == 409
    assert len(query_calls) == 0, "query_fn must not be called when busy"


# ---------------------------------------------------------------------------
# Error-path: loader raises an exception
# ---------------------------------------------------------------------------

@pytest.mark.buttons
def test_pull_data_loader_error_resets_busy_flag():
    """If the loader raises, the busy flag is reset to False afterward."""
    state = {"busy": False, "lock": threading.Lock()}

    def bad_loader(records, conn):
        raise RuntimeError("DB unavailable")

    app = create_app(
        config={"TESTING": True},
        conn_string="fake",
        scraper_fn=lambda: [{"url": "http://x.com"}],
        loader_fn=bad_loader,
        query_fn=lambda conn: {},
        state=state,
    )
    with app.test_client() as c:
        c.post("/pull-data")  # TESTING=True → runs synchronously, exception swallowed

    assert state["busy"] is False, "busy flag must be False after loader error"
