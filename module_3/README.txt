Name: Syrreal Watson | JHED: lwatso28
Module: Module 3 — Databases
Assignment: Grad Cafe PostgreSQL Analysis

================================================================================
REQUIREMENTS
================================================================================
- Python 3.10+
- PostgreSQL 18 installed and running locally
- Module 2 data: llm_extend_applicant_data.json must exist in ../module_2/

================================================================================
SETUP
================================================================================
1. Install dependencies:
       pip install -r requirements.txt

2. Ensure PostgreSQL is running and the gradcafe database exists:
       psql -U postgres -c "CREATE DATABASE gradcafe;"

3. Load Module 2 data into the database:
       python load_data.py

4. Run SQL analysis queries (prints to console):
       python query_data.py

5. Start the Flask web application:
       python run.py
   Then open: http://localhost:8080

================================================================================
DATABASE
================================================================================
Host: localhost | Port: 5432 | Database: gradcafe | User: postgres

Table: applicants
Columns: p_id, program, comments, date_added, url, status, term,
         us_or_international, gpa, gre, gre_v, gre_aw, degree,
         llm_generated_program, llm_generated_university

================================================================================
FLASK WEBPAGE FEATURES
================================================================================
- Displays all 11 query results dynamically from the PostgreSQL database
- "Pull Data" button: runs the Module 2 scraper in the background and adds
  new Grad Cafe entries to the database
- "Update Analysis" button: refreshes the page with latest query results.
  If a data pull is in progress, the button notifies the user and does nothing.

================================================================================
QUERY DESCRIPTIONS (query_data.py)
================================================================================
Q1:  COUNT of entries where term ILIKE '%Fall 2026%'
Q2:  % of entries where us_or_international ILIKE '%international%'
Q3:  AVG of gpa, gre, gre_v, gre_aw across all non-null entries
Q4:  AVG gpa where American + Fall 2026
Q5:  % accepted entries in Fall 2026
Q6:  AVG gpa of accepted Fall 2026 applicants
Q7:  COUNT of JHU Masters CS applicants
Q8:  COUNT of 2026 PhD CS accepts from Georgetown/MIT/Stanford/CMU (raw)
Q9:  Same as Q8 using LLM-generated university/program fields
Q10: Top 5 programs by application volume (custom)
Q11: Acceptance rate by degree type (custom)
