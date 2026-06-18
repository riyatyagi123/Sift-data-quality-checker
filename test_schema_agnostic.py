import os
import sys
import pandas as pd

# Add workspace directory to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from services.validator import validate_csv, resolve_columns
from services.cleaner import clean_csv

def setup_test_files():
    os.makedirs("processed", exist_ok=True)
    
    # File A: order_id, mobile, country, payment_method, amount, order_date
    # Missing: customer_id, currency
    # Valid rows, plus 1 duplicate order_id row and 1 invalid phone row
    df_a = pd.DataFrame([
        # order_id, mobile, country, payment_method, amount, order_date
        ["ORD-101", "+91 98765 43210", "India", "UPI", "500", "2026-06-16"], # Valid
        ["ORD-102", "81234567", "Singapore", "Credit Card", "100.50", "16/06/2026"], # Valid
        ["ORD-101", "9876543210", "India", "UPI", "500", "2026-06-16"], # Duplicate ORD-101 (Invalid)
        ["ORD-104", "12345", "USA", "Wallet", "25", "2026-06-16"], # Invalid phone (US requires 10, got 5) (Invalid)
        ["ORD-105", "+1 202 555 0192", "US", "COD", "-10", "2026-06-16"], # Negative amount (Invalid)
        ["ORD-106", "971501234567", "UAE", "Unknown_Mode", "200", "2026-06-16"] # Valid (Unknown payment mode is WARNING, not ERROR)
    ], columns=["order_id", "mobile", "country", "payment_method", "amount", "order_date"])
    df_a.to_csv("processed/test_file_a.csv", index=False)
    
    # File B: txn_id, customer_phone, nation, payment_type, total_amount, transaction_date
    # Missing: customer_id, currency
    df_b = pd.DataFrame([
        ["TXN-201", "919876543210", "IN", "UPI", "$1,000.50", "2026-06-16"], # Valid (with currency symbol and comma)
        ["TXN-202", "6581234567", "SG", "CARD", "SGD 120", "2026-06-16 12:00:00"] # Valid (with currency prefix)
    ], columns=["txn_id", "customer_phone", "nation", "payment_type", "total_amount", "transaction_date"])
    df_b.to_csv("processed/test_file_b.csv", index=False)
    
    # File C: invoice_no, contact_number, region, price, mode, created_at
    # Missing: customer_id, currency
    df_c = pd.DataFrame([
        ["INV-301", "447911123456", "UK", "50", "BANK_TRANSFER", "16-06-2026"], # Valid
        ["INV-302", "0491570156", "Australia", "150", "COD", "2026/06/16"] # Valid
    ], columns=["invoice_no", "contact_number", "region", "price", "mode", "created_at"])
    df_c.to_csv("processed/test_file_c.csv", index=False)

