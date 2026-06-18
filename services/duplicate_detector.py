import pandas as pd
from services.phone_validator import clean_phone_val, normalize_phone_value
from services.date_validator import clean_date_val
from services.time_validator import normalize_time

IDENTIFIER_COLUMNS = {
    'testid',
    'id',
    'rowid',
    'row',
    'rownumber',
    'serialnumber',
    'serialno',
    'serial',
    'srno',
    'sno',
    'slno',
    'recordid',
    'recordno',
    'index'
}

COUNTRY_NORMALIZATION = {
    'in': 'india',
    'ind': 'india',
    'india': 'india',
    'us': 'united states',
    'usa': 'united states',
    'unitedstates': 'united states',
    'unitedstatesofamerica': 'united states',
    'uk': 'united kingdom',
    'gb': 'united kingdom',
    'unitedkingdom': 'united kingdom',
    'ae': 'united arab emirates',
    'uae': 'united arab emirates',
    'unitedarabemirates': 'united arab emirates',
    'sg': 'singapore',
    'sgp': 'singapore',
    'singapore': 'singapore',
    'au': 'australia',
    'aus': 'australia',
    'australia': 'australia'
}

def normalize_header_name(column: str) -> str:
    return ''.join(ch for ch in str(column).lower().strip() if ch.isalnum())

def is_identifier_column(column: str) -> bool:
    normalized = normalize_header_name(column)
    return normalized in IDENTIFIER_COLUMNS or normalized.endswith('rowid')

def looks_like_row_identifier(series: pd.Series) -> bool:
    """Detects generated row id/serial columns that should not define uniqueness."""
    values = series.fillna('').astype(str).str.strip()
    non_empty = values[values != '']
    if non_empty.empty:
        return False

    numeric_values = pd.to_numeric(non_empty, errors='coerce')
    if numeric_values.isna().any():
        return False

    unique_ratio = non_empty.nunique(dropna=True) / len(non_empty)
    return unique_ratio >= 0.95

def get_business_key_columns(df: pd.DataFrame) -> list[str]:
    """Returns columns used for business duplicate comparison."""
    business_cols = []
    for idx, col in enumerate(df.columns):
        if is_identifier_column(col):
            continue
        if idx == 0 and looks_like_row_identifier(df[col]):
            continue
        business_cols.append(col)
    return business_cols

def find_country_column(df: pd.DataFrame) -> str | None:
    for col in df.columns:
        normalized_header = normalize_header_name(col)
        if 'country' in normalized_header or 'nation' in normalized_header:
            return col
    return None

def normalize_business_value(value, column: str, country_value: str = '') -> str:
    val = '' if pd.isna(value) else str(value).strip()
    normalized_header = normalize_header_name(column)

    if not val:
        return ''
    if 'phone' in normalized_header or 'mobile' in normalized_header:
        cleaned_phone, _ = clean_phone_val(val, country_value)
        return cleaned_phone if cleaned_phone and cleaned_phone != val else normalize_phone_value(val)
    if 'date' in normalized_header:
        cleaned, _ = clean_date_val(val)
        return cleaned if cleaned != 'ERROR' else val.lower()
    if 'time' in normalized_header:
        cleaned, _, _ = normalize_time(val)
        return cleaned if cleaned != 'ERROR' else val.lower()
    if 'country' in normalized_header or 'nation' in normalized_header:
        compact = ''.join(ch for ch in val.lower() if ch.isalnum())
        return COUNTRY_NORMALIZATION.get(compact, val.lower())

    return ' '.join(val.lower().split())

def build_business_key_frame(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Builds the normalized comparison frame used for business duplicate checks."""
    business_key_columns = get_business_key_columns(df)
    business_df = pd.DataFrame(index=df.index)
    if not business_key_columns:
        return business_df, business_key_columns

    country_col = find_country_column(df)
    for col in business_key_columns:
        business_df[col] = df.apply(
            lambda row: normalize_business_value(
                row[col],
                col,
                row[country_col] if country_col else ''
            ),
            axis=1
        )
    return business_df, business_key_columns

def get_duplicate_mask(df: pd.DataFrame, column: str, is_phone: bool = False) -> pd.Series:
    """Returns a boolean mask of duplicate values, keeping all duplicates (keep=False)."""
    if not column or column not in df.columns:
        return pd.Series(False, index=df.index)
    
    series = df[column].fillna('').astype(str).str.strip()
    if is_phone:
        series = series.apply(normalize_phone_value)
        
    # Exclude empty strings from being marked as duplicates
    mask = series.duplicated(keep=False) & (series != '')
    return mask

def detect_all_duplicates(df: pd.DataFrame, col_map: dict) -> dict:
    """Detects duplicates for transaction_id, email, and phone_number."""
    txn_col = col_map.get('transaction_id')
    email_col = col_map.get('email')
    phone_col = col_map.get('phone_number')
    
    duplicate_ids_mask = get_duplicate_mask(df, txn_col) if txn_col else pd.Series(False, index=df.index)
    duplicate_emails_mask = get_duplicate_mask(df, email_col) if email_col else pd.Series(False, index=df.index)
    duplicate_phones_mask = get_duplicate_mask(df, phone_col, is_phone=True) if phone_col else pd.Series(False, index=df.index)

    business_df, business_key_columns = build_business_key_frame(df)
    if business_key_columns:
        duplicate_business_mask = business_df.duplicated(keep='first')
        duplicate_business_all_mask = business_df.duplicated(keep=False)
    else:
        duplicate_business_mask = pd.Series(False, index=df.index)
        duplicate_business_all_mask = pd.Series(False, index=df.index)
    
    # Extract unique duplicate values as examples
    dup_ids_examples = list(df[txn_col][duplicate_ids_mask].unique()[:5]) if txn_col else []
    dup_emails_examples = list(df[email_col][duplicate_emails_mask].unique()[:5]) if email_col else []
    # Note: we show the original format in examples, which is cleaner
    dup_phones_examples = list(df[phone_col][duplicate_phones_mask].unique()[:5]) if phone_col else []
    
    return {
        'duplicate_ids_mask': duplicate_ids_mask,
        'duplicate_emails_mask': duplicate_emails_mask,
        'duplicate_phones_mask': duplicate_phones_mask,
        'duplicate_business_mask': duplicate_business_mask,
        'duplicate_business_all_mask': duplicate_business_all_mask,
        'duplicate_ids_count': int(duplicate_ids_mask.sum()),
        'duplicate_emails_count': int(duplicate_emails_mask.sum()),
        'duplicate_phones_count': int(duplicate_phones_mask.sum()),
        'duplicate_business_count': int(duplicate_business_mask.sum()),
        'duplicate_ids_examples': dup_ids_examples,
        'duplicate_emails_examples': dup_emails_examples,
        'duplicate_phones_examples': dup_phones_examples,
        'business_key_columns': business_key_columns
    }
