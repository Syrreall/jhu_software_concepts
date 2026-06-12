Overview & Setup
================

The Grad Cafe Analytics service scrapes graduate school admission data from
The Grad Cafe, stores it in PostgreSQL, and serves an interactive analysis
dashboard via Flask.

Environment Variables
---------------------

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Variable
     - Description
   * - ``DATABASE_URL``
     - **Required.** psycopg connection string, e.g.
       ``host=localhost port=5432 dbname=gradcafe user=postgres password=secret``

Installation
------------

.. code-block:: bash

   pip install -r requirements.txt

Database Seeding (first run only)
----------------------------------

.. code-block:: bash

   cd module_4/src
   python load_data.py

Running the Application
-----------------------

.. code-block:: bash

   export DATABASE_URL="host=localhost port=5432 dbname=gradcafe user=postgres password=secret"
   cd module_4/src
   python -c "from flask_app import create_app; create_app().run(host='0.0.0.0', port=8080, debug=True)"

Then open http://localhost:8080/analysis in your browser.

Running the Tests
-----------------

.. code-block:: bash

   cd module_4
   export DATABASE_URL="host=localhost port=5432 dbname=gradcafe_test user=postgres password=secret"
   pytest

See :doc:`testing` for details on markers and fixtures.
