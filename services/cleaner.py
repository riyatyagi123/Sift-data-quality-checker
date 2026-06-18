import os
import re
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime

from services.validator import (
    validate_csv,
    resolve_columns,
    is_missing_value,
    preprocess_csv,
    classify_dataset,
    normalize_numeric_string,
    validate_numeric,
    validate_text,
    is_known_payment_mode,
    validate_currency
)
from services.phone_validator import clean_phone_val, get_country_key, load_country_rules, validate_phone
from services.date_validator import clean_date_val, validate_date, check_date_warnings, infer_date_format_and_confidence
from services.time_validator import normalize_time
from services.email_validator import validate_email
from services.duplicate_detector import build_business_key_frame
from services.quality_score import calculate_overall_score, classify_quality_rating

logger = logging.getLogger(__name__)

# Phase 10: Helper functions
def clean_phone(phone_val: str, country_val: str) -> tuple[str, bool]:
    """Cleans phone numbers: strips prefixes and formats local details."""
    return clean_phone_val(phone_val, country_val)

def clean_date(date_val: str, dayfirst: bool | None = None) -> tuple[str, bool]:
    """Standardizes parsed date to YYYY-MM-DD."""
    return clean_date_val(date_val, dayfirst=dayfirst)

def clean_email(email_val: str) -> tuple[str, bool]:
    """Trims spaces, lowercases, and checks email validity."""
    if not email_val or pd.isna(email_val):
        return "", False
    original = str(email_val).strip()
    cleaned = re.sub(r'\s+', '', original).lower()
    if validate_email(cleaned):
        return cleaned, cleaned != original
    return original, False

def clean_currency(val: str) -> tuple[str, bool]:
    """Standardizes currencies to upper-case ISO codes."""
    if not val or pd.isna(val):
        return "", False
    original = str(val).strip()
    cleaned = original.upper()
    mapping = {
        'USD': 'USD', '$': 'USD',
        'INR': 'INR', 'RS': 'INR',
        'AED': 'AED'
    }
    mapped = mapping.get(cleaned)
    if mapped:
        return mapped, mapped != original
    return original, False

def clean_payment_mode(val: str) -> tuple[str, bool]:
    """Maps custom payment terms to standardized values."""
    if not val or pd.isna(val):
        return "", False
    original = str(val).strip()
    cleaned = original.lower()
    mapping = {
        'card': 'Credit Card',
        'credit card': 'Credit Card',
        'upi payment': 'UPI',
        'upi': 'UPI',
        'wire': 'Bank Transfer',
        'bank transfer': 'Bank Transfer',
        'cash': 'COD',
        'cod': 'COD'
    }
    mapped = mapping.get(cleaned)
    if mapped:
        return mapped, mapped != original
    return original, False

def clean_country(val: str) -> tuple[str, bool]:
    """Maps country codes or abbreviations to full names."""
    if not val or pd.isna(val):
        return "", False
    original = str(val).strip()
    cleaned = original.upper()
    mapping = {
        'IN': 'India', 'INDIA': 'India',
        'USA': 'United States', 'US': 'United States', 'UNITED STATES': 'United States',
        'AE': 'United Arab Emirates', 'UNITED ARAB EMIRATES': 'United Arab Emirates',
        'SG': 'Singapore', 'SINGAPORE': 'Singapore',
        'UK': 'United Kingdom', 'UNITED KINGDOM': 'United Kingdom',
        'AU': 'Australia', 'AUSTRALIA': 'Australia'
    }
    mapped = mapping.get(cleaned)
    if mapped:
        return mapped, mapped != original
    return original, False

def dayfirst_for_country(country_val: str, fallback: bool | None = None) -> bool | None:
    """US dates are month-first; other countries keep the existing inferred behavior."""
    return False if get_country_key(country_val) == 'US' else fallback

