"""
clean.py
Data cleaning pipeline for Grad Cafe applicant data.
"""

import html
import json
import re

INPUT_FILE = "applicant_data.json"
OUTPUT_FILE = "applicant_data_cleaned.json"


# ── Field-level cleaners ───────────────────────────────────────────────────────
def _clean_text(value: str | None) -> str | None:
    """Strip HTML tags, unescape entities, and normalize whitespace."""
    if value is None:
        return None
    value = html.unescape(str(value))
    value = re.sub(r"<[^>]+>", "", value)         # remove any residual HTML tags
    value = re.sub(r"\s+", " ", value).strip()
    return value if value else None


def _clean_gpa(value: str | None) -> str | None:
    """Validate and normalize a GPA value to two decimal places (0.00–4.00)."""
    if value is None:
        return None
    # Strip 'GPA' prefix if present
    raw = re.sub(r"(?i)\bGPA\s*", "", str(value)).strip()
    try:
        gpa = float(raw)
        if 0.0 <= gpa <= 4.0:
            return f"{gpa:.2f}"
    except (ValueError, TypeError):
        pass
    return None


def _clean_gre_section(value: str | None) -> str | None:
    """Validate a GRE section score (130–170)."""
    if value is None:
        return None
    try:
        score = int(str(value).strip())
        if 130 <= score <= 170:
            return str(score)
    except (ValueError, TypeError):
        pass
    return None


def _clean_gre_total(value: str | None) -> str | None:
    """Validate a GRE total score (260–340)."""
    if value is None:
        return None
    try:
        score = int(str(value).strip())
        if 260 <= score <= 340:
            return str(score)
    except (ValueError, TypeError):
        pass
    return None


def _clean_gre_aw(value: str | None) -> str | None:
    """Validate a GRE Analytical Writing score (0.0–6.0)."""
    if value is None:
        return None
    try:
        score = float(str(value).strip())
        if 0.0 <= score <= 6.0:
            return f"{score:.1f}"
    except (ValueError, TypeError):
        pass
    return None


def _normalize_status(status: str | None) -> str | None:
    """Normalize applicant decision to a canonical label."""
    if status is None:
        return None
    mapping = {
        "accept":    "Accepted",
        "reject":    "Rejected",
        "waitlist":  "Wait listed",
        "wait list": "Wait listed",
        "wait-list": "Wait listed",
        "interview": "Interview",
    }
    lower = status.lower()
    for key, val in mapping.items():
        if key in lower:
            return val
    return status.strip()


def _normalize_degree(degree: str | None) -> str | None:
    """Normalize degree to 'Masters' or 'PhD'."""
    if degree is None:
        return None
    t = degree.lower()
    if re.search(r"\bphd\b|\bph\.d\b|\bdoctoral?\b", t):
        return "PhD"
    if re.search(r"\bmaster\b|\bm\.s\b|\bm\.a\b|\bmeng\b|\bmba\b|\bm\.eng\b|\bmfa\b", t):
        return "Masters"
    return degree.strip()


# ── Record-level cleaner ───────────────────────────────────────────────────────
def _clean_record(raw: dict) -> dict:
    """Apply all cleaning steps to a single raw applicant record."""
    return {
        # Original program kept for traceability/reproducibility
        "program":          _clean_text(raw.get("program")),
        "status":           _normalize_status(raw.get("status")),
        "term":             _clean_text(raw.get("term")),
        "date_added":       _clean_text(raw.get("date_added")),
        "url":              raw.get("url"),
        "Degree":           _normalize_degree(_clean_text(raw.get("Degree"))),
        "US/International": _clean_text(raw.get("US/International")),
        "GPA":              _clean_gpa(raw.get("GPA")),
        "GRE":              _clean_gre_total(raw.get("GRE")),
        "GRE_V":            _clean_gre_section(raw.get("GRE_V")),
        "GRE_AW":           _clean_gre_aw(raw.get("GRE_AW")),
        "comments":         _clean_text(raw.get("comments")),
        "raw_text":         raw.get("raw_text"),  # preserved, not modified
    }


# ── Public API ─────────────────────────────────────────────────────────────────
def clean_data(data: list[dict]) -> list[dict]:
    """Clean a list of raw applicant records and return cleaned records."""
    return [_clean_record(record) for record in data]


def save_data(data: list[dict], filename: str = OUTPUT_FILE) -> None:
    """Write cleaned applicant data to a JSON file."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_data(filename: str = INPUT_FILE) -> list[dict]:
    """Load applicant data from a JSON file."""
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    print(f"Loading {INPUT_FILE}...")
    raw = load_data(INPUT_FILE)
    print(f"Cleaning {len(raw)} records...")
    cleaned = clean_data(raw)
    save_data(cleaned)
    print(f"Saved cleaned data to {OUTPUT_FILE}")