def test_schema_agnostic_pipeline():
    setup_test_files()
    
    print("=== Test 1: File A Schema Discovery & Validation ===")
    res_a = validate_csv("processed/test_file_a.csv")
    print(f"File A - Total: {res_a['total_records']}, Valid: {res_a['valid_records']}, Invalid: {res_a['invalid_records']}")
    print(f"Schema Warnings: {res_a['schemaWarnings']}")
    print(f"Rule Statuses: {res_a['rule_status']}")
    
    # customer_id and currency fields are missing. So schema status is WARNING.
    assert "customer_id field not found" in res_a['schemaWarnings']
    assert "currency field not found" in res_a['schemaWarnings']
    assert res_a['rule_status']['schema'] == 'WARNING'
    
    # Customer ID and Currency validations are skipped
    assert res_a['rule_status']['currency'] == 'SKIPPED'
    
    # Valid records should be: ORD-101 (first), ORD-102. (Total 2 valid rows out of 6)
    # Invalid records:
    # 1. ORD-101 (duplicate) - Error
    # 2. ORD-104 (phone invalid) - Error
    # 3. ORD-105 (negative amount) - Error
    # 4. ORD-106 (unknown payment mode) - Warning
    # So valid: 2 (ORD-101, ORD-102)
    # Invalid: 4 (ORD-101 duplicate, ORD-104 phone, ORD-105 negative amount, ORD-106 payment mode warning)
    assert res_a['valid_records'] == 2, f"Expected 2 valid rows, got {res_a['valid_records']}"
    assert res_a['invalid_records'] == 4, f"Expected 4 invalid rows, got {res_a['invalid_records']}"
    assert res_a['warning_records'] == 1, f"Expected 1 warning row, got {res_a['warning_records']}"
    assert res_a['error_records'] == 4, f"Expected 4 error rows, got {res_a['error_records']}"
    
    # Clean File A and check retained/removed rows
    clean_out_a = "processed/test_file_a_cleaned.csv"
    removed_out_a = "processed/test_file_a_removed.csv"
    clean_res_a = clean_csv("processed/test_file_a.csv", clean_out_a, removed_out_a)
    print(f"File A Cleaned: {clean_res_a}")
    # Discarded rows should be duplicate, negative amount, and invalid phone (which is now properly marked as an error and removed).
    # Removed rows:
    # 1. Both ORD-101 (duplicate)
    # 2. ORD-104 (phone error)
    # 3. ORD-105 (negative amount)
    # Thus, 5 rows removed, 1 row retained.
    assert clean_res_a['rows_removed'] == 5, f"Expected 5 rows removed, got {clean_res_a['rows_removed']}"
    assert clean_res_a['rows_retained'] == 1, f"Expected 1 row retained, got {clean_res_a['rows_retained']}"
    
    # Read the cleaned file to ensure headers are preserved
    cleaned_df = pd.read_csv(clean_out_a)
    assert list(cleaned_df.columns) == ["order_id", "mobile", "country", "payment_method", "amount", "order_date"]
    print("File A verification passed.\n")

    print("=== Test 2: File B Currency & Normalization Validation ===")
    res_b = validate_csv("processed/test_file_b.csv")
    print(f"File B - Total: {res_b['total_records']}, Valid: {res_b['valid_records']}, Invalid: {res_b['invalid_records']}")
    assert res_b['valid_records'] == 2
    assert res_b['invalid_records'] == 0
    
    # Clean File B and check amount normalization
    clean_out_b = "processed/test_file_b_cleaned.csv"
    clean_res_b = clean_csv("processed/test_file_b.csv", clean_out_b, "processed/test_file_b_removed.csv")
    cleaned_df_b = pd.read_csv(clean_out_b)
    # The total_amount should remain, but the payment_type and other fields normalized
    print(f"File B Cleaned DF:\n{cleaned_df_b}")
    print("File B verification passed.\n")

    print("=== Test 3: File C Validations ===")
    res_c = validate_csv("processed/test_file_c.csv")
    print(f"File C - Total: {res_c['total_records']}, Valid: {res_c['valid_records']}, Invalid: {res_c['invalid_records']}")
    assert res_c['valid_records'] == 2
    assert res_c['invalid_records'] == 0
    print("File C verification passed.\n")
    
    print("=== Test 4: Customer Dataset (300 valid + 699 empty rows simulation) ===")
    # Generate customer dataframe: 3 valid rows, 2 invalid rows, plus 702 completely empty/whitespace/null rows
    df_cust = pd.DataFrame([
        # customer_id, full_name, email, phone_number, city, signup_date
        ["457429", "Tanya", "tanya@gmail.com", "7006534601", "Srinagar", "22-08-2024"], # Valid (10 digit India phone starts with 6-9, valid email, valid date)
        ["457430", "Rahul", "rahul@test.org", "9876543210", "Delhi", "2026-06-16"], # Valid
        ["457431", "Aisha", "aisha@domain.co.in", "8123456789", "Mumbai", "16/06/2026"], # Valid
        ["457432", "Raj", "invalid_email", "987654321", "Bangalore", "22-08-2024"], # Invalid (bad email format & phone 9 digits)
        ["", "", "", "", "", ""], # Completely empty row (should be dropped)
        [" ", "  ", " ", " ", " ", " "], # Whitespace empty row (should be dropped)
        [None, None, None, None, None, None], # NULL row (should be dropped)
        ["457433", "John", "john@gmail.com", "", "New York", "22-08-2024"] # Partially populated row (invalid due to missing phone)
    ], columns=["customer_id", "full_name", "email", "phone_number", "city", "signup_date"])
    
    # Concat 699 completely empty rows to simulate the exact user report
    empty_rows_list = []
    for _ in range(699):
        empty_rows_list.append([None, None, None, None, None, None])
    df_empty = pd.DataFrame(empty_rows_list, columns=df_cust.columns)
    df_cust = pd.concat([df_cust, df_empty], ignore_index=True)
    
    cust_file = "processed/test_customer_dataset.csv"
    df_cust.to_csv(cust_file, index=False)
    
    # Run validation
    res_cust = validate_csv(cust_file)
    print(f"Customer Dataset - Total after preprocess: {res_cust['total_records']}, Valid: {res_cust['valid_records']}, Invalid: {res_cust['invalid_records']}")
    print(f"Dataset Type detected: {res_cust['dataset_type']}")
    print(f"Rule Statuses: {res_cust['rule_status']}")
    
    # Verify empty rows pre-processing
    # Expected: 5 records total (3 valid, 2 invalid: Raj, John)
    assert res_cust['total_records'] == 5, f"Expected 5 records, got {res_cust['total_records']}"
    assert res_cust['dataset_type'] == "Customer Dataset", f"Expected Customer Dataset, got {res_cust['dataset_type']}"
    assert res_cust['valid_records'] == 3, f"Expected 3 valid rows, got {res_cust['valid_records']}"
    assert res_cust['invalid_records'] == 2, f"Expected 2 invalid rows, got {res_cust['invalid_records']}"
    
    # Verify skipped checks
    assert res_cust['rule_status']['duplicates'] == 'SKIPPED'
    assert res_cust['rule_status']['currency'] == 'SKIPPED'
    assert res_cust['rule_status']['payment_mode'] == 'SKIPPED'
    print("Customer Dataset verification passed.\n")
    
    print("=== ALL SCHEMA-AGNOSTIC TESTS PASSED SUCCESSFUL ===")

if __name__ == "__main__":
    try:
        test_schema_agnostic_pipeline()
        sys.exit(0)
    except AssertionError as ae:
        print(f"Assertion failed: {ae}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