def clean_text(val: str) -> tuple[str, bool]:
    """Removes unicode control codes, binary corruption, and trims excessive spaces."""
    if not val or pd.isna(val):
        return "", False
    original = str(val)
    # Replace tabs/newlines with spaces, remove non-printable chars
    cleaned = re.sub(r'[\t\r\n]+', ' ', original)
    cleaned = re.sub(r'[^\x20-\x7E]', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned, cleaned != original

PRESERVE_ABBREVIATIONS = {
    "ID", "USD", "EUR", "AED", "GBP", "AUD", "UAE", "UPI", "PAYPAL", "SGD"
}

def title_case_with_abbreviations(text: str) -> str:
    tokens = re.split(r'(\b\w+\b)', text)
    result = []
    for token in tokens:
        if token.isalnum():
            upper_tok = token.upper()
            if upper_tok in PRESERVE_ABBREVIATIONS:
                result.append(upper_tok)
            else:
                result.append(token.capitalize())
        else:
            result.append(token)
    return "".join(result)

def clean_name(val: str) -> tuple[str, bool]:
    """Standardizes names to Title Case and cleans whitespace."""
    cleaned, corrected = clean_text(val)
    title_cleaned = title_case_with_abbreviations(cleaned)
    return title_cleaned, title_cleaned != str(val)

# Phase 2: Empty Row Checker
def is_empty_row(row_dict: dict) -> bool:
    """Returns True if every cell in the row is empty or a null/nan indicator."""
    empty_indicators = {'', 'null', 'undefined', 'nan', 'none'}
    for val in row_dict.values():
        if str(val).strip().lower() not in empty_indicators:
            return False
    return True

def remove_cleaned_business_duplicates(output_filepath: str, duplicates_path: str, audit_trail: list) -> int:
    """Removes duplicate business records from the fully cleaned output CSV."""
    if not os.path.exists(output_filepath) or os.path.getsize(output_filepath) == 0:
        return 0

    cleaned_df = pd.read_csv(output_filepath, dtype=str).fillna('')
    if cleaned_df.empty:
        return 0

    business_df, business_key_columns = build_business_key_frame(cleaned_df)
    if not business_key_columns:
        return 0

    duplicate_mask = business_df.duplicated(keep='first')
    duplicates_removed = int(duplicate_mask.sum())
    if duplicates_removed == 0:
        return 0

    duplicate_rows = cleaned_df.loc[duplicate_mask].copy()
    cleaned_df.loc[~duplicate_mask].to_csv(output_filepath, index=False)
    duplicate_rows.to_csv(
        duplicates_path,
        mode='a',
        index=False,
        header=not os.path.exists(duplicates_path)
    )

    for original_idx, row in duplicate_rows.iterrows():
        audit_trail.append({
            'row': int(original_idx) + 1,
            'column': 'Entire_Row',
            'original': json.dumps(row.to_dict(), ensure_ascii=True),
            'cleaned': 'DELETED',
            'action': 'Duplicate Removed',
            'severity': 'INFO'
        })

    return duplicates_removed

# Two-pass analyzer for memory efficiency & global stats
def analyze_csv_globally(input_filepath, col_map, column_types, dataset_type):
    """
    Analyzes the CSV to discover global duplicate IDs,
    100% empty columns, and median/mode values for imputation.
    """
    txn_col = col_map.get('transaction_id')
    email_col = col_map.get('email')
    phone_col = col_map.get('phone_number')
    cust_col = col_map.get('customer_id')
    
    dup_col = txn_col if dataset_type != "Customer Dataset" else cust_col
    
    # 1. Duplicates Count
    from collections import Counter
    id_counts = Counter()
    
    try:
        df_head = pd.read_csv(input_filepath, nrows=5)
        all_cols = list(df_head.columns)
    except Exception:
        return set(), {}, [], None
        
    if dup_col and dup_col in all_cols:
        for chunk in pd.read_csv(input_filepath, usecols=[dup_col], chunksize=50000, dtype=str):
            vals = chunk[dup_col].dropna().apply(lambda x: str(x).strip())
            id_counts.update(vals)
            
    duplicate_keys = {k for k, count in id_counts.items() if count > 1 and k}
    
    # 2. Imputation and Empty Columns
    global_imputation_data = {}
    empty_cols_detected = []
    mandatory_cols = {col_map.get('customer_id'), col_map.get('transaction_id'), col_map.get('email'), col_map.get('phone_number')}
    
    for col in all_cols:
        col_type = column_types.get(col, 'Text')
        try:
            # Read single column for memory-safety
            col_df = pd.read_csv(input_filepath, usecols=[col], dtype=str).dropna()
            valid_vals = col_df[col].apply(lambda x: str(x).strip())
            valid_vals = valid_vals[~valid_vals.str.lower().isin(['', 'null', 'nan', 'none', 'undefined'])]
            
            if valid_vals.empty:
                empty_cols_detected.append(col)
                continue
                
            if col in mandatory_cols:
                continue
                
            if col_type == 'Numeric':
                nums = pd.to_numeric(valid_vals, errors='coerce').dropna()
                if not nums.empty:
                    med = nums.median()
                    global_imputation_data[col] = str(int(med)) if med.is_integer() else str(med)
            else:
                mode_val = valid_vals.mode()
                if not mode_val.empty:
                    global_imputation_data[col] = mode_val.iloc[0]
        except Exception as e:
            logger.warning(f"Failed to resolve global stats for column {col}: {e}")
            
    # Date format inference
    dayfirst_inferred = None
    detected_format = "unknown"
    confidence = 0.0
    date_col = col_map.get('transaction_date')
    if date_col and date_col in all_cols:
        try:
            col_df = pd.read_csv(input_filepath, usecols=[date_col], nrows=20000, dtype=str).dropna()
            date_strings = col_df[date_col].apply(lambda x: str(x).strip()).tolist()
            dayfirst_inferred, detected_format, confidence = infer_date_format_and_confidence(date_strings)
        except Exception as e:
            logger.warning(f"Failed to infer date format globally: {e}")
            
    return duplicate_keys, global_imputation_data, empty_cols_detected, dup_col, dayfirst_inferred, detected_format, confidence

def clean_csv(input_filepath: str, output_filepath: str, removed_filepath: str, mode: str = 'SMART') -> dict:
    """
    Orchestrates the cleaning process chunk-by-chunk.
    Supports STRICT, SMART, and SOFT modes.
    Outputs:
      - cleaned.csv
      - errors.csv
      - warnings.csv
      - duplicates.csv
      - audit_report.json
      - removed_columns.json
    """
    preprocess_csv(input_filepath)
    validation_results = validate_csv(input_filepath)
    col_map = validation_results['column_mapping']
    column_types = validation_results['column_types']
    dataset_type = validation_results['dataset_type']
    
    # Run two-pass analyzer
    duplicate_keys, global_impute, empty_cols, dup_col, dayfirst_inferred, detected_format, confidence = analyze_csv_globally(
        input_filepath, col_map, column_types, dataset_type
    )
    
    # Columns definition
    phone_col = col_map.get('phone_number')
    country_col = col_map.get('country')
    date_col = col_map.get('transaction_date')
    time_col = col_map.get('transaction_time')
    email_col = col_map.get('email')
    txn_col = col_map.get('transaction_id')
    cust_col = col_map.get('customer_id')
    name_col = col_map.get('customer_name')
    amt_col = col_map.get('amount')
    curr_col = col_map.get('currency')
    pay_col = col_map.get('payment_mode')
    
    mandatory_fields = (
        ['customer_id', 'customer_name', 'phone_number', 'transaction_date', 'email']
        if dataset_type == "Customer Dataset"
        else ['transaction_id', 'customer_id', 'country', 'phone_number', 'transaction_date', 'amount']
    )
    
    # Stats counters
    stats = {
        'total_processed': 0,
        'rows_corrected': 0,
        'rows_removed': 0,
        'rows_retained': 0,
        'phones_fixed': 0,
        'emails_fixed': 0,
        'dates_fixed': 0,
        'times_fixed': 0,
        'currencies_fixed': 0,
        'countries_fixed': 0,
        'payment_modes_fixed': 0,
        'duplicates_removed': 0,
        'empty_rows_removed': 0,
        'empty_columns_removed': len(empty_cols),
        'rows_imputed': 0,
        'success_rate': 0.0
    }
    
    audit_trail = []
    
    # Set up output paths
    folder = os.path.dirname(output_filepath)
    os.makedirs(folder, exist_ok=True)
    base_name = os.path.basename(input_filepath)
    name, ext = os.path.splitext(base_name)
    
    errors_path = os.path.join(folder, f"{name}_errors{ext}")
    warnings_path = os.path.join(folder, f"{name}_warnings{ext}")
    duplicates_path = os.path.join(folder, f"{name}_duplicates{ext}")
    removed_cols_path = os.path.join(folder, f"{name}_removed_columns.json")
    audit_report_path = os.path.join(folder, f"{name}_audit_report.json")
    
    # Clean previous output files
    for path in [output_filepath, errors_path, warnings_path, duplicates_path]:
        if os.path.exists(path):
            os.remove(path)
            
    # Write empty removed_columns.json
    with open(removed_cols_path, 'w') as f:
        json.dump({'removed_columns': empty_cols}, f, indent=2)
        
    try:
        reader = pd.read_csv(input_filepath, dtype=str, chunksize=50000)
    except Exception as e:
        logger.error(f"Error reading dataset chunk-by-chunk: {e}")
        return {}
        
    # Headers list for outputs
    first_chunk = True
    col_headers = []
    
    for chunk in reader:
        chunk = chunk.fillna('')
        if first_chunk:
            col_headers = list(chunk.columns)
            # Remove empty columns globally from target header list
            cleaned_headers = [c for c in col_headers if c not in empty_cols]
            if mode == 'SOFT':
                cleaned_headers.append('status')
            first_chunk = False
            
        retained_chunk_rows = []
        error_chunk_rows = []
        warning_chunk_rows = []
        duplicate_chunk_rows = []
        
        for idx, pd_row in chunk.iterrows():
            row_dict = pd_row.to_dict()
            
            # Phase 2: Empty row check
            if is_empty_row(row_dict):
                stats['empty_rows_removed'] += 1
                continue
                
            stats['total_processed'] += 1
            row_num = stats['total_processed']
            
            # Phase 1: Duplicates Check
            is_dup = False
            if dup_col and row_dict.get(dup_col):
                val = str(row_dict[dup_col]).strip()
                if val in duplicate_keys:
                    is_dup = True
                    
            if is_dup:
                row_dup = row_dict.copy()
                for ec in empty_cols:
                    if ec in row_dup:
                        del row_dup[ec]
                duplicate_chunk_rows.append(row_dup)
                stats['duplicates_removed'] += 1
                
                audit_trail.append({
                    'row': row_num,
                    'column': dup_col,
                    'original': row_dict.get(dup_col),
                    'cleaned': 'DELETED',
                    'action': 'duplicate_removal',
                    'severity': 'ERROR'
                })
                
                if mode in ['STRICT', 'SMART']:
                    stats['rows_removed'] += 1
                    continue
                elif mode == 'SOFT':
                    row_dup['status'] = 'CRITICAL'
                    retained_chunk_rows.append(row_dup)
                    stats['rows_retained'] += 1
                    continue
                    
            # Row modifications tracking
            row_was_corrected = False
            row_errors = []
            row_warnings = []
            
            # Drop 100% empty columns from row content
            for ec in empty_cols:
                if ec in row_dict:
                    del row_dict[ec]
                    
            # Imputations & Cleanings
            for field, col_name in col_map.items():
                if not col_name or col_name not in row_dict:
                    continue
                    
                val = str(row_dict[col_name]).strip()
                is_missing = is_missing_value(val)

                if is_missing and field == 'transaction_time':
                    date_source_val = str(row_dict.get(date_col, '')).strip() if date_col else ''
                    extracted_time, _, _ = normalize_time(date_source_val)
                    if extracted_time != 'ERROR':
                        row_dict[col_name] = extracted_time
                        stats['times_fixed'] += 1
                        row_was_corrected = True
                        audit_trail.append({
                            'row': row_num,
                            'column': col_name,
                            'original': date_source_val,
                            'cleaned': extracted_time,
                            'action': 'Time Extraction',
                            'severity': 'INFO'
                        })
                        continue

                    normalized_time, time_severity, time_message = normalize_time(val)
                    row_dict[col_name] = normalized_time
                    row_errors.append({
                        'column': col_name,
                        'original': val,
                        'message': time_message,
                        'severity': time_severity
                    })
                    continue

                if is_missing and field == 'transaction_date':
                    row_dict[col_name] = 'ERROR'
                    row_errors.append({
                        'column': col_name,
                        'original': val,
                        'message': 'Missing Date',
                        'severity': 'ERROR'
                    })
                    continue
                
                # Phase 4: Optional Imputation (SMART mode only)
                if is_missing and mode == 'SMART' and col_name in global_impute:
                    impute_val = global_impute[col_name]
                    row_dict[col_name] = impute_val
                    stats['rows_imputed'] += 1
                    row_was_corrected = True
                    
                    audit_trail.append({
                        'row': row_num,
                        'column': col_name,
                        'original': '',
                        'cleaned': impute_val,
                        'action': 'missing_imputation',
                        'severity': 'INFO'
                    })
                    val = impute_val
                    is_missing = False
                    
                if is_missing:
                    # Missing mandatory identifier
                    if field in mandatory_fields:
                        row_errors.append({
                            'column': col_name,
                            'original': val,
                            'message': 'Missing mandatory field',
                            'severity': 'CRITICAL'
                        })
                    else:
                        row_warnings.append(f"Missing optional: {col_name}")
                    continue
                    
                # Standard Correction/Cleaning
                corrected = False
                cleaned_val = val
                
                if field == 'phone_number':
                    c_val = str(row_dict.get(country_col, '')).strip() if country_col else ''
                    if not validate_phone(val, c_val):
                        if mode == 'SMART':
                            cleaned_val, corrected = clean_phone(val, c_val)
                            if corrected and validate_phone(cleaned_val, c_val):
                                stats['phones_fixed'] += 1
                            else:
                                row_errors.append({
                                    'column': col_name,
                                    'original': val,
                                    'message': 'Invalid phone format',
                                    'severity': 'ERROR'
                                })
                        else:
                            row_errors.append({
                                'column': col_name,
                                'original': val,
                                'message': 'Invalid phone format',
                                'severity': 'ERROR'
                            })
                    else:
                        cleaned_val, corrected = clean_phone(val, c_val)
                        if corrected:
                            stats['phones_fixed'] += 1
                            
                    if corrected:
                        row_dict[col_name] = cleaned_val
                        row_was_corrected = True
                        audit_trail.append({
                            'row': row_num,
                            'column': col_name,
                            'original': val,
                            'cleaned': cleaned_val,
                            'action': 'phone_normalization',
                            'severity': 'INFO'
                        })
                        
                elif field == 'transaction_date':
                    country_val = str(row_dict.get(country_col, '')).strip() if country_col else ''
                    row_dayfirst = dayfirst_for_country(country_val, dayfirst_inferred)
                    if not validate_date(val, dayfirst=row_dayfirst):
                        if mode == 'SMART':
                            cleaned_val, corrected = clean_date(val, dayfirst=row_dayfirst)
                            if corrected and validate_date(cleaned_val, dayfirst=row_dayfirst):
                                stats['dates_fixed'] += 1
                            else:
                                row_errors.append({
                                    'column': col_name,
                                    'original': val,
                                    'message': 'Invalid date',
                                    'severity': 'ERROR'
                                })
                        else:
                            row_errors.append({
                                'column': col_name,
                                'original': val,
                                'message': 'Invalid date',
                                'severity': 'ERROR'
                            })
                    else:
                        cleaned_val, corrected = clean_date(val, dayfirst=row_dayfirst)
                        if corrected:
                            stats['dates_fixed'] += 1
                            
                    if corrected:
                        row_dict[col_name] = cleaned_val
                        row_was_corrected = True
                        audit_trail.append({
                            'row': row_num,
                            'column': col_name,
                            'original': val,
                            'cleaned': cleaned_val,
                            'action': 'date_standardization',
                            'severity': 'INFO'
                        })

                    if time_col and time_col in row_dict and is_missing_value(row_dict.get(time_col)):
                        extracted_time, _, _ = normalize_time(val)
                        if extracted_time != 'ERROR':
                            row_dict[time_col] = extracted_time
                            stats['times_fixed'] += 1
                            row_was_corrected = True
                            audit_trail.append({
                                'row': row_num,
                                'column': time_col,
                                'original': val,
                                'cleaned': extracted_time,
                                'action': 'Time Extraction',
                                'severity': 'INFO'
                            })
                        
                    # Check warnings on dates
                    if validate_date(cleaned_val, dayfirst=row_dayfirst):
                        date_warns = check_date_warnings(cleaned_val, dayfirst=row_dayfirst)
                        for dw in date_warns:
                            row_warnings.append(dw['message'])

                elif field == 'transaction_time':
                    normalized_time, time_severity, time_message = normalize_time(val)
                    if time_severity == 'ERROR':
                        row_dict[col_name] = normalized_time
                        row_errors.append({
                            'column': col_name,
                            'original': val,
                            'message': time_message,
                            'severity': time_severity
                        })
                    else:
                        cleaned_val = normalized_time
                        corrected = cleaned_val != val
                        if corrected:
                            stats['times_fixed'] += 1

                    if corrected:
                        row_dict[col_name] = cleaned_val
                        row_was_corrected = True
                        audit_trail.append({
                            'row': row_num,
                            'column': col_name,
                            'original': val,
                            'cleaned': cleaned_val,
                            'action': time_message,
                            'severity': time_severity
                        })
                            
                elif field == 'email':
                    if not validate_email(val):
                        if mode == 'SMART':
                            cleaned_val, corrected = clean_email(val)
                            if corrected and validate_email(cleaned_val):
                                stats['emails_fixed'] += 1
                            else:
                                row_errors.append({
                                    'column': col_name,
                                    'original': val,
                                    'message': 'Invalid email format',
                                    'severity': 'ERROR'
                                })
                        else:
                            row_errors.append({
                                'column': col_name,
                                'original': val,
                                'message': 'Invalid email format',
                                'severity': 'ERROR'
                            })
                    else:
                        cleaned_val, corrected = clean_email(val)
                        if corrected:
                            stats['emails_fixed'] += 1
                            
                    if corrected:
                        row_dict[col_name] = cleaned_val
                        row_was_corrected = True
                        audit_trail.append({
                            'row': row_num,
                            'column': col_name,
                            'original': val,
                            'cleaned': cleaned_val,
                            'action': 'email_cleanup',
                            'severity': 'INFO'
                        })
                        
                elif field == 'currency':
                    cleaned_val, corrected = clean_currency(val)
                    if corrected:
                        stats['currencies_fixed'] += 1
                        row_dict[col_name] = cleaned_val
                        row_was_corrected = True
                        audit_trail.append({
                            'row': row_num,
                            'column': col_name,
                            'original': val,
                            'cleaned': cleaned_val,
                            'action': 'currency_mapping',
                            'severity': 'INFO'
                        })
                    if not validate_currency(cleaned_val):
                        row_errors.append({
                            'column': col_name,
                            'original': val,
                            'message': 'Unsupported currency code',
                            'severity': 'ERROR'
                        })
                        
                elif field == 'payment_mode':
                    cleaned_val, corrected = clean_payment_mode(val)
                    if corrected:
                        stats['payment_modes_fixed'] += 1
                        row_dict[col_name] = cleaned_val
                        row_was_corrected = True
                        audit_trail.append({
                            'row': row_num,
                            'column': col_name,
                            'original': val,
                            'cleaned': cleaned_val,
                            'action': 'payment_mode_mapping',
                            'severity': 'INFO'
                        })
                    if not is_known_payment_mode(cleaned_val):
                        row_errors.append({
                            'column': col_name,
                            'original': val,
                            'message': 'Unsupported payment mode',
                            'severity': 'ERROR'
                        })
                        
                elif field == 'country':
                    cleaned_val, corrected = clean_country(val)
                    if corrected:
                        stats['countries_fixed'] += 1
                        row_dict[col_name] = cleaned_val
                        row_was_corrected = True
                        audit_trail.append({
                            'row': row_num,
                            'column': col_name,
                            'original': val,
                            'cleaned': cleaned_val,
                            'action': 'country_mapping',
                            'severity': 'INFO'
                        })
                        
                elif field == 'customer_name':
                    cleaned_val, corrected = clean_name(val)
                    if corrected:
                        row_dict[col_name] = cleaned_val
                        row_was_corrected = True
                        audit_trail.append({
                            'row': row_num,
                            'column': col_name,
                            'original': val,
                            'cleaned': cleaned_val,
                            'action': 'whitespace_trim',
                            'severity': 'INFO'
                        })
                        
                elif field == 'amount':
                    if dataset_type != "Customer Dataset":
                        if not validate_numeric(val):
                            row_errors.append({
                                'column': col_name,
                                'original': val,
                                'message': 'Invalid numeric amount',
                                'severity': 'ERROR'
                            })
                        else:
                            norm_amt = float(normalize_numeric_string(val))
                            if norm_amt < 0:
                                row_errors.append({
                                    'column': col_name,
                                    'original': val,
                                    'message': 'Negative amount',
                                    'severity': 'ERROR'
                                })
                else:
                    # General Text Cleanups
                    cleaned_val, corrected = clean_text(val)
                    if corrected:
                        row_dict[col_name] = cleaned_val
                        row_was_corrected = True
                        audit_trail.append({
                            'row': row_num,
                            'column': col_name,
                            'original': val,
                            'cleaned': cleaned_val,
                            'action': 'whitespace_trim',
                            'severity': 'INFO'
                        })
                        
            if row_was_corrected:
                stats['rows_corrected'] += 1
                
            # Keep log collections of warnings and errors
            if row_errors:
                error_chunk_rows.append(row_dict)
                for err in row_errors:
                    audit_trail.append({
                        'row': row_num,
                        'column': err['column'],
                        'original': err['original'],
                        'cleaned': 'ERROR',
                        'action': err['message'],
                        'severity': err['severity']
                    })
            elif row_warnings:
                warning_chunk_rows.append(row_dict)
                
            # Modes Logic
            if mode == 'STRICT':
                if not row_errors and not row_warnings:
                    retained_chunk_rows.append(row_dict)
                    stats['rows_retained'] += 1
                else:
                    stats['rows_removed'] += 1
            elif mode == 'SMART':
                if not row_errors:
                    retained_chunk_rows.append(row_dict)
                    stats['rows_retained'] += 1
                else:
                    stats['rows_removed'] += 1
            elif mode == 'SOFT':
                status = 'VALID'
                if row_errors:
                    status = 'ERROR'
                elif row_warnings:
                    status = 'WARNING'
                row_dict['status'] = status
                retained_chunk_rows.append(row_dict)
                stats['rows_retained'] += 1
                
        # Append chunk data to files
        def append_to_csv(data_list, path, headers):
            if not data_list:
                return
            df = pd.DataFrame(data_list, columns=headers)
            write_header = not os.path.exists(path)
            df.to_csv(path, mode='a', index=False, header=write_header)
            
        append_to_csv(retained_chunk_rows, output_filepath, cleaned_headers)
        append_to_csv(error_chunk_rows, errors_path, [h for h in col_headers if h not in empty_cols])
        append_to_csv(warning_chunk_rows, warnings_path, [h for h in col_headers if h not in empty_cols])
        append_to_csv(duplicate_chunk_rows, duplicates_path, [h for h in col_headers if h not in empty_cols])
        
    # Write backward compatibility removed.csv (equals errors + warning for STRICT, errors for SMART)
    # Since it is a smaller file generally, we can just copy errors or read it
    if mode == 'STRICT':
        # concat errors and warnings
        try:
            e_df = pd.read_csv(errors_path, dtype=str) if os.path.exists(errors_path) else pd.DataFrame()
            w_df = pd.read_csv(warnings_path, dtype=str) if os.path.exists(warnings_path) else pd.DataFrame()
            pd.concat([e_df, w_df]).to_csv(removed_filepath, index=False)
        except Exception:
            pd.DataFrame().to_csv(removed_filepath, index=False)
    else:
        # copy errors file
        try:
            if os.path.exists(errors_path):
                import shutil
                shutil.copyfile(errors_path, removed_filepath)
            else:
                pd.DataFrame().to_csv(removed_filepath, index=False)
        except Exception:
            pd.DataFrame().to_csv(removed_filepath, index=False)
            
    final_duplicates_removed = remove_cleaned_business_duplicates(output_filepath, duplicates_path, audit_trail)
    if final_duplicates_removed:
        stats['duplicates_removed'] += final_duplicates_removed
        stats['rows_removed'] += final_duplicates_removed
        stats['rows_retained'] = max(0, stats['rows_retained'] - final_duplicates_removed)

    final_total = stats['rows_retained']
    invalid_rows = 0
    if mode == 'SOFT' and os.path.exists(output_filepath):
        try:
            final_df = pd.read_csv(output_filepath, dtype=str).fillna('')
            if 'status' in final_df.columns:
                invalid_rows = int((final_df['status'] == 'ERROR').sum())
        except Exception:
            invalid_rows = 0

    valid_rows = max(0, final_total - invalid_rows)
    uniqueness_score = 100.0
    validity_score = round((valid_rows / final_total) * 100, 1) if final_total > 0 else 100.0
    completeness_score = 100.0
    quality_score = calculate_overall_score(completeness_score, validity_score, uniqueness_score)

    stats['total_records'] = final_total
    stats['total_rows'] = final_total
    stats['valid_rows'] = valid_rows
    stats['invalid_rows'] = invalid_rows
    stats['unique_records'] = final_total
    stats['unique_rows'] = final_total
    stats['uniqueness_score'] = uniqueness_score
    stats['validity_score'] = validity_score
    stats['completeness_score'] = completeness_score
    stats['quality_score'] = quality_score
    stats['quality_rating'] = classify_quality_rating(quality_score)
    stats['success_rate'] = validity_score
    
    stats['detected_date_format'] = detected_format
    stats['date_confidence_score'] = f"{confidence}%" if confidence > 0 else "0%"
    
    # Save the full audit report JSON to file
    with open(audit_report_path, 'w') as f:
        json.dump(audit_trail, f, indent=2)
        
    return {
        'stats': stats,
        'audit_trail': audit_trail[:1000],  # Return only first 1000 for preview in table
        'total_processed': stats['total_processed'],
        'rows_corrected': stats['rows_corrected'],
        'rows_removed': stats['rows_removed'],
        'rows_retained': stats['rows_retained'],
        'success_rate': stats['success_rate'],
        'mode': mode,
        'detected_date_format': detected_format,
        'date_confidence_score': f"{confidence}%" if confidence > 0 else "0%"
    }
