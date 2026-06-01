"""
run_parallel.py
Parallelized wrapper around app.py's LLM standardization.
Processes only unique 'program' strings (deduplication), then maps
results back to all records — reducing LLM calls by ~2-3x.
Uses multiprocessing across all available CPU cores.

Usage:
    python run_parallel.py --file ../../applicant_data.json --out ../../llm_extend_applicant_data.json
"""

import argparse
import json
import multiprocessing
import os
import sys
from functools import partial


def _init_worker(model_path: str):
    """Load the LLM once per worker process from a pre-downloaded model path."""
    import os
    os.environ["_MODEL_PATH_OVERRIDE"] = model_path
    from app import _load_llm
    _load_llm()


def _process_program(program_text: str) -> tuple[str, dict]:
    """Call the LLM for one program string. Returns (program_text, result)."""
    from app import _call_llm
    try:
        result = _call_llm(program_text)
    except Exception:
        result = {"standardized_program": "", "standardized_university": "Unknown"}
    return program_text, result


def run_parallel(in_path: str, out_path: str, workers: int) -> None:
    print(f"Loading {in_path}...")
    with open(in_path, "r", encoding="utf-8") as f:
        rows = json.load(f)
    if isinstance(rows, dict) and "rows" in rows:
        rows = rows["rows"]

    # Deduplicate program strings to minimize LLM calls
    unique_programs = list({(r.get("program") or "") for r in rows})
    print(f"Total records: {len(rows)} | Unique programs: {len(unique_programs)}")
    print(f"Running with {workers} workers...")

    # Pre-download model ONCE in main process before spawning workers
    print("Downloading model (once)...")
    from huggingface_hub import hf_hub_download
    model_path = hf_hub_download(
        repo_id=os.getenv("MODEL_REPO", "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF"),
        filename=os.getenv("MODEL_FILE", "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"),
        local_dir="models",
    )
    print(f"Model ready at: {model_path}")

    # Process unique programs in parallel, passing model path to each worker
    cache: dict[str, dict] = {}
    with multiprocessing.Pool(
        processes=workers,
        initializer=_init_worker,
        initargs=(model_path,),
    ) as pool:
        for i, (prog, result) in enumerate(
            pool.imap_unordered(_process_program, unique_programs, chunksize=4), 1
        ):
            cache[prog] = result
            if i % 100 == 0 or i == len(unique_programs):
                pct = i / len(unique_programs) * 100
                print(f"  {i}/{len(unique_programs)} ({pct:.1f}%) unique programs done", flush=True)

    # Map cached results back to all records
    print("Mapping results to all records...")
    out_rows = []
    for row in rows:
        prog = row.get("program") or ""
        result = cache.get(prog, {"standardized_program": "", "standardized_university": "Unknown"})
        row["llm-generated-program"] = result["standardized_program"]
        row["llm-generated-university"] = result["standardized_university"]
        out_rows.append(row)

    print(f"Saving to {out_path}...")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out_rows, f, ensure_ascii=False, indent=2)
    print(f"Done. {len(out_rows)} records saved.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Input JSON file")
    parser.add_argument("--out", required=True, help="Output JSON file")
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 4))
    args = parser.parse_args()

    run_parallel(args.file, args.out, args.workers)
