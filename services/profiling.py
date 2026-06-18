import re
import pandas as pd
import numpy as np
from datetime import datetime
from services.phone_validator import normalize_phone_value
from services.date_validator import parse_date

def classify_dataset_from_headers(headers: list) -> str:
    """Classifies dataset type based on header clues."""
    norm_headers = [str(h).strip().lower().replace('_', '').replace(' ', '') for h in headers]
    
    cust_score = 0
    txn_score = 0
    emp_score = 0
    prod_score = 0
    hosp_score = 0
    
    for h in norm_headers:
        # Customer clues
        if h in ['customerid', 'custid', 'clientid', 'memberid', 'customername', 'clientname']:
            cust_score += 2
        elif h in ['email', 'phone', 'phonenumber', 'mobile']:
            cust_score += 1
            
        # Transaction clues
        if h in ['transactionid', 'txnid', 'orderid', 'invoiceid', 'receiptid']:
            txn_score += 2
        elif h in ['amount', 'price', 'totalamount', 'paymentmode', 'paymenttype', 'currency']:
            txn_score += 1
            
        # Employee clues
        if h in ['employeeid', 'empid', 'staffid', 'employeename', 'salary', 'department', 'dept', 'hiredate', 'jobtitle', 'managerid']:
            emp_score += 2
        elif h in ['joined', 'signup', 'signupdate', 'createdon']:
            emp_score += 1
            
        # Product clues
        if h in ['productid', 'itemid', 'sku', 'productname', 'productdesc', 'stock', 'quantity', 'qty', 'unitprice', 'category']:
            prod_score += 2
            
        # Hospital clues
        if h in ['patientid', 'patientname', 'medicalid', 'mrn', 'doctor', 'diagnosis', 'roomnumber', 'admissiondate', 'dischargedate', 'hospitalname']:
            hosp_score += 2
            
    scores = {
        "Customer Dataset": cust_score,
        "Transaction Dataset": txn_score,
        "Employee Dataset": emp_score,
        "Product Dataset": prod_score,
        "Hospital Dataset": hosp_score
    }
    
    # Find max score
    max_type = max(scores, key=scores.get)
    if scores[max_type] == 0:
        return "Unknown Dataset"
        
    # If customer and transaction both have high scores, it's mixed
    if cust_score >= 2 and txn_score >= 2:
        return "Mixed Dataset"
        
    return max_type

def calculate_schema_confidence(resolved_cols: dict, dataset_type: str) -> int:
    """Calculates a confidence score (0-100) for the mapped schema."""
    expected = {
        "Customer Dataset": ['customer_id', 'customer_name', 'phone_number', 'transaction_date', 'email'],
        "Transaction Dataset": ['transaction_id', 'customer_id', 'country', 'phone_number', 'transaction_date', 'amount', 'currency', 'payment_mode'],
        "Employee Dataset": ['customer_id', 'customer_name', 'email', 'transaction_date'],
        "Product Dataset": ['amount', 'transaction_id'], 
        "Hospital Dataset": ['customer_id', 'customer_name', 'transaction_date'],
        "Mixed Dataset": ['customer_id', 'transaction_date'],
        "Unknown Dataset": []
    }.get(dataset_type, [])
    
    if not expected:
        mapped_count = sum(1 for v in resolved_cols.values() if v is not None)
        return int((mapped_count / len(resolved_cols)) * 100) if resolved_cols else 0
        
    mapped_expected = sum(1 for f in expected if resolved_cols.get(f) is not None)
    score = int((mapped_expected / len(expected)) * 100)
    return max(0, min(100, score))

def infer_column_type(df: pd.DataFrame, col: str) -> str:
    """Infers type of column for display."""
    series = df[col].dropna()
    if series.empty:
        return 'Text/String'
        
    # Sample 100 non-empty values
    sample = series.astype(str).str.strip().tolist()[:100]
    
    # 1. Email check
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if all(re.match(email_regex, x) for x in sample if x):
        return 'Email'
        
    # 2. Date check
    date_successes = 0
    for x in sample:
        if not x:
            continue
        if parse_date(x):
            date_successes += 1
    if date_successes > len(sample) * 0.7:
        return 'Date'
        
    # 3. Numeric check
    numeric_successes = 0
    for x in sample:
        if not x:
            continue
        cleaned_num = re.sub(r'[^\d\.\-]', '', x)
        try:
            float(cleaned_num)
            numeric_successes += 1
        except ValueError:
            pass
    if numeric_successes > len(sample) * 0.8:
        return 'Numeric'
        
    # 4. Phone check
    phone_successes = 0
    for x in sample:
        if not x:
            continue
        cleaned_ph = normalize_phone_value(x)
        if len(cleaned_ph) >= 7 and len(cleaned_ph) <= 15:
            phone_successes += 1
    if phone_successes > len(sample) * 0.7:
        return 'Phone'
        
    # 5. Boolean check
    boolean_values = {'true', 'false', 'yes', 'no', '1', '0', 't', 'f'}
    if all(x.lower() in boolean_values for x in sample if x):
        return 'Boolean'
        
    return 'Text/String'

def generate_column_profiles(df: pd.DataFrame, col_map: dict) -> dict:
    """Generates detailed profiling metrics for each column."""
    profiles = {}
    
    for col in df.columns:
        series = df[col].fillna('').astype(str).str.strip()
        non_empty = series[series != '']
        
        completeness = round((len(non_empty) / len(df)) * 100, 1) if not df.empty else 0.0
        col_type = infer_column_type(df, col)
        
        col_profile = {
            'type': col_type,
            'completeness': completeness,
            'non_empty_count': len(non_empty),
            'empty_count': len(df) - len(non_empty)
        }
        
        # Numeric Stats
        if col_type == 'Numeric':
            nums = pd.to_numeric(non_empty.str.replace(r'[^\d\.\-]', '', regex=True), errors='coerce').dropna()
            if not nums.empty:
                col_profile['stats'] = {
                    'minimum': float(nums.min()),
                    'maximum': float(nums.max()),
                    'average': float(nums.mean()),
                    'median': float(nums.median()),
                    'std_dev': float(nums.std()) if len(nums) > 1 else 0.0
                }
                
        # Text/String Stats
        elif col_type in ['Text/String', 'Email']:
            val_counts = non_empty.value_counts()
            top_10 = [[val, int(count)] for val, count in zip(val_counts.index[:10], val_counts.values[:10])]
            avg_len = float(non_empty.str.len().mean()) if not non_empty.empty else 0.0
            
            col_profile['stats'] = {
                'distinct_count': int(non_empty.nunique()),
                'top_10_values': top_10,
                'average_length': avg_len
            }
            
        # Date Stats
        elif col_type == 'Date':
            parsed_dates = non_empty.apply(parse_date).dropna()
            if not parsed_dates.empty:
                now_naive = datetime.now()
                future_count = int((parsed_dates > now_naive).sum())
                ancient_count = int((parsed_dates.apply(lambda x: x.year < 2000)).sum())
                
                col_profile['stats'] = {
                    'minimum_date': parsed_dates.min().strftime("%Y-%m-%d"),
                    'maximum_date': parsed_dates.max().strftime("%Y-%m-%d"),
                    'future_dates_count': future_count,
                    'ancient_dates_count': ancient_count
                }
                
        profiles[col] = col_profile
        
    return profiles
