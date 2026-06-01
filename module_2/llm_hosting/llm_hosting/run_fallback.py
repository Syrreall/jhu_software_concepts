"""
run_fallback.py
Produces llm_extend_applicant_data.json using the rule-based fallback
from app.py (_split_fallback + canonical list matching) when the LLM
cannot finish in time. Runs in seconds instead of hours.
"""

import json
import sys
import os

# Add app.py's directory to path
sys.path.insert(0, os.path.dirname(__file__))

from app import _split_fallback, _post_normalize_program, _post_normalize_university


def run_fallback(in_path: str, out_path: str) -> None:
    print(f"Loading {in_path}...")
    with open(in_path, "r", encoding="utf-8") as f:
        rows = json.load(f)

    print(f"Processing {len(rows)} records with rule-based fallback...")
    out_rows = []
    for i, row in enumerate(rows):
        program_text = (row.get("program") or "").strip()
        prog, uni = _split_fallback(program_text)
        prog = _post_normalize_program(prog)
        uni = _post_normalize_university(uni)
        row["llm-generated-program"] = prog
        row["llm-generated-university"] = uni
        out_rows.append(row)
        if (i + 1) % 5000 == 0:
            print(f"  {i+1}/{len(rows)} records processed")

    print(f"Saving to {out_path}...")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out_rows, f, ensure_ascii=False, indent=2)
    print(f"Done. {len(out_rows)} records saved.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    run_fallback(args.file, args.out)
