"""
query_data.py
SQL analysis queries for the Grad Cafe applicants dataset.

Public API
----------
run_queries(conn_string) -> dict
    Execute all analysis queries and return results as a dictionary.
"""

import psycopg

EXPECTED_KEYS = [
    "q1_fall_2026_count",
    "q2_pct_international",
    "q3_avg_gpa",
    "q3_avg_gre",
    "q3_avg_gre_v",
    "q3_avg_gre_aw",
    "q4_avg_gpa_american_fall2026",
    "q5_pct_accepted_fall2026",
    "q6_avg_gpa_accepted_fall2026",
    "q7_jhu_masters_cs",
    "q8_top_school_phd_cs_2026",
    "q9_top_school_phd_cs_2026_llm",
    "q10_top_programs",
    "q11_acceptance_by_degree",
]


def run_queries(conn_string: str) -> dict:
    """
    Run all analysis queries against the applicants table.

    Parameters
    ----------
    conn_string:
        psycopg connection string (from DATABASE_URL).

    Returns
    -------
    dict
        Keys match EXPECTED_KEYS; values are ints, floats, or lists of dicts.
    """
    results = {}

    with psycopg.connect(conn_string) as conn:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT COUNT(*)
                FROM applicants
                WHERE date_added >= '2026-01-01';
            """)
            results["q1_fall_2026_count"] = cur.fetchone()[0]

            cur.execute("""
                SELECT ROUND(
                    COUNT(*) FILTER (WHERE us_or_international ILIKE '%international%')
                    * 100.0 / NULLIF(COUNT(*), 0), 2
                )
                FROM applicants;
            """)
            results["q2_pct_international"] = float(cur.fetchone()[0] or 0)

            cur.execute("""
                SELECT
                    ROUND(AVG(gpa)::numeric, 2),
                    ROUND(AVG(gre)::numeric, 2),
                    ROUND(AVG(gre_v)::numeric, 2),
                    ROUND(AVG(gre_aw)::numeric, 2)
                FROM applicants
                WHERE gpa IS NOT NULL
                   OR gre IS NOT NULL
                   OR gre_v IS NOT NULL
                   OR gre_aw IS NOT NULL;
            """)
            row = cur.fetchone()
            results["q3_avg_gpa"]    = float(row[0]) if row[0] else None
            results["q3_avg_gre"]    = float(row[1]) if row[1] else None
            results["q3_avg_gre_v"]  = float(row[2]) if row[2] else None
            results["q3_avg_gre_aw"] = float(row[3]) if row[3] else None

            cur.execute("""
                SELECT ROUND(AVG(gpa)::numeric, 2)
                FROM applicants
                WHERE us_or_international ILIKE '%american%'
                  AND date_added >= '2026-01-01'
                  AND gpa IS NOT NULL;
            """)
            val = cur.fetchone()[0]
            results["q4_avg_gpa_american_fall2026"] = float(val) if val else None

            cur.execute("""
                SELECT ROUND(
                    COUNT(*) FILTER (WHERE status ILIKE '%accept%')
                    * 100.0 / NULLIF(COUNT(*), 0), 2
                )
                FROM applicants
                WHERE date_added >= '2026-01-01';
            """)
            val = cur.fetchone()[0]
            results["q5_pct_accepted_fall2026"] = float(val) if val else 0.0

            cur.execute("""
                SELECT ROUND(AVG(gpa)::numeric, 2)
                FROM applicants
                WHERE date_added >= '2026-01-01'
                  AND status ILIKE '%accept%'
                  AND gpa IS NOT NULL;
            """)
            val = cur.fetchone()[0]
            results["q6_avg_gpa_accepted_fall2026"] = float(val) if val else None

            cur.execute("""
                SELECT COUNT(*)
                FROM applicants
                WHERE (program ILIKE '%Johns Hopkins%' OR program ILIKE '%JHU%')
                  AND degree ILIKE '%master%'
                  AND program ILIKE '%computer science%';
            """)
            results["q7_jhu_masters_cs"] = cur.fetchone()[0]

            top_schools = [
                "Georgetown University", "MIT",
                "Stanford University", "Carnegie Mellon University",
            ]
            school_cond = " OR ".join(f"program ILIKE '%{s}%'" for s in top_schools)
            cur.execute(f"""
                SELECT COUNT(*)
                FROM applicants
                WHERE ({school_cond})
                  AND degree ILIKE '%phd%'
                  AND program ILIKE '%computer science%'
                  AND status ILIKE '%accept%'
                  AND date_added >= '2026-01-01';
            """)
            results["q8_top_school_phd_cs_2026"] = cur.fetchone()[0]

            llm_cond = " OR ".join(
                f"llm_generated_university ILIKE '%{s}%'" for s in top_schools
            )
            cur.execute(f"""
                SELECT COUNT(*)
                FROM applicants
                WHERE ({llm_cond})
                  AND degree ILIKE '%phd%'
                  AND llm_generated_program ILIKE '%computer science%'
                  AND status ILIKE '%accept%'
                  AND date_added >= '2026-01-01';
            """)
            results["q9_top_school_phd_cs_2026_llm"] = cur.fetchone()[0]

            cur.execute("""
                SELECT llm_generated_program, COUNT(*) AS total
                FROM applicants
                WHERE llm_generated_program IS NOT NULL
                  AND llm_generated_program != ''
                GROUP BY llm_generated_program
                ORDER BY total DESC
                LIMIT 5;
            """)
            results["q10_top_programs"] = [
                {"program": r[0], "count": r[1]} for r in cur.fetchall()
            ]

            cur.execute("""
                SELECT
                    degree,
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE status ILIKE '%accept%') AS accepted,
                    ROUND(
                        COUNT(*) FILTER (WHERE status ILIKE '%accept%')
                        * 100.0 / NULLIF(COUNT(*), 0), 2
                    ) AS accept_rate
                FROM applicants
                WHERE degree IS NOT NULL
                GROUP BY degree
                ORDER BY total DESC;
            """)
            results["q11_acceptance_by_degree"] = [
                {"degree": r[0], "total": r[1], "accepted": r[2], "rate": float(r[3] or 0)}
                for r in cur.fetchall()
            ]

    return results
