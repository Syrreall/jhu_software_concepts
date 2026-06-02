"""
run.py — Flask app entry point. Start with: python run.py
"""
import os
import subprocess
import threading
from pathlib import Path

import psycopg
from flask import Flask, jsonify, render_template
from db_config import get_conn_string
from query_data import run_queries

app = Flask(__name__)

# Track whether a scrape is currently running
_scrape_running = False
_scrape_lock = threading.Lock()

MODULE2_SCRAPE = Path(__file__).parent.parent / "module_2" / "scrape.py"


@app.route("/")
def index():
    results = run_queries()
    return render_template("analysis.html", r=results, scraping=_scrape_running)


@app.route("/pull_data", methods=["POST"])
def pull_data():
    """Start a background scrape and add new results to the database."""
    global _scrape_running
    with _scrape_lock:
        if _scrape_running:
            return jsonify({"status": "already_running", "message": "Scrape already in progress."})
        _scrape_running = True

    def _run():
        global _scrape_running
        try:
            subprocess.run(
                ["python", str(MODULE2_SCRAPE)],
                capture_output=True,
            )
            # After scraping, reload any new entries into the DB
            _load_new_data()
        finally:
            with _scrape_lock:
                _scrape_running = False

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "started", "message": "Scraping started in background."})


@app.route("/update_analysis")
def update_analysis():
    """Refresh analysis — blocked if a scrape is running."""
    if _scrape_running:
        return jsonify({"status": "busy", "message": "Scrape in progress. Try again shortly."})
    results = run_queries()
    return jsonify({"status": "ok", "results": {k: str(v) for k, v in results.items() if not isinstance(v, list)}})


def _load_new_data():
    """Load any newly scraped entries that are not already in the DB."""
    import json
    new_file = Path(__file__).parent.parent / "module_2" / "applicant_data.json"
    if not new_file.exists():
        return

    with open(new_file, "r", encoding="utf-8") as f:
        records = json.load(f)

    from load_data import INSERT_ROW, _parse_date, _parse_float
    with psycopg.connect(get_conn_string()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT url FROM applicants WHERE url IS NOT NULL;")
            existing_urls = {row[0] for row in cur.fetchall()}

            added = 0
            for row in records:
                url = row.get("url")
                if url and url in existing_urls:
                    continue
                try:
                    cur.execute(INSERT_ROW, (
                        row.get("program"), row.get("comments"),
                        _parse_date(row.get("date_added")), url,
                        row.get("status"), row.get("term"),
                        row.get("US/International"),
                        _parse_float(row.get("GPA")), _parse_float(row.get("GRE")),
                        _parse_float(row.get("GRE_V")), _parse_float(row.get("GRE_AW")),
                        row.get("Degree"), row.get("llm-generated-program"),
                        row.get("llm-generated-university"),
                    ))
                    added += 1
                except Exception:
                    pass
            conn.commit()
            print(f"Added {added} new entries from scrape.")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
