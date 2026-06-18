import os
import json
import re
import string
import unicodedata
from datetime import datetime
import pandas as pd
import numpy as np
import logging

# Submodules
from services.phone_validator import load_country_rules, get_country_key, normalize_phone_value, validate_phone
from services.date_validator import validate_date, check_date_warnings, clean_date_val, parse_date
from services.email_validator import validate_email
from services.duplicate_detector import detect_all_duplicates
from services.quality_score import get_issue_severity, classify_quality_rating, calculate_overall_score
from services.profiling import classify_dataset_from_headers, calculate_schema_confidence, infer_column_type

logger = logging.getLogger(__name__)

# Configurable aliases for dynamic field discovery
DEFAULT_ALIASES = {
    "transaction_id": [
        "transaction_id", "txn_id", "order_id", "invoice_id", "invoice_no", "id",
        "transactionid", "txnid"
    ],
    "customer_id": [
        "customer_id", "cust_id", "client_id", "customerid", "custid",
        "empid", "employeeid", "userid", "memberid"
    ],
    "customer_name": [
        "customer_name", "customername", "full_name", "fullname", "name", "cust_name",
        "employeename", "patient_name", "product_name"
    ],
    "country": [
        "country", "country_name", "nation", "region"
    ],
    "phone_number": [
        "phone", "mobile", "mobile_no", "mobile_number", "contact_number",
        "customer_phone", "telephone", "customer_mobile", "customermobile",
        "phone_number", "phonenumber"
    ],
    "transaction_date": [
        "date", "order_date", "transaction_date", "created_at", "timestamp",
        "signup_date", "transactiondate", "signupdate",
        "joined", "createdon", "signup"
    ],
    "amount": [
        "amount", "price", "total", "total_amount", "total_price",
        "transaction_amount", "value", "amt"
    ],
    "currency": [
        "currency", "curr", "currency_code"
    ],
    "payment_mode": [
        "payment_mode", "payment_method", "payment_type", "mode", "payment",
        "pay_mode", "paymentmode", "paymode"
    ],
    "email": [
        "email", "email_address", "emailaddress", "mail"
    ]
}

COLUMN_MAPPING = DEFAULT_ALIASES

def preprocess_csv(filepath: str) -> str:
    """
    Preprocesses the CSV file:
    1. Replaces whitespace-only fields with NaN.
    2. Removes rows where ALL columns are NaN/NULL/empty.
    3. Resets index.
    4. Overwrites the original file with this cleaned dataset.
    """
    try:
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            return filepath
            
        df = pd.read_csv(filepath, dtype=str)
        if df.empty:
            return filepath
            
        # DEBUG LOGGING (Before Cleaning)
        print(f"[PREPROCESS DEBUG] Before Cleaning row count: {len(df)}")
        logger.info(f"[PREPROCESS DEBUG] Before Cleaning row count: {len(df)}")
            
        # Replace empty or whitespace-only with NaN
        df_clean = df.replace(r'^\s*$', np.nan, regex=True)
        
        # Replace string "null", "nan", "undefined" with NaN
        for col in df_clean.columns:
            df_clean[col] = df_clean[col].apply(
                lambda x: np.nan if str(x).strip().lower() in ('null', 'undefined', 'nan') else x
            )
            
        # Drop rows where all elements are NaN
        df_clean = df_clean.dropna(how='all')
        df_clean = df_clean.reset_index(drop=True)
        
        # DEBUG LOGGING (After Cleaning)
        print(f"[PREPROCESS DEBUG] After Cleaning row count: {len(df_clean)}")
        logger.info(f"[PREPROCESS DEBUG] After Cleaning row count: {len(df_clean)}")
        
        # Overwrite file
        df_clean.to_csv(filepath, index=False)
        return filepath
    except Exception as e:
        logger.error(f"Error in preprocess_csv: {e}")
        return filepath

def normalize_header(header: str) -> str:
    """Normalizes header string: lowercase, trim, remove spaces/underscores/dashes."""
    if not isinstance(header, str):
        header = str(header)
    h = header.lower().strip()
    h = h.replace(' ', '').replace('_', '').replace('-', '')
    return h

