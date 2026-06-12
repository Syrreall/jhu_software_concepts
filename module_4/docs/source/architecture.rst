Architecture
============

The service is divided into three layers:

Web Layer
---------

**Files:** ``flask_app.py``, ``templates/analysis.html``, ``static/``

The Flask application factory (``create_app()``) wires together all three layers
and exposes three routes:

- ``GET /analysis`` — renders the analysis dashboard.
- ``POST /pull-data`` — starts a background scrape + DB load; returns 409 if busy.
- ``POST /update-analysis`` — refreshes analysis results; returns 409 if busy.

All three external dependencies (scraper, loader, query function) are injected
at construction time, making the web layer fully testable without network or DB.

ETL Layer
---------

**Files:** ``scrape.py``, ``clean.py``

- ``scrape_gradcafe()`` uses Selenium (headless Chrome) and BeautifulSoup to
  scrape the Grad Cafe survey pages and return raw record dicts.
- ``clean_records()`` normalizes text fields, validates GPA/GRE ranges, and
  returns cleaned dicts ready for database insertion.

In production the Flask app calls the scraper in a background thread so the
HTTP response is returned immediately. In tests, ``TESTING=True`` causes the
route to run synchronously — no threads, no sleep needed.

Database Layer
--------------

**Files:** ``load_data.py``, ``query_data.py``, ``db_config.py``

- ``db_config.get_conn_string()`` reads ``DATABASE_URL`` from the environment.
- ``load_data.insert_rows(records, conn_string)`` creates the ``applicants``
  table if needed and inserts records using ``ON CONFLICT DO NOTHING`` to
  enforce URL-level idempotency.
- ``query_data.run_queries(conn_string)`` executes 11 SQL analysis queries and
  returns a dict with keys defined in ``EXPECTED_KEYS``.

Busy-State Policy
-----------------

A mutable ``state`` dict (``{"busy": bool, "lock": Lock}``) tracks whether a
scrape is running. Both ``/pull-data`` and ``/update-analysis`` check this flag
under the lock and return ``409 {"busy": true}`` when active. The flag is
always reset in a ``finally`` block, even if the scraper or loader raises.
