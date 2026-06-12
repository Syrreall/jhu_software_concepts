"""
flask_app.py
Flask application factory for the Grad Cafe analytics service.

Public API
----------
create_app(config, scraper_fn, loader_fn, query_fn, state) -> Flask
    Build and return a configured Flask application.

Routes
------
GET  /analysis         Render the analysis dashboard.
POST /pull-data        Start a background scrape + DB load.
POST /update-analysis  Refresh analysis (blocked while a pull is running).
"""

import threading
from typing import Callable, Optional

from flask import Flask, jsonify, render_template

from db_config import get_conn_string
from load_data import insert_rows
from query_data import run_queries
from scrape import scrape_gradcafe


def create_app(
    config: Optional[dict] = None,
    scraper_fn: Optional[Callable] = None,
    loader_fn: Optional[Callable] = None,
    query_fn: Optional[Callable] = None,
    state: Optional[dict] = None,
    conn_string: Optional[str] = None,
) -> Flask:
    """
    Application factory.

    Parameters
    ----------
    config:
        Optional Flask config overrides (e.g. ``{"TESTING": True}``).
    scraper_fn:
        Callable ``() -> list[dict]`` that returns scraped records.
        Defaults to :func:`scrape.scrape_gradcafe`.
        Inject a fake in tests to avoid network calls.
    loader_fn:
        Callable ``(records, conn_string) -> int`` that inserts records.
        Defaults to :func:`load_data.insert_rows`.
    query_fn:
        Callable ``(conn_string) -> dict`` that returns analysis results.
        Defaults to :func:`query_data.run_queries`.
    state:
        Mutable dict with keys ``"busy"`` (bool) and ``"lock"`` (Lock).
        Inject a pre-built dict in tests to control busy state.
    conn_string:
        Override the database connection string directly.
        When provided, ``DATABASE_URL`` is not read from the environment.
        Useful in tests that inject fake ``query_fn``/``loader_fn`` so
        ``DATABASE_URL`` does not need to be set at all.

    Returns
    -------
    Flask
        Configured application instance.
    """
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.update(config or {})

    if state is None:
        state = {"busy": False, "lock": threading.Lock()}

    _scraper  = scraper_fn or scrape_gradcafe
    _loader   = loader_fn  or insert_rows
    _query    = query_fn   or run_queries
    _conn_fn  = (lambda: conn_string) if conn_string is not None else get_conn_string

    app.config["STATE"] = state

    @app.template_filter("pct")
    def pct_filter(value):
        """Format a numeric value as a percentage with exactly two decimal places."""
        if value is None:
            return "—"
        return f"{float(value):.2f}%"

    @app.route("/analysis")
    def analysis():
        """Render the analysis dashboard page."""
        conn_str = _conn_fn()
        results = _query(conn_str)
        return render_template("analysis.html", r=results, scraping=state["busy"])

    @app.route("/pull-data", methods=["POST"])
    def pull_data():
        """
        Start a background scrape and DB load.

        Returns 409 with ``{"busy": true}`` if a pull is already running.
        Returns 200 with ``{"ok": true}`` otherwise.
        In TESTING mode the scrape runs synchronously (no background thread).
        """
        lock = state.get("lock") or threading.Lock()
        with lock:
            if state["busy"]:
                return jsonify({"busy": True}), 409
            state["busy"] = True

        def _run():
            try:
                records = _scraper()
                conn_str = _conn_fn()
                _loader(records, conn_str)
            except Exception:
                pass
            finally:
                state["busy"] = False

        if app.config.get("TESTING"):
            _run()
        else:
            threading.Thread(target=_run, daemon=True).start()

        return jsonify({"ok": True}), 200

    @app.route("/update-analysis", methods=["POST"])
    def update_analysis():
        """
        Refresh analysis results.

        Returns 409 with ``{"busy": true}`` if a pull is in progress.
        Returns 200 with ``{"ok": true}`` otherwise.
        """
        if state["busy"]:
            return jsonify({"busy": True}), 409
        conn_str = _conn_fn()
        results = _query(conn_str)
        safe = {k: str(v) for k, v in results.items() if not isinstance(v, list)}
        return jsonify({"ok": True, "results": safe}), 200

    return app
