import sys
import os

# Ensure the root project path is in sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

try:
    print("Testing config import...")
    from config import Config
    print("Config imported successfully.")

    print("\nTesting service layers import...")
    from services.csv_parser import parse_csv_metadata
    from services.validator import validate_csv
    from services.cleaner import clean_csv
    from services.chunker import split_csv
    print("Services imported successfully.")

    print("\nTesting blueprints import...")
    from blueprints.upload.routes import upload_bp
    from blueprints.validation.routes import validation_bp
    from blueprints.cleaning.routes import cleaning_bp
    from blueprints.chunking.routes import chunking_bp
    print("Blueprints imported successfully.")

    print("\nTesting app creation...")
    from app import create_app
    app = create_app()
    print("Flask app factory executed successfully.")

    print("\nAll imports and initializations verified. No errors.")
    sys.exit(0)
except Exception as e:
    import traceback
    print(f"\nImport verification FAILED:")
    traceback.print_exc()
    sys.exit(1)
