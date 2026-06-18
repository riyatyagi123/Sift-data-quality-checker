import re
import pandas as pd

TEMP_DOMAINS = {
    'mailinator.com', 'yopmail.com', 'tempmail.com', '10minutemail.com', 
    'dispostable.com', 'guerrillamail.com', 'trashmail.com'
}

def validate_email(email: str) -> bool:
    """
    Validates email format, rejecting spaces, double dots, double @,
    missing TLD, temporary domains, and unicode corruption.
    """
    if not email or pd.isna(email):
        return False
        
    email_str = str(email).strip()
    if not email_str:
        return False
        
    # Check spaces
    if ' ' in email_str or '\t' in email_str:
        return False
        
    # Check double dots
    if '..' in email_str:
        return False
        
    # Check double @
    if email_str.count('@') != 1:
        return False
        
    # Unicode corruption check
    if '\ufffd' in email_str:
        return False
        
    parts = email_str.split('@')
    local_part, domain_part = parts[0], parts[1]
    
    if not local_part or not domain_part:
        return False
        
    # Check missing TLD
    if '.' not in domain_part:
        return False
        
    domain_parts = domain_part.split('.')
    tld = domain_parts[-1]
    if len(tld) < 2:
        return False
        
    # Check temporary domains
    if domain_part.lower() in TEMP_DOMAINS:
        return False
        
    # General regex validation
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email_str):
        return False
        
    return True
