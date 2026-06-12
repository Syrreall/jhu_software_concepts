Testing Guide
=============

Running the Suite
-----------------

.. code-block:: bash

   cd module_4

   # Full suite (requires DATABASE_URL for db/integration marks)
   pytest

   # Run by marker (required command per assignment policy)
   pytest -m "web or buttons or analysis or db or integration"

   # Run only non-DB tests (no DATABASE_URL needed)
   pytest -m "web or buttons or analysis"

   # Save coverage summary
   pytest 2>&1 | tee coverage_summary.txt

Markers
-------

All tests are tagged with one or more of the following markers:

.. list-table::
   :header-rows: 1

   * - Marker
     - Covers
   * - ``@pytest.mark.web``
     - Flask route registration, GET /analysis page structure
   * - ``@pytest.mark.buttons``
     - POST /pull-data and POST /update-analysis behavior, busy-state gating
   * - ``@pytest.mark.analysis``
     - Answer: label presence, percentage two-decimal formatting
   * - ``@pytest.mark.db``
     - Database inserts, idempotency, query function keys (requires DATABASE_URL)
   * - ``@pytest.mark.integration``
     - Full pull → update → render flows (requires DATABASE_URL)

Stable Selectors
----------------

The ``analysis.html`` template uses ``data-testid`` attributes for reliable
element targeting in tests:

- ``data-testid="pull-data-btn"`` — the Pull Data button
- ``data-testid="update-analysis-btn"`` — the Update Analysis button
- ``data-testid="q1-value"`` through ``data-testid="q7-value"`` — metric cards

Fixtures (conftest.py)
----------------------

.. list-table::
   :header-rows: 1

   * - Fixture
     - Description
   * - ``app``
     - Flask app with all external calls faked (no DB, no network)
   * - ``client``
     - Test client from ``app``
   * - ``busy_app``
     - Flask app whose ``state["busy"]`` is pre-set to ``True``
   * - ``busy_client``
     - Test client from ``busy_app``
   * - ``empty_db``
     - Ensures the applicants table exists and is empty; yields conn string; cleans up after test
   * - ``db_app``
     - Flask app with real DB + fake scraper (requires DATABASE_URL)
   * - ``db_client``
     - Test client from ``db_app``

Test Doubles
------------

The ``create_app()`` factory accepts injectable callables:

- ``scraper_fn=lambda: [FAKE_RECORD]`` — avoids network calls
- ``loader_fn=lambda records, conn: len(records)`` — avoids DB writes in non-DB tests
- ``query_fn=lambda conn: FAKE_RESULTS`` — returns deterministic results

Busy-state is tested by injecting ``state={"busy": True, "lock": threading.Lock()}``.

TESTING mode
~~~~~~~~~~~~

When ``app.config["TESTING"] is True``, ``/pull-data`` runs the scraper and
loader **synchronously** in the request thread instead of spawning a background
thread. This makes tests deterministic with no need for ``sleep()`` or
threading events.
