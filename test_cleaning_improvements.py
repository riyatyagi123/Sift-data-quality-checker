import os
import pandas as pd
from services.cleaner import clean_name, clean_csv
from services.validator import validate_csv
from services.date_validator import infer_date_format_and_confidence

def test_abbreviations():
    # Test abbreviation preservation
    res, corr = clean_name("PAYPAL ACCT")
    assert res == "PAYPAL Acct", f"Expected 'PAYPAL Acct', got '{res}'"
    
    res2, corr2 = clean_name("USD CURRENCY")
    assert res2 == "USD Currency", f"Expected 'USD Currency', got '{res2}'"

def test_date_inference():
    # Sample date list favoring dayfirst
    dates_dayfirst = ["16-06-2026", "22/08/2024", "05-12-2025"]
    dayfirst, fmt, conf = infer_date_format_and_confidence(dates_dayfirst)
    assert dayfirst is True, "Expected dayfirst=True"
    assert "dd" in fmt, "Expected dd-mm-yyyy or similar format string"
    assert conf > 80.0, f"Expected high confidence, got {conf}"

    # Sample date list favoring monthfirst
    dates_monthfirst = ["06-16-2026", "08/22/2024", "12-05-2025"]
    dayfirst_m, fmt_m, conf_m = infer_date_format_and_confidence(dates_monthfirst)
    assert dayfirst_m is False, "Expected dayfirst=False"
    assert "mm" in fmt_m, "Expected mm-dd-yyyy or similar format string"


def test_mixed_date_format():
    dates_mixed = ["12-05-2026", "16/06/2026", "05/24/2026", "2026/04/10"]
    dayfirst, fmt, conf = infer_date_format_and_confidence(dates_mixed)
    assert dayfirst is None, "Expected dayfirst=None for mixed formats"
    assert fmt == "Mixed Formats", f"Expected 'Mixed Formats', got '{fmt}'"


def test_libphonenumber_engine():
    from services.phone_validator import validate_phone_details, validate_phone, clean_phone_val
    
    # 1. Valid numbers
    r1 = validate_phone_details("+91 98765 43210", "India")
    assert r1["is_valid"] is True, "Expected valid phone for +91 98765 43210"
    assert r1["e164"] == "+919876543210", f"Expected +919876543210, got {r1['e164']}"
    assert r1["national"] == "9876543210", f"Expected 9876543210, got {r1['national']}"
    assert r1["region"] == "IN", f"Expected IN, got {r1['region']}"
    
    r2 = validate_phone_details("98765-43210", "India")
    assert r2["is_valid"] is True, "Expected valid phone for 98765-43210"
    assert r2["national"] == "9876543210", f"Expected 9876543210, got {r2['national']}"
    
    r3 = validate_phone_details("(98765)43210", "India")
    assert r3["is_valid"] is True, "Expected valid phone for (98765)43210"
    assert r3["national"] == "9876543210", f"Expected 9876543210, got {r3['national']}"
    
    # 2. Invalid numbers (missing leading zero, do not guess/prepend)
    r4 = validate_phone_details("7911123456", "UK")
    assert r4["is_valid"] is False, "Expected invalid phone for 7911123456"
    
    r5 = validate_phone_details("491570156", "Australia")
    assert r5["is_valid"] is False, "Expected invalid phone for 491570156"
    
    r6 = validate_phone_details("501234567", "UAE")
    assert r6["is_valid"] is False, "Expected invalid phone for 501234567"
    
    # 3. Unknown countries
    r7 = validate_phone_details("+91 98765 43210", "UnknownCountry")
    assert r7 == ("WARNING", "Unknown country"), f"Expected warning tuple, got {r7}"
    
    # 4. Cleaning
    c1, changed1 = clean_phone_val("+91 98765 43210", "India")
    assert c1 == "9876543210", f"Expected 9876543210, got {c1}"
    assert changed1 is True
    
    c2, changed2 = clean_phone_val("7911123456", "UK")
    assert c2 == "7911123456", f"Expected 7911123456, got {c2}"
    assert changed2 is False

def test_duplicate_shortcircuit():
    # Generate temporary duplicate dataset
    os.makedirs("processed", exist_ok=True)
    df = pd.DataFrame([
        ["TXN-001", "John Doe", "john@gmail.com", "919876543210", "IN", "22-08-2024", "UPI", "100", "INR"],
        ["TXN-001", "Jane Doe", "jane@gmail.com", "919876543210", "IN", "22-08-2024", "UPI", "100", "INR"]
    ], columns=["transaction_id", "customer_name", "email", "phone_number", "country", "transaction_date", "payment_mode", "amount", "currency"])
    
    df.to_csv("processed/test_dup.csv", index=False)
    
    res = clean_csv("processed/test_dup.csv", "processed/test_dup_cleaned.csv", "processed/test_dup_removed.csv")
    
    # Both rows are flagged as duplicates
    assert res['stats']['duplicates_removed'] == 2, f"Expected 2 duplicates, got {res['stats']['duplicates_removed']}"
    
    # Check audit trail for duplicate removal
    audit_trail = res['audit_trail']
    dup_actions = [a for a in audit_trail if a['action'] == 'duplicate_removal']
    assert len(dup_actions) == 2, "Expected 2 duplicate removal actions in audit log"
    
    # Verify no downstream corrections (e.g. name whitespace_trim or country mapping) on the duplicate row
    row2_actions = [a for a in audit_trail if a['row'] == 2 and a['action'] != 'duplicate_removal']
    assert len(row2_actions) == 0, f"Expected 0 actions on the duplicate row except duplicate_removal, got {row2_actions}"

