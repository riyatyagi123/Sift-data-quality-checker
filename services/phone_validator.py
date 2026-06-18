import re
import pandas as pd
import logging
import phonenumbers
from phonenumbers import PhoneNumberFormat, PhoneMetadata

logger = logging.getLogger(__name__)

# Dummy for backwards compatibility
COUNTRY_RULES = {
    "India": {"length": 10, "prefix": "91"},
    "Singapore": {"length": 8, "prefix": "65"},
    "USA": {"length": 10, "prefix": "1"},
    "UK": {"length": 11, "prefix": "44"},
    "Australia": {"length": 10, "prefix": "61"},
    "UAE": {"length": 10, "prefix": "971"}
}

def load_country_rules() -> dict:
    """Returns country rules dictionary for backwards compatibility."""
    return COUNTRY_RULES

def map_country_to_region(country_str: str) -> str:
    """Maps country name or code to a 2-letter ISO region code."""
    if not country_str:
        return ""
    c = str(country_str).strip().upper()
    
    mapping = {
        "INDIA": "IN", "IN": "IN", "IND": "IN",
        "SINGAPORE": "SG", "SG": "SG", "SGP": "SG",
        "USA": "US", "US": "US", "UNITED STATES": "US", "UNITED STATES OF AMERICA": "US",
        "UK": "GB", "UNITED KINGDOM": "GB", "GB": "GB", "GREAT BRITAIN": "GB",
        "AUSTRALIA": "AU", "AU": "AU", "AUS": "AU",
        "UAE": "AE", "UNITED ARAB EMIRATES": "AE", "AE": "AE"
    }
    
    if c in mapping:
        return mapping[c]
        
    # Support any 2-letter code supported by libphonenumber
    if len(c) == 2 and c in phonenumbers.SUPPORTED_REGIONS:
        return c
        
    # Extra common countries
    extra_mapping = {
        "CANADA": "CA", "CAN": "CA",
        "GERMANY": "DE", "DE": "DE", "DEU": "DE",
        "FRANCE": "FR", "FR": "FR", "FRA": "FR",
        "JAPAN": "JP", "JP": "JP", "JPN": "JP",
        "CHINA": "CN", "CN": "CN", "CHN": "CN",
        "BRAZIL": "BR", "BR": "BR", "BRA": "BR",
        "ITALY": "IT", "IT": "IT", "ITA": "IT",
        "SPAIN": "ES", "ES": "ES", "ESP": "ES",
        "RUSSIA": "RU", "RU": "RU", "RUS": "RU",
        "NETHERLANDS": "NL", "NL": "NL", "NLD": "NL",
        "SWITZERLAND": "CH", "CH": "CH", "CHE": "CH",
        "SWEDEN": "SE", "SE": "SE", "SWE": "SE",
        "NORWAY": "NO", "NO": "NO", "NOR": "NO",
        "DENMARK": "DK", "DK": "DK", "DNK": "DK",
        "FINLAND": "FI", "FI": "FI", "FIN": "FI",
        "NEW ZEALAND": "NZ", "NZ": "NZ", "NZL": "NZ",
        "SOUTH AFRICA": "ZA", "ZA": "ZA", "ZAF": "ZA",
        "HONG KONG": "HK", "HK": "HK", "HKG": "HK",
    }
    if c in extra_mapping:
        return extra_mapping[c]
        
    return ""

def get_country_key(country_str: str) -> str:
    """Resolves country name or ISO code to region code."""
    return map_country_to_region(country_str)

def normalize_phone_value(phone: str) -> str:
    """Normalizes phone value: removes spaces, dashes, brackets, trims whitespace."""
    if not phone or pd.isna(phone):
        return ""
    phone_str = str(phone).strip()
    cleaned = re.sub(r'[\s\-\(\)]+', '', phone_str)
    if cleaned.startswith('+'):
        cleaned = cleaned[1:]
    cleaned = re.sub(r'\D', '', cleaned)
    return cleaned