def resolve_columns(df_columns: list) -> dict:
    """Maps CSV headers to our standardized fields using alias mapping and header normalization."""
    resolved = {}
    for field in DEFAULT_ALIASES.keys():
        resolved[field] = None
        
    for header in df_columns:
        norm_header = normalize_header(header)
        for field_type, aliases in DEFAULT_ALIASES.items():
            if resolved[field_type] is not None:
                continue
            norm_aliases = [normalize_header(a) for a in aliases]
            if norm_header in norm_aliases:
                resolved[field_type] = header
                break
                
    return resolved

def classify_dataset(col_map: dict) -> str:
    """Classifies dataset type based on mapped/discovered columns (backward compatibility)."""
    headers = [col for col in col_map.values() if col is not None]
    if not headers:
        return "Unknown Dataset"
    return classify_dataset_from_headers(headers)

def is_missing_value(val) -> bool:
    """Detects missing values (null, undefined, NaN, empty or whitespace-only string)."""
    if val is None or pd.isna(val):
        return True
    val_str = str(val).strip()
    if val_str == "" or val_str.lower() in ('null', 'undefined', 'nan'):
        return True
    return False

def normalize_numeric_string(val_str: str) -> str:
    """Strips currency symbols, codes, commas, and spaces from a numeric value."""
    val_str = val_str.replace(',', '')
    val_str = re.sub(r'^[A-Za-z\$\u20A0-\u20CF\s\u00A2\u00A3\u00A4\u00A5\u20B9\u20A8]+', '', val_str)
    val_str = re.sub(r'[A-Za-z\$\u20A0-\u20CF\s\u00A2\u00A3\u00A4\u00A5\u20B9\u20A8]+$', '', val_str)
    return val_str.strip()

def validate_numeric(val) -> bool:
    """Validates if value represents a valid numeric type after normalization."""
    if is_missing_value(val):
        return False
    val_str = str(val).strip()
    normalized = normalize_numeric_string(val_str)
    try:
        float(normalized)
        return True
    except ValueError:
        return False

def validate_text(val) -> bool:
    """Validates if string is a printable text without binary garbage or control characters."""
    if is_missing_value(val):
        return False
    val_str = str(val)
    for c in val_str:
        cat = unicodedata.category(c)
        if cat.startswith('C') and c not in '\n\r\t':
            return False
    return True

def normalize_payment_mode(pay_val: str) -> str:
    """Normalizes payment mode formats to a standard value."""
    p = str(pay_val).strip().lower()
    if p in ('upi', 'upi payment'):
        return 'UPI'
    if p in ('credit card', 'debit card', 'card', 'cards'):
        return 'Credit Card'
    if p in ('wallet', 'wallets', 'e-wallet'):
        return 'Wallet'
    if p in ('bank transfer', 'bank_transfer', 'wire', 'transfer'):
        return 'Bank Transfer'
    if p in ('cod', 'cash on delivery', 'cash'):
        return 'COD'
    return pay_val.strip().title()

def is_known_payment_mode(pay_val: str) -> bool:
    """Returns True if payment mode is recognized in our standardized set."""
    normalized = normalize_payment_mode(pay_val)
    return normalized in ('UPI', 'Credit Card', 'Wallet', 'Bank Transfer', 'COD', 'CARD', 'BANK_TRANSFER')

def validate_currency(currency_val: str) -> bool:
    """Validates currency string against list of allowed codes."""
    if not currency_val or pd.isna(currency_val):
        return False
    return str(currency_val).strip().upper() in {'USD', 'INR', 'SGD', 'AED', 'GBP', 'AUD'}

