from datetime import datetime
import re

import dateutil.parser
import pandas as pd


TIME_ONLY_RE = re.compile(
    r"^\s*\d{1,2}:\d{1,2}(?::\d{1,2}(?:\.\d+)?)?(?:\s*[AaPp][Mm])?\s*$"
)
ISO_TIMESTAMP_RE = re.compile(
    r"^\s*\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\s*$"
)


def parse_time(time_val) -> datetime | None:
    """Parse supported time or ISO timestamp values, returning a datetime or None."""
    if time_val is None or pd.isna(time_val):
        return None

    time_str = str(time_val).strip()
    if not time_str or time_str.lower() in ("null", "undefined", "nan"):
        return None

    try:
        if ISO_TIMESTAMP_RE.match(time_str):
            dt = dateutil.parser.isoparse(time_str)
        elif TIME_ONLY_RE.match(time_str):
            dt = dateutil.parser.parse(time_str, default=datetime(1900, 1, 1))
        else:
            return None
    except (ValueError, TypeError, OverflowError, dateutil.parser.ParserError):
        return None

    if dt.hour > 23 or dt.minute > 59 or dt.second > 59:
        return None
    return dt


def validate_time(time_val) -> bool:
    """Return True when the value is a supported, valid time representation."""
    return parse_time(time_val) is not None


def normalize_time(time_val) -> tuple[str, str, str]:
    """
    Normalize supported time values to HH:MM:SS.

    Returns:
        cleaned_time: normalized time or ERROR
        severity: INFO or ERROR
        validation_message: Time Standardization, Invalid Time, or Missing Time
    """
    original = "" if time_val is None or pd.isna(time_val) else str(time_val).strip()
    if not original or original.lower() in ("null", "undefined", "nan"):
        return "ERROR", "ERROR", "Missing Time"

    dt = parse_time(original)
    if not dt:
        return "ERROR", "ERROR", "Invalid Time"

    return dt.strftime("%H:%M:%S"), "INFO", "Time Standardization"


def clean_time_val(time_val) -> tuple[str, bool]:
    """Normalize valid time values to HH:MM:SS."""
    original = "" if time_val is None or pd.isna(time_val) else str(time_val).strip()
    cleaned, severity, _ = normalize_time(time_val)
    if severity == "ERROR":
        return original, False

    return cleaned, cleaned != original
