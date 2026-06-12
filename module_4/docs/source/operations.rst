Operational Notes
=================

Busy-State Policy
-----------------

Only one scrape can run at a time. When ``POST /pull-data`` is accepted, the
``state["busy"]`` flag is set to ``True`` under a ``threading.Lock``.

- A second ``POST /pull-data`` while busy returns ``HTTP 409 {"busy": true}``.
- ``POST /update-analysis`` while busy also returns ``HTTP 409 {"busy": true}``
  and performs **no database query**.
- The flag is always reset in a ``finally`` block, so a scraper crash cannot
  leave the service permanently locked.

Idempotency Strategy
--------------------

URL is used as the natural uniqueness key. The ``applicants`` table has a
partial unique index on ``url WHERE url IS NOT NULL``. All inserts use
``ON CONFLICT (url) DO NOTHING``, so re-scraping the same pages is safe.

Records without a URL (rare) do not trigger the conflict clause — multiple
such rows could accumulate. This is an accepted limitation documented in
``limitations.txt``.

Uniqueness Keys
---------------

- **Primary key:** ``p_id SERIAL`` (internal)
- **Business key:** ``url TEXT`` (unique, nullable)

Troubleshooting
---------------

``RuntimeError: DATABASE_URL environment variable is not set``
    Set the ``DATABASE_URL`` environment variable before starting the app or
    running tests. See :doc:`setup`.

``psycopg.OperationalError: connection refused``
    PostgreSQL is not running. Start it with ``pg_ctl start`` or check your
    Docker / managed service.

``pytest: no tests ran``
    Make sure you are running pytest from inside ``module_4/`` where
    ``pytest.ini`` lives.

``FAILED ... --cov-fail-under=100``
    A code path is not exercised by any test. Run
    ``pytest --cov=src --cov-report=html`` and open ``htmlcov/index.html`` to
    find the missing lines.

GitHub Actions DB connection fails
    Ensure the ``postgres`` service in the workflow uses the same credentials as
    ``DATABASE_URL`` in the ``env:`` block.
