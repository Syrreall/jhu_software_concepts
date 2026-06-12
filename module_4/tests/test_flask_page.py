"""
test_flask_page.py
Tests for Flask app creation, route registration, and the /analysis page.
"""

import pytest
from bs4 import BeautifulSoup

from flask_app import create_app


# ---------------------------------------------------------------------------
# App factory / config
# ---------------------------------------------------------------------------

@pytest.mark.web
def test_app_factory_creates_app(app):
    """create_app() returns a non-None Flask application."""
    assert app is not None


@pytest.mark.web
def test_app_is_in_testing_mode(app):
    """TESTING flag is set so the test client behaves correctly."""
    assert app.config["TESTING"] is True


@pytest.mark.web
def test_analysis_route_registered(app):
    """The /analysis route exists in the URL map."""
    rules = [rule.rule for rule in app.url_map.iter_rules()]
    assert "/analysis" in rules


@pytest.mark.web
def test_pull_data_route_registered(app):
    """The /pull-data route exists in the URL map."""
    rules = [rule.rule for rule in app.url_map.iter_rules()]
    assert "/pull-data" in rules


@pytest.mark.web
def test_update_analysis_route_registered(app):
    """The /update-analysis route exists in the URL map."""
    rules = [rule.rule for rule in app.url_map.iter_rules()]
    assert "/update-analysis" in rules


# ---------------------------------------------------------------------------
# GET /analysis — status and structure
# ---------------------------------------------------------------------------

@pytest.mark.web
def test_get_analysis_returns_200(client):
    """GET /analysis responds with HTTP 200."""
    rv = client.get("/analysis")
    assert rv.status_code == 200


@pytest.mark.web
def test_analysis_page_contains_analysis_text(client):
    """The rendered page contains the word 'Analysis'."""
    rv = client.get("/analysis")
    assert b"Analysis" in rv.data


@pytest.mark.web
def test_analysis_page_has_pull_data_button(client):
    """Page contains a button with data-testid='pull-data-btn'."""
    rv = client.get("/analysis")
    soup = BeautifulSoup(rv.data, "html.parser")
    btn = soup.find(attrs={"data-testid": "pull-data-btn"})
    assert btn is not None, "pull-data-btn not found in page HTML"


@pytest.mark.web
def test_analysis_page_has_update_analysis_button(client):
    """Page contains a button with data-testid='update-analysis-btn'."""
    rv = client.get("/analysis")
    soup = BeautifulSoup(rv.data, "html.parser")
    btn = soup.find(attrs={"data-testid": "update-analysis-btn"})
    assert btn is not None, "update-analysis-btn not found in page HTML"


@pytest.mark.web
def test_analysis_page_has_pull_data_button_text(client):
    """The pull-data button displays 'Pull Data'."""
    rv = client.get("/analysis")
    soup = BeautifulSoup(rv.data, "html.parser")
    btn = soup.find(attrs={"data-testid": "pull-data-btn"})
    assert "Pull Data" in btn.get_text()


@pytest.mark.web
def test_analysis_page_has_update_button_text(client):
    """The update-analysis button displays 'Update Analysis'."""
    rv = client.get("/analysis")
    soup = BeautifulSoup(rv.data, "html.parser")
    btn = soup.find(attrs={"data-testid": "update-analysis-btn"})
    assert "Update Analysis" in btn.get_text()


@pytest.mark.web
def test_analysis_page_has_answer_label(client):
    """The rendered page contains at least one 'Answer:' label."""
    rv = client.get("/analysis")
    assert b"Answer:" in rv.data


@pytest.mark.web
def test_analysis_page_content_type_is_html(client):
    """Response Content-Type is text/html."""
    rv = client.get("/analysis")
    assert "text/html" in rv.content_type
