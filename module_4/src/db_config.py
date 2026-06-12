"""
db_config.py
Database connection helper — reads DATABASE_URL from the environment.
"""

import os


def get_conn_string() -> str:
    """Return the psycopg connection string from the DATABASE_URL env var."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Example: DATABASE_URL='host=localhost port=5432 dbname=gradcafe user=postgres password=secret'"
        )
    return url