def test_business_duplicates_ignore_identifier_columns():
    os.makedirs("processed", exist_ok=True)
    df = pd.DataFrame([
        [1, "IN", "9876543210", "2026-06-18", "14:30:00"],
        [3, "IN", "9876543210", "2026-06-18", "14:30:00"],
        [4, "IN", "+919876543210", "18-06-2026", "02:30 PM"],
        [5, "US", "2125551234", "06/18/2026", "02:30 PM"],
    ], columns=["Test_ID", "Country", "Phone_Number", "Transaction_Date", "Transaction_Time"])

    input_path = "processed/test_business_duplicates.csv"
    output_path = "processed/test_business_duplicates_cleaned.csv"
    removed_path = "processed/test_business_duplicates_removed.csv"
    df.to_csv(input_path, index=False)

    validation = validate_csv(input_path)
    duplicate_validation_logs = [
        log for log in validation.get('validation_logs', [])
        if log['column'] == 'Entire_Row' and log['message'] == 'Duplicate Record Detected'
    ]
    assert len(duplicate_validation_logs) == 2, f"Expected 2 duplicate validation warnings, got {duplicate_validation_logs}"
    assert validation['duplicate_profile']['duplicate_business_count'] == 2

    res = clean_csv(input_path, output_path, removed_path)
    cleaned_df = pd.read_csv(output_path, dtype=str)

    assert len(cleaned_df) == 2, f"Expected 2 final rows, got {len(cleaned_df)}"
    assert cleaned_df.iloc[0]["Test_ID"] == "1", "Expected first business duplicate occurrence to be kept"
    assert not cleaned_df.duplicated(subset=["Country", "Phone_Number", "Transaction_Date", "Transaction_Time"]).any()
    assert res['stats']['duplicates_removed'] == 2, f"Expected 2 final duplicates removed, got {res['stats']['duplicates_removed']}"
    assert res['stats']['total_records'] == 2
    assert res['stats']['unique_records'] == 2
    assert res['stats']['uniqueness_score'] == 100.0

    duplicate_cleaning_logs = [
        log for log in res['audit_trail']
        if log['column'] == 'Entire_Row' and log['action'] == 'Duplicate Removed' and log['severity'] == 'INFO'
    ]
    assert len(duplicate_cleaning_logs) == 2, f"Expected 2 duplicate cleaning logs, got {duplicate_cleaning_logs}"

def test_numeric_first_column_does_not_block_duplicate_cleanup():
    os.makedirs("processed", exist_ok=True)
    df = pd.DataFrame([
        [1, "India", "9876543210", "18-06-2026", "14:30:45"],
        [24, "India", "9876543210", "18-06-2026", "14:30:45"],
        [25, "Singapore", "91234567", "18-06-2026", "23:59:59"],
    ], columns=["Record_No", "Country", "Phone_Number", "Transaction_Date", "Transaction_Time"])

    input_path = "processed/test_numeric_id_duplicates.csv"
    output_path = "processed/test_numeric_id_duplicates_cleaned.csv"
    removed_path = "processed/test_numeric_id_duplicates_removed.csv"
    df.to_csv(input_path, index=False)

    res = clean_csv(input_path, output_path, removed_path)
    cleaned_df = pd.read_csv(output_path, dtype=str)

    assert len(cleaned_df) == 2, f"Expected 2 final rows, got {len(cleaned_df)}"
    assert cleaned_df.iloc[0]["Record_No"] == "1"
    assert "24" not in set(cleaned_df["Record_No"])
    assert res['stats']['duplicates_removed'] == 1

if __name__ == "__main__":
    print("Running new cleaning improvements tests...")
    test_abbreviations()
    print("Abbreviation preservation passed.")
    test_date_inference()
    print("Date format inference passed.")
    test_mixed_date_format()
    print("Mixed date format detection passed.")
    test_libphonenumber_engine()
    print("Libphonenumber engine tests passed.")
    test_duplicate_shortcircuit()
    print("Duplicate short-circuit & precise audit log passed.")
    test_business_duplicates_ignore_identifier_columns()
    print("Business duplicate validation and cleanup passed.")
    test_numeric_first_column_does_not_block_duplicate_cleanup()
    print("Numeric row identifier duplicate cleanup passed.")
    print("All new verification tests passed successfully!")