def validate_csv(filepath: str) -> dict:
    """
    Validates CSV file using modular submodules.
    Preprocessing -> Header Normalization -> Field Discovery -> Classification -> Profiling -> Validation.
    """
    # Preprocess dataset before validation
    preprocess_csv(filepath)
    
    # Read entire CSV
    try:
        df = pd.read_csv(filepath, dtype=str).fillna('')
        col_headers = list(df.columns)
    except Exception as e:
        logger.error(f"Error reading CSV: {e}")
        df = pd.DataFrame()
        col_headers = []
        
    total_records = len(df)
    col_map = resolve_columns(col_headers)
    dataset_type = classify_dataset_from_headers(col_headers)
    schema_confidence = calculate_schema_confidence(col_map, dataset_type)
    
    # Classify run checks based on dataset classification
    run_checks = {
        'phone': True,
        'date': True,
        'mandatory': True,
        'integrity': True,
        'duplicates': True,
        'currency': True,
        'payment_mode': True,
        'email': True
    }
    
    if dataset_type == "Customer Dataset":
        run_checks['duplicates'] = False
        run_checks['currency'] = False
        run_checks['payment_mode'] = False
        
    # Schema Analysis Warnings
    schema_warnings = []
    if dataset_type == "Customer Dataset":
        customer_fields = {
            'customer_id': 'customer_id',
            'customer_name': 'customer_name',
            'phone_number': 'phone_number',
            'transaction_date': 'signup_date',
            'email': 'email'
        }
        for field_key, display_name in customer_fields.items():
            if not col_map.get(field_key):
                schema_warnings.append(f"{display_name} field not found")
    else:
        transaction_fields = {
            'transaction_id': 'transaction_id',
            'customer_id': 'customer_id',
            'country': 'country',
            'phone_number': 'phone_number',
            'transaction_date': 'transaction_date',
            'amount': 'amount',
            'currency': 'currency',
            'payment_mode': 'payment_mode'
        }
        for field_key, display_name in transaction_fields.items():
            if not col_map.get(field_key):
                schema_warnings.append(f"{display_name} field not found")

    # Column Types & Completeness
    column_types = {}
    for col in col_headers:
        column_types[col] = infer_column_type(df, col)
        
    column_completeness = {}
    empty_columns = []
    partially_empty_columns = []
    
    for col in col_headers:
        non_empty_count = (df[col] != '').sum()
        pct = round((non_empty_count / total_records) * 100, 1) if total_records > 0 else 0.0
        column_completeness[col] = pct
        if pct == 0.0:
            empty_columns.append(col)
        elif pct < 100.0:
            partially_empty_columns.append(col)
            
    overall_completeness_score = round(sum(column_completeness.values()) / len(col_headers), 1) if col_headers else 0.0

    # Detect duplicates using duplicate detector
    dup_results = detect_all_duplicates(df, col_map)
    duplicate_ids_mask = dup_results['duplicate_ids_mask']
    
    # Initialize error lists per row to preserve existing error/warning logs
    row_errors_list = [[] for _ in range(total_records)]
    row_warnings_list = [[] for _ in range(total_records)]
    
    # Track affected sets
    mandatory_affected_indices = set()
    integrity_affected_indices = set()
    duplicates_affected_indices = set()
    date_affected_indices = set()
    phone_affected_indices = set()
    email_affected_indices = set()
    curr_affected_indices = set()
    pay_affected_indices = set()
    country_affected_indices = set()
    
    phone_col = col_map.get('phone_number')
    country_col = col_map.get('country')
    date_col = col_map.get('transaction_date')
    email_col = col_map.get('email')
    txn_col = col_map.get('transaction_id')
    amt_col = col_map.get('amount')
    curr_col = col_map.get('currency')
    pay_col = col_map.get('payment_mode')
    
    # Row-by-row validation loop
    if dataset_type == "Customer Dataset":
        mandatory_fields = ['customer_id', 'customer_name', 'phone_number', 'transaction_date', 'email']
    else:
        mandatory_fields = ['transaction_id', 'customer_id', 'country', 'phone_number', 'transaction_date', 'amount']
        
    for idx in range(total_records):
        # A. Mandatory fields check
        for field in mandatory_fields:
            m_col = col_map.get(field)
            if m_col:
                val = str(df[m_col].iloc[idx]).strip()
                if is_missing_value(val):
                    row_errors_list[idx].append({
                        'column': m_col, 'field': field, 
                        'message': f"Missing mandatory field: {m_col}", 'severity': 'CRITICAL'
                    })
                    mandatory_affected_indices.add(idx)
                    
        # Check general missing values on other detected columns
        for field, m_col in col_map.items():
            if m_col and field not in mandatory_fields:
                val = str(df[m_col].iloc[idx]).strip()
                if is_missing_value(val):
                    row_errors_list[idx].append({
                        'column': m_col, 'field': field,
                        'message': f"Missing value: {m_col}", 'severity': 'ERROR'
                    })
                    integrity_affected_indices.add(idx)
                    
        # B. Duplicate Check
        if run_checks['duplicates'] and txn_col and duplicate_ids_mask.iloc[idx]:
            val = str(df[txn_col].iloc[idx]).strip()
            row_errors_list[idx].append({
                'column': txn_col, 'field': 'transaction_id',
                'message': f"Duplicate transaction ID: {val}", 'severity': 'ERROR'
            })
            duplicates_affected_indices.add(idx)
            
        # C. Email format check
        if email_col:
            val = str(df[email_col].iloc[idx]).strip()
            if val and not is_missing_value(val):
                if not validate_email(val):
                    row_errors_list[idx].append({
                        'column': email_col, 'field': 'email',
                        'message': f"Invalid email format: {val}", 'severity': 'ERROR'
                    })
                    email_affected_indices.add(idx)
                    
        # D. Phone format check
        if phone_col:
            val = str(df[phone_col].iloc[idx]).strip()
            if val and not is_missing_value(val):
                c_val = str(df[country_col].iloc[idx]).strip() if country_col else ""
                country_key = get_country_key(c_val)
                
                # Unsupported country produces WARNING
                if country_col and c_val and not country_key:
                    row_warnings_list[idx].append({
                        'column': country_col, 'field': 'country',
                        'message': f"Unknown country: {c_val}", 'severity': 'WARNING'
                    })
                    country_affected_indices.add(idx)
                    
                if not validate_phone(val, c_val):
                    row_errors_list[idx].append({
                        'column': phone_col, 'field': 'phone_number',
                        'message': f"Invalid phone format: {val}", 'severity': 'ERROR'
                    })
                    phone_affected_indices.add(idx)
                    
        # E. Date validation & warnings check
        if date_col:
            val = str(df[date_col].iloc[idx]).strip()
            if val and not is_missing_value(val):
                if not validate_date(val):
                    row_errors_list[idx].append({
                        'column': date_col, 'field': 'transaction_date',
                        'message': f"Invalid date format: {val}", 'severity': 'ERROR'
                    })
                    date_affected_indices.add(idx)
                else:
                    # check for future/ancient warnings
                    date_warns = check_date_warnings(val)
                    for dw in date_warns:
                        row_warnings_list[idx].append({
                            'column': date_col, 'field': 'transaction_date',
                            'message': dw['message'], 'severity': dw['severity']
                        })
                        
        # F. Amount check
        if amt_col and dataset_type != "Customer Dataset":
            val = str(df[amt_col].iloc[idx]).strip()
            if val and not is_missing_value(val):
                if not validate_numeric(val):
                    row_errors_list[idx].append({
                        'column': amt_col, 'field': 'amount',
                        'message': f"Invalid numeric amount: {val}", 'severity': 'ERROR'
                    })
                    integrity_affected_indices.add(idx)
                else:
                    amt_float = float(normalize_numeric_string(val))
                    if amt_float < 0:
                        row_errors_list[idx].append({
                            'column': amt_col, 'field': 'amount',
                            'message': f"Negative amount: {val}", 'severity': 'ERROR'
                        })
                        integrity_affected_indices.add(idx)
                        
        # G. Currency check
        if curr_col and run_checks['currency']:
            val = str(df[curr_col].iloc[idx]).strip()
            if val and not is_missing_value(val):
                if not validate_currency(val):
                    row_warnings_list[idx].append({
                        'column': curr_col, 'field': 'currency',
                        'message': f"Invalid currency code: {val}", 'severity': 'WARNING'
                    })
                    curr_affected_indices.add(idx)
                    
        # H. Payment mode check
        if pay_col and run_checks['payment_mode']:
            val = str(df[pay_col].iloc[idx]).strip()
            if val and not is_missing_value(val):
                if not is_known_payment_mode(val):
                    row_warnings_list[idx].append({
                        'column': pay_col, 'field': 'payment_mode',
                        'message': f"Invalid payment mode: {val}", 'severity': 'WARNING'
                    })
                    pay_affected_indices.add(idx)
                    
        # I. Printable text/name integrity check
        name_col = col_map.get('customer_name')
        if name_col:
            val = str(df[name_col].iloc[idx]).strip()
            if val and not is_missing_value(val):
                if not validate_text(val):
                    row_errors_list[idx].append({
                        'column': name_col, 'field': 'customer_name',
                        'message': f"Corrupted text: {val}", 'severity': 'ERROR'
                    })
                    integrity_affected_indices.add(idx)

    # Compile rule statuses
    rule_status = {}
    affected_rows = {}
    
    def set_status(key, affected_set, is_active=True):
        if not is_active:
            rule_status[key] = 'SKIPPED'
            affected_rows[key] = 0
            return
        if len(affected_set) > 0:
            rule_status[key] = 'FAILED'
        else:
            rule_status[key] = 'PASSED'
        affected_rows[key] = len(affected_set)
        
    set_status('phone', phone_affected_indices, run_checks['phone'] and phone_col is not None)
    set_status('date', date_affected_indices, run_checks['date'] and date_col is not None)
    set_status('mandatory', mandatory_affected_indices, run_checks['mandatory'])
    set_status('integrity', integrity_affected_indices, run_checks['integrity'])
    set_status('duplicates', duplicates_affected_indices, run_checks['duplicates'] and txn_col is not None)
    set_status('currency', curr_affected_indices, run_checks['currency'] and curr_col is not None)
    set_status('payment_mode', pay_affected_indices, run_checks['payment_mode'] and pay_col is not None)
    set_status('email', email_affected_indices, run_checks['email'] and email_col is not None)
    set_status('country', country_affected_indices, country_col is not None)
    rule_status['schema'] = 'WARNING' if len(schema_warnings) > 0 else 'PASSED'
    affected_rows['schema'] = len(schema_warnings)

    # Classify row stats
    valid_records = 0
    warning_records = 0
    error_records = 0
    failed_rows_sample = []
    
    for idx in range(total_records):
        has_error = len(row_errors_list[idx]) > 0
        has_warning = len(row_warnings_list[idx]) > 0
        
        if has_error:
            error_records += 1
            if len(failed_rows_sample) < 10:
                row_data = df.iloc[idx].to_dict()
                err_msg = row_errors_list[idx][0]['message']
                failed_rows_sample.append({
                    'row_index': idx + 1,
                    'data': row_data,
                    'error': err_msg
                })
        elif has_warning:
            warning_records += 1
            valid_records += 1 # warnings keep the row valid
        else:
            valid_records += 1
            
    success_rate = round((valid_records / total_records) * 100, 1) if total_records > 0 else 100.0

    # Date profiling stats
    detected_date_format = "Mixed Formats"
    date_confidence_val = "0.0%"
    min_date_val = "N/A"
    max_date_val = "N/A"
    date_invalid_count = len(date_affected_indices)
    date_invalid_examples = []
    
    if date_col:
        from services.date_validator import infer_date_format_and_confidence
        _, fmt_str, conf = infer_date_format_and_confidence(df[date_col].tolist())
        detected_date_format = fmt_str
        date_confidence_val = f"{conf}%"
        
        parsed_dates = df[date_col].apply(parse_date).dropna()
        if not parsed_dates.empty:
            min_date_val = parsed_dates.min().strftime("%Y-%m-%d")
            max_date_val = parsed_dates.max().strftime("%Y-%m-%d")
            
        # Get examples of invalid dates
        invalid_mask = df[date_col].apply(lambda x: not validate_date(x) if x and not is_missing_value(x) else False)
        date_invalid_examples = list(df[date_col][invalid_mask].unique()[:5])
        
    # Email profiling stats
    email_invalid_count = len(email_affected_indices)
    email_invalid_examples = []
    if email_col:
        invalid_mask = df[email_col].apply(lambda x: not validate_email(x) if x and not is_missing_value(x) else False)
        email_invalid_examples = list(df[email_col][invalid_mask].unique()[:5])
        
    # Phone profiling stats
    phone_invalid_count = len(phone_affected_indices)
    phone_invalid_examples = []
    if phone_col:
        phone_vals = df[phone_col].tolist()
        country_vals = df[country_col].tolist() if country_col else [""] * total_records
        phone_invalid_examples = []
        for i, val in enumerate(phone_vals):
            if val and not is_missing_value(val) and not validate_phone(val, country_vals[i]):
                if val not in phone_invalid_examples:
                    phone_invalid_examples.append(val)
                    if len(phone_invalid_examples) >= 5:
                        break

    # Calculate Quality Scores
    # Completeness
    completeness_score = overall_completeness_score
    
    # Uniqueness
    uniq_scores = []
    if txn_col and run_checks['duplicates']:
        uniq_scores.append(100.0 * (total_records - dup_results['duplicate_ids_count']) / total_records if total_records > 0 else 100.0)
    if email_col:
        uniq_scores.append(100.0 * (total_records - dup_results['duplicate_emails_count']) / total_records if total_records > 0 else 100.0)
    if phone_col:
        uniq_scores.append(100.0 * (total_records - dup_results['duplicate_phones_count']) / total_records if total_records > 0 else 100.0)
    uniqueness_score = round(sum(uniq_scores) / len(uniq_scores), 1) if uniq_scores else 100.0
    
    # Validity
    val_scores = []
    if email_col:
        email_present = (df[email_col] != '').sum()
        e_val = 100.0 * (email_present - email_invalid_count) / email_present if email_present > 0 else 100.0
        val_scores.append(e_val)
    if phone_col:
        phone_present = (df[phone_col] != '').sum()
        p_val = 100.0 * (phone_present - phone_invalid_count) / phone_present if phone_present > 0 else 100.0
        val_scores.append(p_val)
    if date_col:
        date_present = (df[date_col] != '').sum()
        d_val = 100.0 * (date_present - len(date_affected_indices)) / date_present if date_present > 0 else 100.0
        val_scores.append(d_val)
    if curr_col and run_checks['currency']:
        curr_present = (df[curr_col] != '').sum()
        c_val = 100.0 * (curr_present - len(curr_affected_indices)) / curr_present if curr_present > 0 else 100.0
        val_scores.append(c_val)
    if pay_col and run_checks['payment_mode']:
        pay_present = (df[pay_col] != '').sum()
        py_val = 100.0 * (pay_present - len(pay_affected_indices)) / pay_present if pay_present > 0 else 100.0
        val_scores.append(py_val)
    if amt_col and dataset_type != "Customer Dataset":
        amt_present = (df[amt_col] != '').sum()
        amt_invalid_count = sum(1 for idx in range(total_records) if any(e['field'] == 'amount' for e in row_errors_list[idx]))
        a_val = 100.0 * (amt_present - amt_invalid_count) / amt_present if amt_present > 0 else 100.0
        val_scores.append(a_val)
        
    validity_score = round(sum(val_scores) / len(val_scores), 1) if val_scores else 100.0
    overall_score = calculate_overall_score(completeness_score, validity_score, uniqueness_score)
    quality_rating = classify_quality_rating(overall_score)

    # Issue aggregation
    issues_dict = {}
    
    def get_friendly_rule_name(field, msg):
        if 'Missing' in msg:
            return f"Missing {field}"
        if field == 'email':
            return "Invalid Email"
        if field == 'phone_number':
            return "Invalid Phone"
        if field == 'transaction_date':
            if 'Future' in msg:
                return "Future Date"
            if 'before year 2000' in msg:
                return "Ancient Date"
            return "Invalid Date"
        if field == 'transaction_id':
            if 'Duplicate' in msg:
                return "Duplicate Transaction"
        if field == 'amount':
            if 'Negative' in msg:
                return "Negative Amount"
            return "Invalid Amount"
        if field == 'currency':
            return "Invalid Currency Code"
        if field == 'payment_mode':
            return "Invalid Payment Mode"
        if field == 'country':
            return "Unknown Country"
        if field == 'customer_name' and 'Corrupted' in msg:
            return "Corrupted Text"
        return "General Validation Issue"

    for idx in range(total_records):
        all_row_issues = row_errors_list[idx] + row_warnings_list[idx]
        for issue in all_row_issues:
            field = issue.get('field')
            col = issue.get('column')
            msg = issue.get('message')
            sev = issue.get('severity', 'ERROR')
            
            rule = get_friendly_rule_name(field, msg)
            key = (rule, col)
            if key not in issues_dict:
                issues_dict[key] = {
                    'rule': rule,
                    'column': col,
                    'message': msg.split(': ')[0] if ': ' in msg else msg,
                    'severity': sev,
                    'count': 0,
                    'examples': []
                }
            issues_dict[key]['count'] += 1
            val_extracted = msg.split(': ')[-1] if ': ' in msg else ''
            if val_extracted and val_extracted not in issues_dict[key]['examples'] and len(issues_dict[key]['examples']) < 5:
                issues_dict[key]['examples'].append(val_extracted)
                
    issue_summary = list(issues_dict.values())

    # Build legacy-compatible validation_results
    validation_results = {}
    for key in ['phone', 'date', 'duplicates', 'currency', 'payment_mode', 'country', 'integrity', 'email']:
        validation_results[key] = {
            'status': rule_status.get(key, 'SKIPPED'),
            'affectedRows': affected_rows.get(key, 0)
        }

    results = {
        'total_records': total_records,
        'valid_records': valid_records,
        'invalid_records': total_records - valid_records,
        'warning_records': warning_records,
        'error_records': error_records,
        'success_rate': success_rate,
        'rule_status': rule_status,
        'affected_rows': affected_rows,
        'failed_rows': failed_rows_sample,
        'column_mapping': col_map,
        'dataset_type': dataset_type,
        
        # Spec validation summary format
        'totalRows': total_records,
        'validRows': valid_records,
        'invalidRows': total_records - valid_records,
        'schemaWarnings': schema_warnings,
        'validationResults': validation_results,
        'datasetType': dataset_type,
        
        # New Platform features
        'column_types': column_types,
        'column_completeness': column_completeness,
        'empty_columns': empty_columns,
        'partially_empty_columns': partially_empty_columns,
        'completeness_score': completeness_score,
        'validity_score': validity_score,
        'uniqueness_score': uniqueness_score,
        'overall_score': overall_score,
        'quality_rating': quality_rating,
        'schema_confidence': schema_confidence,
        'filesize_kb': round(os.path.getsize(filepath) / 1024, 2) if os.path.exists(filepath) else 0.0,
        'date_profile': {
            'detected_format': detected_date_format,
            'confidence': date_confidence_val,
            'min_date': min_date_val,
            'max_date': max_date_val,
            'invalid_count': date_invalid_count,
            'examples': date_invalid_examples
        },
        'email_profile': {
            'invalid_count': email_invalid_count,
            'examples': email_invalid_examples,
            'missing_count': int((df[email_col] == '').sum() if email_col else 0)
        },
        'phone_profile': {
            'invalid_count': phone_invalid_count,
            'examples': phone_invalid_examples
        },
        'duplicate_profile': {
            'duplicate_ids_count': dup_results['duplicate_ids_count'],
            'duplicate_ids_examples': dup_results['duplicate_ids_examples'],
            'duplicate_emails_count': dup_results['duplicate_emails_count'],
            'duplicate_emails_examples': dup_results['duplicate_emails_examples'],
            'duplicate_phones_count': dup_results['duplicate_phones_count'],
            'duplicate_phones_examples': dup_results['duplicate_phones_examples']
        },
        'issue_summary': issue_summary
    }
    
    return results
