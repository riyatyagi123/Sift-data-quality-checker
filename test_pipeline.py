import sys
import os

# Add root directory to sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from services.csv_parser import parse_csv_metadata
from services.validator import validate_csv
from services.cleaner import clean_csv
from services.chunker import split_csv

def test_full_pipeline():
    sample_csv = "static/sample_transactions.csv"
    
    print("=== Step 1: Testing CSV Parser ===")
    metadata = parse_csv_metadata(sample_csv)
    print(f"Filename: {metadata['filename']}")
    print(f"Rows: {metadata['rows']}")
    print(f"Columns: {metadata['columns']}")
    print(f"Filesize: {metadata['filesize_kb']} KB")
    print(f"Headers: {metadata['preview']['headers']}")
    assert metadata['rows'] == 16, f"Expected 16 rows, got {metadata['rows']}"
    assert metadata['columns'] == 10, f"Expected 10 columns, got {metadata['columns']}"
    print("CSV Parser verified successfully.\n")

    print("=== Step 2: Testing Validation Engine ===")
    val_results = validate_csv(sample_csv)
    print(f"Total: {val_results['total_records']}")
    print(f"Valid: {val_results['valid_records']}")
    print(f"Invalid: {val_results['invalid_records']}")
    print(f"Success Rate: {val_results['success_rate']}%")
    print(f"Rule Status: {val_results['rule_status']}")
    print(f"Affected Rows: {val_results['affected_rows']}")
    print(f"Failed Rows Count (Sample): {len(val_results['failed_rows'])}")
    
    # Assert validation counts
    assert val_results['total_records'] == 16, "Expected 16 total records validated"
    # Expected affected counts:
    # Mandatory missing: 1 (CUST-10010 has missing customer_id)
    # Duplicates: 2 (TXN-10007 appears twice, and both are flagged with keep=False)
    # Date: 1 (Impossible Date Dec 32 has 32-12-2025)
    # Phone: 1 (US number with 7 digits: 5550192)
    # Currency: 1 (EUR is not in USD, INR, SGD, AED, GBP, AUD)
    # Payment: 1 (PAYPAL is not in UPI, CARD, BANK_TRANSFER, WALLET, COD)
    # Valid records should be 11 (errors and critical make row invalid; warnings like currency and payment mode do not):
    assert val_results['valid_records'] == 11, f"Expected 11 valid records, got {val_results['valid_records']}"
    assert val_results['rule_status']['phone'] == 'FAILED', "Expected phone validation status FAILED"
    assert val_results['rule_status']['currency'] == 'FAILED', "Expected currency validation status FAILED"
    assert val_results['affected_rows']['duplicates'] == 2, f"Expected 2 duplicate rows, got {val_results['affected_rows']['duplicates']}"
    print("Validation Engine verified successfully.\n")

    print("=== Step 3: Testing Cleaning Engine ===")
    cleaned_out = "processed/test_cleaned.csv"
    removed_out = "processed/test_removed.csv"
    
    # Ensure clean workspace directories exist
    os.makedirs("processed", exist_ok=True)
    os.makedirs("chunks", exist_ok=True)
    
    clean_results = clean_csv(sample_csv, cleaned_out, removed_out)
    print(f"Total Clean Processed: {clean_results['total_processed']}")
    print(f"Rows Corrected: {clean_results['rows_corrected']}")
    print(f"Rows Removed: {clean_results['rows_removed']}")
    print(f"Rows Retained: {clean_results['rows_retained']}")
    print(f"Success Rate: {clean_results['success_rate']}%")
    
    # Assert cleaning counts
    # Rows should be removed if they fail mandatory, duplicate, or negative amounts/invalid phone/date
    # Removed rows:
    # 1. TXN-10008 (Negative amount & invalid phone)
    # 2. Both TXN-10007 (Duplicate transaction ID)
    # 3. TXN-10010 (Missing customer_id - mandatory field)
    # 4. TXN-10009 (Impossible Date)
    # Thus, 7 rows removed, 9 rows retained.
    assert clean_results['rows_removed'] == 7, f"Expected 7 rows removed, got {clean_results['rows_removed']}"
    assert clean_results['rows_retained'] == 9, f"Expected 9 rows retained, got {clean_results['rows_retained']}"
    print("Cleaning Engine verified successfully.\n")

    print("=== Step 4: Testing Chunking Engine ===")
    chunk_dir = "chunks/test_session"
    chunk_results = split_csv(cleaned_out, chunk_size=5, output_dir=chunk_dir)
    print(f"Chunks generated: {chunk_results['chunk_count']}")
    print(f"Zip path: {chunk_results['zip_filepath']}")
    print(f"Chunk files: {chunk_results['chunk_files']}")
    
    # 9 retained rows split in chunk_size=5 should produce 2 chunks (5, 4)
    assert chunk_results['chunk_count'] == 2, f"Expected 2 chunks, got {chunk_results['chunk_count']}"
    assert os.path.exists(chunk_results['zip_filepath']), "Expected chunks zip file to exist"
    print("Chunking Engine verified successfully.\n")

    print("=== ALL PIPELINE TESTS PASSED SUCCESSFUL ===")

if __name__ == "__main__":
    try:
        test_full_pipeline()
        sys.exit(0)
    except AssertionError as ae:
        print(f"Pipeline validation Assertion failed: {ae}")
        sys.exit(1)
    except Exception as e:
        print(f"Pipeline verification errored: {e}")
        sys.exit(1)
