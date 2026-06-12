"""Shared fake records and expected results used across test modules."""

FAKE_RECORD = {
    "program": "Computer Science, PhD",
    "comments": "Accepted with funding.",
    "date_added": "2026-03-15",
    "url": "https://thegradcafe.com/survey/fake-record-001",
    "status": "Accepted",
    "term": "Fall 2026",
    "US/International": "American",
    "GPA": "3.95",
    "GRE": "165",
    "GRE_V": "162",
    "GRE_AW": "4.5",
    "Degree": "PhD",
    "llm-generated-program": "Computer Science",
    "llm-generated-university": "Johns Hopkins University",
}

FAKE_RECORD_2 = {
    "program": "Computer Science, MS",
    "comments": "Waitlisted.",
    "date_added": "2026-04-01",
    "url": "https://thegradcafe.com/survey/fake-record-002",
    "status": "Waitlisted",
    "term": "Fall 2026",
    "US/International": "International",
    "GPA": "3.80",
    "GRE": "160",
    "GRE_V": "158",
    "GRE_AW": "4.0",
    "Degree": "Masters",
    "llm-generated-program": "Computer Science",
    "llm-generated-university": "MIT",
}

FAKE_RESULTS = {
    "q1_fall_2026_count": 42,
    "q2_pct_international": 39.28,
    "q3_avg_gpa": 3.75,
    "q3_avg_gre": 162.50,
    "q3_avg_gre_v": 158.00,
    "q3_avg_gre_aw": 4.25,
    "q4_avg_gpa_american_fall2026": 3.80,
    "q5_pct_accepted_fall2026": 22.50,
    "q6_avg_gpa_accepted_fall2026": 3.90,
    "q7_jhu_masters_cs": 5,
    "q8_top_school_phd_cs_2026": 3,
    "q9_top_school_phd_cs_2026_llm": 4,
    "q10_top_programs": [{"program": "Computer Science", "count": 100}],
    "q11_acceptance_by_degree": [{"degree": "PhD", "total": 50, "accepted": 20, "rate": 40.00}],
}