def validate_phone_details(phone: str, country: str) -> dict | tuple[str, str]:
    """
    Validates phone number using Google's libphonenumber (via phonenumbers library).
    Returns a details dictionary or a tuple ("WARNING", "Unknown country") if unknown.
    """
    if not phone or pd.isna(phone):
        return {
            "is_valid": False,
            "country": country,
            "region": "",
            "e164": "",
            "national": "",
            "international": "",
            "type": "UNKNOWN"
        }
        
    region = map_country_to_region(country)
    if not region:
        return "WARNING", "Unknown country"
        
    clean_input = str(phone).strip()
    digits_only = re.sub(r'\D', '', clean_input)
    
    try:
        parsed = phonenumbers.parse(clean_input, region)
    except Exception:
        return {
            "is_valid": False,
            "country": country,
            "region": region,
            "e164": "",
            "national": "",
            "international": "",
            "type": "UNKNOWN"
        }
        
    possible = phonenumbers.is_possible_number(parsed)
    valid = phonenumbers.is_valid_number(parsed)
    
    if not (possible and valid):
        return {
            "is_valid": False,
            "country": country,
            "region": region,
            "e164": "",
            "national": "",
            "international": "",
            "type": "UNKNOWN"
        }
        
    e164_val = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
    national_val = phonenumbers.format_number(parsed, PhoneNumberFormat.NATIONAL)
    international_val = phonenumbers.format_number(parsed, PhoneNumberFormat.INTERNATIONAL)
    
    national_digits = re.sub(r'\D', '', national_val)
    if region == "IN" and national_digits.startswith('0') and len(national_digits) == 11:
        national_digits = national_digits[1:]
    
    # Strict validation check: Do not guess missing leading zeros / missing digits
    metadata = PhoneMetadata.metadata_for_region(region)
    national_prefix = metadata.national_prefix
    country_code = str(parsed.country_code)
    
    is_invalid = False
    
    if national_prefix and region in {"GB", "AU", "AE"}:
        has_intl_prefix = clean_input.startswith('+') or clean_input.startswith('00')
        starts_with_country_code = digits_only.startswith(country_code) and len(digits_only) > len(country_code)
        if not has_intl_prefix and not starts_with_country_code:
            # Local number, must start with national prefix
            if not clean_input.startswith(national_prefix) and not digits_only.startswith(national_prefix):
                is_invalid = True
                
    if len(digits_only) < len(national_digits):
        is_invalid = True
        
    if is_invalid:
        return {
            "is_valid": False,
            "country": country,
            "region": region,
            "e164": "",
            "national": "",
            "international": "",
            "type": "UNKNOWN"
        }
        
    from phonenumbers import PhoneNumberType
    ntype = phonenumbers.number_type(parsed)
    if ntype == PhoneNumberType.MOBILE:
        type_str = "MOBILE"
    elif ntype == PhoneNumberType.FIXED_LINE:
        type_str = "FIXED_LINE"
    elif ntype == PhoneNumberType.FIXED_LINE_OR_MOBILE:
        type_str = "FIXED_LINE_OR_MOBILE"
    elif ntype == PhoneNumberType.TOLL_FREE:
        type_str = "TOLL_FREE"
    elif ntype == PhoneNumberType.PREMIUM_RATE:
        type_str = "PREMIUM_RATE"
    elif ntype == PhoneNumberType.SHARED_COST:
        type_str = "SHARED_COST"
    elif ntype == PhoneNumberType.VOIP:
        type_str = "VOIP"
    elif ntype == PhoneNumberType.PERSONAL_NUMBER:
        type_str = "PERSONAL_NUMBER"
    elif ntype == PhoneNumberType.PAGER:
        type_str = "PAGER"
    elif ntype == PhoneNumberType.UAN:
        type_str = "UAN"
    elif ntype == PhoneNumberType.VOICEMAIL:
        type_str = "VOICEMAIL"
    else:
        type_str = "UNKNOWN"
        
    region_to_country = {
        "IN": "India",
        "SG": "Singapore",
        "US": "USA",
        "GB": "UK",
        "AU": "Australia",
        "AE": "UAE"
    }
    country_name = region_to_country.get(region, country)
    
    return {
        "is_valid": True,
        "country": country_name,
        "region": region,
        "e164": e164_val,
        "national": national_digits,
        "international": international_val,
        "type": type_str
    }

def validate_phone(phone: str, country: str, rules: dict = None) -> bool:
    """Validates phone number using libphonenumber. Returns True if valid or country unknown."""
    res = validate_phone_details(phone, country)
    if isinstance(res, tuple):
        return True
    return res["is_valid"]

def clean_phone_val(phone_val: str, country_val: str) -> tuple[str, bool]:
    """Normalizes phone value formatting to standard National format digits."""
    res = validate_phone_details(phone_val, country_val)
    if isinstance(res, tuple):
        return str(phone_val).strip(), False
    if not res["is_valid"]:
        return str(phone_val).strip(), False
        
    cleaned = res["national"]
    original = str(phone_val).strip()
    return cleaned, (cleaned != original)
