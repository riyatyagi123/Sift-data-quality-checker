from datetime import datetime
import dateutil.parser
import pandas as pd
import re

def parse_date(date_val, dayfirst: bool | None = None) -> datetime:
    """Parses date using dateutil.parser.parse, returning datetime or None."""
    if not date_val or pd.isna(date_val):
        return None
    date_str = str(date_val).strip()
    if not date_str:
        return None
    try:
        # Prevent parsing short digits like "12345" as date
        if date_str.isdigit() and len(date_str) < 8:
            return None
        if dayfirst is not None:
            dt = dateutil.parser.parse(date_str, dayfirst=dayfirst)
        else:
            dt = dateutil.parser.parse(date_str)
        # Convert timezone-aware datetimes to naive for comparison
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except (ValueError, TypeError, OverflowError, IndexError):
        return None

def validate_date(date_str: str, dayfirst: bool | None = None) -> bool:
    """Validates if date is parseable."""
    return parse_date(date_str, dayfirst=dayfirst) is not None

def check_date_warnings(date_str: str, dayfirst: bool | None = None) -> list[dict]:
    """Checks for warnings like future dates or dates before year 2000."""
    dt = parse_date(date_str, dayfirst=dayfirst)
    if not dt:
        return []
        
    warnings = []
    # Future dates
    if dt > datetime.now():
        warnings.append({
            'warning_type': 'future_date',
            'message': f"Future date: {date_str}",
            'severity': 'INFO'
        })
    # Ancient dates
    if dt.year < 2000:
        warnings.append({
            'warning_type': 'ancient_date',
            'message': f"Date before year 2000: {date_str}",
            'severity': 'WARNING'
        })
    return warnings

def clean_date_val(date_val: str, dayfirst: bool | None = None) -> tuple[str, bool]:
    """Standardizes parsed dates to YYYY-MM-DD."""
    dt = parse_date(date_val, dayfirst=dayfirst)
    if not dt:
        return str(date_val).strip(), False
    cleaned = dt.strftime("%Y-%m-%d")
    return cleaned, cleaned != str(date_val).strip()

def infer_date_format_and_confidence(date_strings: list[str]) -> tuple[bool | None, str, float]:
    """
    Infers if the date format is dayfirst (dd-mm-yyyy) or not (mm-dd-yyyy)
    based on a list of date strings.
    Returns:
        dayfirst_inferred: True (dayfirst), False (monthfirst/yyyy-first), or None (inconclusive / mixed)
        detected_format_str: e.g. "dd-mm-yyyy", "mm-dd-yyyy", "yyyy-mm-dd", "mixed", "unknown"
        confidence: float percentage, e.g. 96.0
    """
    valid_dates = []
    for val in date_strings:
        if not val or pd.isna(val):
            continue
        s = str(val).strip()
        if s.isdigit() and len(s) < 8:
            continue
        valid_dates.append(s)
        
    if not valid_dates:
        return None, "unknown", 0.0
        
    dayfirst_votes = 0
    monthfirst_votes = 0
    yyyy_mm_dd_votes = 0
    ambiguous_votes = 0
    total_valid_formats = 0
    
    separators = []
    
    for s in valid_dates:
        # Detect separator
        sep = None
        for char in ['-', '/', '.']:
            if char in s:
                sep = char
                break
        if not sep:
            continue
            
        parts = s.split(sep)
        if len(parts) != 3:
            continue
            
        separators.append(sep)
        total_valid_formats += 1
        
        p1, p2, p3 = parts[0].strip(), parts[1].strip(), parts[2].strip()
        if not (p1.isdigit() and p2.isdigit() and p3.isdigit()):
            continue
            
        val1, val2, val3 = int(p1), int(p2), int(p3)
        
        # Case 1: YYYY-MM-DD
        if len(p1) == 4 or val1 > 31:
            yyyy_mm_dd_votes += 1
        # Case 2: Year is third
        elif len(p3) == 4 or val3 > 31:
            if val1 > 12 and val2 <= 12:
                dayfirst_votes += 1
            elif val1 <= 12 and val2 > 12:
                monthfirst_votes += 1
            else:
                ambiguous_votes += 1
        else:
            ambiguous_votes += 1
            
    if total_valid_formats == 0:
        return None, "unknown", 0.0
        
    most_common_sep = max(set(separators), key=separators.count) if separators else '-'
    
    total_non_ambiguous = dayfirst_votes + monthfirst_votes + yyyy_mm_dd_votes
    
    if total_non_ambiguous == 0:
        return None, "Mixed Formats", 50.0
        
    dayfirst_ratio = dayfirst_votes / total_non_ambiguous
    monthfirst_ratio = monthfirst_votes / total_non_ambiguous
    yyyy_mm_dd_ratio = yyyy_mm_dd_votes / total_non_ambiguous
    
    ratios = {
        'yyyy': (yyyy_mm_dd_ratio, False, f"yyyy{most_common_sep}mm{most_common_sep}dd"),
        'dd': (dayfirst_ratio, True, f"dd{most_common_sep}mm{most_common_sep}yyyy"),
        'mm': (monthfirst_ratio, False, f"mm{most_common_sep}dd{most_common_sep}yyyy")
    }
    
    sorted_formats = sorted(ratios.items(), key=lambda item: item[1][0], reverse=True)
    best_key, (best_ratio, best_dayfirst, best_fmt_str) = sorted_formats[0]
    
    confidence = best_ratio * 100
    if confidence > 90.0:
        confidence = 95.0 + (confidence - 90.0) * 0.4
        
    num_formats_with_votes = sum(1 for r, _, _ in ratios.values() if r > 0.05)
    
    if num_formats_with_votes > 1:
        if best_ratio > 0.5:
            return best_dayfirst, f"Dominant Format: {best_fmt_str}", round(confidence, 1)
        else:
            return None, "Mixed Formats", round(confidence, 1)
    else:
        return best_dayfirst, best_fmt_str, round(confidence, 1)
