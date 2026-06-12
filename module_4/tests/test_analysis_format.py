"""
test_analysis_format.py
Tests that analysis outputs are correctly labeled and percentages
are always rendered with exactly two decimal places.
"""

import re

import pytest
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# "Answer:" labels
# ---------------------------------------------------------------------------

@pytest.mark.analysis
def test_answer_labels_present(client):
    """Every analysis card value is prefixed with 'Answer:'."""
    rv = client.get("/analysis")
    assert b"Answer:" in rv.data


@pytest.mark.analysis
def test_multiple_answer_labels_present(client):
    """The page contains more than one 'Answer:' label."""
    rv = client.get("/analysis")
    text = rv.data.decode("utf-8")
    count = text.count("Answer:")
    assert count >= 2, f"Expected multiple Answer: labels, found {count}"


@pytest.mark.analysis
def test_answer_labels_in_cards(client):
    """Card value elements contain 'Answer:'."""
    rv = client.get("/analysis")
    soup = BeautifulSoup(rv.data, "html.parser")
    card_values = soup.find_all(attrs={"data-testid": re.compile(r"q\d+-value")})
    assert len(card_values) > 0, "No card value elements with data-testid found"
    for card in card_values:
        assert "Answer:" in card.get_text(), f"Card missing 'Answer:': {card}"


# ---------------------------------------------------------------------------
# Percentage formatting — exactly two decimal places
# ---------------------------------------------------------------------------

@pytest.mark.analysis
def test_percentages_have_two_decimal_places(client):
    """Every percentage on the page is formatted as XX.XX%."""
    rv = client.get("/analysis")
    text = rv.data.decode("utf-8")
    # Match any number followed by % — must have exactly 2 decimal digits
    pct_pattern = re.compile(r"(\d+\.\d+)%")
    matches = pct_pattern.findall(text)
    assert len(matches) > 0, "No percentages found on the analysis page"
    for match in matches:
        decimal_part = match.split(".")[1]
        assert len(decimal_part) == 2, (
            f"Percentage '{match}%' does not have exactly two decimal places"
        )


@pytest.mark.analysis
def test_international_pct_two_decimals(client):
    """The q2 international percentage is shown with two decimal places."""
    rv = client.get("/analysis")
    # FAKE_RESULTS has q2_pct_international = 39.28
    assert b"39.28%" in rv.data


@pytest.mark.analysis
def test_accepted_pct_two_decimals(client):
    """The q5 accepted percentage is shown with two decimal places."""
    rv = client.get("/analysis")
    # FAKE_RESULTS has q5_pct_accepted_fall2026 = 22.50
    assert b"22.50%" in rv.data


@pytest.mark.analysis
def test_zero_percent_formatted_correctly(tmp_path):
    """A 0% value is rendered as '0.00%', not '0%'."""
    from flask_app import create_app
    results = {
        "q1_fall_2026_count": 0,
        "q2_pct_international": 0.0,
        "q3_avg_gpa": None,
        "q3_avg_gre": None,
        "q3_avg_gre_v": None,
        "q3_avg_gre_aw": None,
        "q4_avg_gpa_american_fall2026": None,
        "q5_pct_accepted_fall2026": 0.0,
        "q6_avg_gpa_accepted_fall2026": None,
        "q7_jhu_masters_cs": 0,
        "q8_top_school_phd_cs_2026": 0,
        "q9_top_school_phd_cs_2026_llm": 0,
        "q10_top_programs": [],
        "q11_acceptance_by_degree": [],
    }
    app = create_app(
        config={"TESTING": True},
        conn_string="fake",
        query_fn=lambda conn: results,
        scraper_fn=lambda: [],
        loader_fn=lambda r, c: 0,
    )
    with app.test_client() as c:
        rv = c.get("/analysis")
    assert b"0.00%" in rv.data
