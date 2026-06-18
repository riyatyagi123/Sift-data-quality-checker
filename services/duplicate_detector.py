import pandas as pd
from services.phone_validator import normalize_phone_value

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
    
    # Extract unique duplicate values as examples
    dup_ids_examples = list(df[txn_col][duplicate_ids_mask].unique()[:5]) if txn_col else []
    dup_emails_examples = list(df[email_col][duplicate_emails_mask].unique()[:5]) if email_col else []
    # Note: we show the original format in examples, which is cleaner
    dup_phones_examples = list(df[phone_col][duplicate_phones_mask].unique()[:5]) if phone_col else []
    
    return {
        'duplicate_ids_mask': duplicate_ids_mask,
        'duplicate_emails_mask': duplicate_emails_mask,
        'duplicate_phones_mask': duplicate_phones_mask,
        'duplicate_ids_count': int(duplicate_ids_mask.sum()),
        'duplicate_emails_count': int(duplicate_emails_mask.sum()),
        'duplicate_phones_count': int(duplicate_phones_mask.sum()),
        'duplicate_ids_examples': dup_ids_examples,
        'duplicate_emails_examples': dup_emails_examples,
        'duplicate_phones_examples': dup_phones_examples
    }
