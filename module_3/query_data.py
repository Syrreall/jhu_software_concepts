"""
query_data.py
SQL queries answering required analysis questions about Grad Cafe applicants.
"""

import psycopg
from db_config import get_conn_string


def run_queries() -> dict:
    """Run all analysis queries and return results as a dict."""
    results = {}

    with psycopg.connect(get_conn_string()) as conn:
        with conn.cursor() as cur:

            # Q1: How many entries were added in 2026?
            # Note: GradCafe's table view does not expose the start term
            # (Fall/Spring/etc.) — it is only visible on individual entry pages.
            # We instead count entries added in 2026 as a meaningful proxy.
            cur.execute("""
                SELECT COUNT(*)
                FROM applicants
                WHERE date_added >= '2026-01-01';
            """)
            results["q1_fall_2026_count"] = cur.fetchone()[0]

            # Q2: Percentage of international students (to 2 decimal places)
            cur.execute("""
                SELECT ROUND(
                    COUNT(*) FILTER (WHERE us_or_international ILIKE '%international%')
                    * 100.0 / NULLIF(COUNT(*), 0), 2
                )
                FROM applicants;
            """)
            results["q2_pct_international"] = float(cur.fetchone()[0] or 0)

            # Q3: Average GPA, GRE, GRE V, GRE AW of applicants who provide them
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
            results["q3_avg_gpa"]   = float(row[0]) if row[0] else None
            results["q3_avg_gre"]   = float(row[1]) if row[1] else None
            results["q3_avg_gre_v"] = float(row[2]) if row[2] else None
            results["q3_avg_gre_aw"]= float(row[3]) if row[3] else None

            # Q4: Average GPA of American students in 2026
            cur.execute("""
                SELECT ROUND(AVG(gpa)::numeric, 2)
                FROM applicants
                WHERE us_or_international ILIKE '%american%'
                  AND date_added >= '2026-01-01'
                  AND gpa IS NOT NULL;
            """)
            val = cur.fetchone()[0]
            results["q4_avg_gpa_american_fall2026"] = float(val) if val else None

            # Q5: Percent of 2026 entries that are acceptances
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

            # Q6: Average GPA of accepted 2026 applicants
            cur.execute("""
                SELECT ROUND(AVG(gpa)::numeric, 2)
                FROM applicants
                WHERE date_added >= '2026-01-01'
                  AND status ILIKE '%accept%'
                  AND gpa IS NOT NULL;
            """)
            val = cur.fetchone()[0]
            results["q6_avg_gpa_accepted_fall2026"] = float(val) if val else None

            # Q7: JHU Masters Computer Science applicants
            cur.execute("""
                SELECT COUNT(*)
                FROM applicants
                WHERE (program ILIKE '%Johns Hopkins%' OR program ILIKE '%JHU%')
                  AND degree ILIKE '%master%'
                  AND program ILIKE '%computer science%';
            """)
            results["q7_jhu_masters_cs"] = cur.fetchone()[0]

            # Q8: 2026 PhD CS acceptances from top schools (raw fields)
            top_schools = ['Georgetown University', 'MIT', 'Stanford University', 'Carnegie Mellon University']
            school_conditions = " OR ".join([f"program ILIKE '%{s}%'" for s in top_schools])
            cur.execute(f"""
                SELECT COUNT(*)
                FROM applicants
                WHERE ({school_conditions})
                  AND degree ILIKE '%phd%'
                  AND program ILIKE '%computer science%'
                  AND status ILIKE '%accept%'
                  AND date_added >= '2026-01-01';
            """)
            results["q8_top_school_phd_cs_2026"] = cur.fetchone()[0]

            # Q9: Same as Q8 but using LLM generated fields
            llm_school_conditions = " OR ".join([f"llm_generated_university ILIKE '%{s}%'" for s in top_schools])
            cur.execute(f"""
                SELECT COUNT(*)
                FROM applicants
                WHERE ({llm_school_conditions})
                  AND degree ILIKE '%phd%'
                  AND llm_generated_program ILIKE '%computer science%'
                  AND status ILIKE '%accept%'
                  AND date_added >= '2026-01-01';
            """)
            results["q9_top_school_phd_cs_2026_llm"] = cur.fetchone()[0]

            # Q10 (custom): Most common programs applied to
            cur.execute("""
                SELECT llm_generated_program, COUNT(*) as total
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

            # Q11 (custom): Acceptance rate by degree type
            cur.execute("""
                SELECT
                    degree,
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE status ILIKE '%accept%') as accepted,
                    ROUND(
                        COUNT(*) FILTER (WHERE status ILIKE '%accept%')
                        * 100.0 / NULLIF(COUNT(*), 0), 2
                    ) as accept_rate
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


if __name__ == "__main__":
    print("Running Grad Cafe analysis queries...\n")
    r = run_queries()

    print(f"Q1:  Fall 2026 entries:                    {r['q1_fall_2026_count']}")
    print(f"Q2:  % International students:             {r['q2_pct_international']}%")
    print(f"Q3:  Avg GPA:  {r['q3_avg_gpa']}  |  Avg GRE: {r['q3_avg_gre']}  |  Avg GRE-V: {r['q3_avg_gre_v']}  |  Avg AW: {r['q3_avg_gre_aw']}")
    print(f"Q4:  Avg GPA American students Fall 2026:  {r['q4_avg_gpa_american_fall2026']}")
    print(f"Q5:  % Accepted in Fall 2026:              {r['q5_pct_accepted_fall2026']}%")
    print(f"Q6:  Avg GPA Accepted Fall 2026:           {r['q6_avg_gpa_accepted_fall2026']}")
    print(f"Q7:  JHU Masters CS applicants:            {r['q7_jhu_masters_cs']}")
    print(f"Q8:  Top-school PhD CS 2026 accepts (raw): {r['q8_top_school_phd_cs_2026']}")
    print(f"Q9:  Top-school PhD CS 2026 accepts (LLM): {r['q9_top_school_phd_cs_2026_llm']}")
    print(f"Q10: Top 5 programs applied to:")
    for p in r["q10_top_programs"]:
        print(f"       {p['program']}: {p['count']}")
    print(f"Q11: Acceptance rate by degree:")
    for d in r["q11_acceptance_by_degree"]:
        print(f"       {d['degree']}: {d['rate']}% ({d['accepted']}/{d['total']})")
