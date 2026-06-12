"""
clean.py
Data cleaning pipeline for Grad Cafe applicant records.

Public API
----------
clean_records(records) -> list[dict]
    Accept a list of raw scraped dicts and return cleaned copies.
"""

import html
import re
from typing import Optional


def _clean_text(value: Optional[str]) -> Optional[str]:
    """Strip HTML tags, unescape entities, and normalize whitespace."""
    if value is None:
        return None
    value = html.unescape(str(value))
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value if value else None


def _clean_gpa(value: Optional[str]) -> Optional[str]:
    """Validate and normalize a GPA value (0.00–4.00), or return None."""
    if value is None:
        return None
    raw = re.sub(r"(?i)\bGPA\s*", "", str(value)).strip()
    try:
        gpa = float(raw)
        if 0.0 <= gpa <= 4.0:
            return f"{gpa:.2f}"
    except ValueError:
        pass
    return None


def _clean_gre(value: Optional[str]) -> Optional[str]:
    """Normalize a GRE score string, returning None if out of range."""
    if value is None:
        return None
    raw = re.sub(r"[^\d.]", "", str(value)).strip()
    try:
        score = float(raw)
        if 130 <= score <= 170 or 260 <= score <= 340:
            return str(int(score))
    except ValueError:
        pass
    return None


def clean_record(record: dict) -> dict:
    """
    Clean a single applicant record dict in-place and return it.

    Parameters
    ----------
    record:
        Raw dict from the scraper.

    Returns
    -------
    dict
        Cleaned copy of the record.
    """
    cleaned = dict(record)
    cleaned["program"]  = _clean_text(record.get("program"))
    cleaned["comments"] = _clean_text(record.get("comments"))
    cleaned["status"]   = _clean_text(record.get("status"))
    cleaned["term"]     = _clean_text(record.get("term"))
    cleaned["GPA"]      = _clean_gpa(record.get("GPA"))
    cleaned["GRE"]      = _clean_gre(record.get("GRE"))
    cleaned["GRE_V"]    = _clean_gre(record.get("GRE_V"))
    return cleaned


def clean_records(records: list) -> list:
    """
    Clean a list of raw applicant record dicts.

    Parameters
    ----------
    records:
        List of raw dicts from scrape_gradcafe().

    Returns
    -------
    list[dict]
        List of cleaned record dicts ready for insert_rows().
    """
    return [clean_record(r) for r in records]
