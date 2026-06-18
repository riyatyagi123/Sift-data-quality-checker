# Project Documentation

## 1. Project Overview

### Problem Solved

Sift Data Validator is a Flask web application for uploading CSV datasets, validating data quality, cleaning invalid or inconsistent values, removing duplicates, and optionally splitting the cleaned dataset into smaller CSV chunks. It is built for tabular transaction/customer-style datasets where common quality problems include missing required fields, malformed phone numbers, mixed date/time formats, duplicate business records, invalid emails, unsupported payment modes, negative amounts, and inconsistent categorical values.

The project exists to turn an uploaded CSV into a more reliable, standardized, downloadable CSV while also exposing validation and cleaning metrics to the user.

### Objectives

- Accept CSV uploads through a browser interface.
- Parse uploaded files and show metadata plus a 10-row preview.
- Dynamically infer common business columns from varied headers.
- Validate rows for completeness, validity, uniqueness, schema confidence, and type-specific rules.
- Clean and standardize recoverable values.
- Remove invalid rows according to the selected cleaning mode.
- Remove duplicate business records after normalization.
- Produce downloadable cleaned, error, warning, duplicate, audit, and removed-column artifacts.
- Split the final cleaned CSV into smaller chunks and package them in a ZIP archive.

### Supported File Formats

The app currently supports only CSV files.

This is enforced in `config.py`:

```python
ALLOWED_EXTENSIONS = {'csv'}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024
```

The stated target is large CSV processing up to about 50 MB. Parsing and cleaning use Pandas chunking in several places to reduce memory pressure.

### End-to-End Workflow

1. User opens `/upload`.
2. Browser posts a CSV file to `POST /upload`.
3. `blueprints/upload/routes.py` sanitizes the filename with `secure_filename`, saves it in `static/uploads`, and calls `services.csv_parser.parse_csv_metadata`.
4. Metadata and the uploaded path are stored in the Flask session.
5. User goes to `/validate`.
6. `static/js/validate.js` calls `POST /validate/run`.
7. `services.validator.validate_csv` preprocesses the CSV, resolves column aliases, classifies the dataset, runs validators, computes quality scores, and returns JSON.
8. User goes to `/clean`.
9. `static/js/clean.js` calls `POST /clean/run` with a cleaning mode: `STRICT`, `SMART`, or `SOFT`.
10. `services.cleaner.clean_csv` validates, analyzes global stats, processes the file in chunks, standardizes values, writes output artifacts, removes final normalized business duplicates, and returns cleaning stats plus an audit trail.
11. User downloads the final cleaned CSV from `/download/cleaned`.
12. Optionally, user goes to `/chunk`, chooses a chunk size, and calls `POST /chunk/generate`.
13. `services.chunker.split_csv` writes chunk files and `chunks.zip`, downloadable from `/download/chunks`.

## 2. Tech Stack

### Frontend

The frontend is server-rendered HTML using Jinja templates and browser-side JavaScript.

- Jinja2 templates through Flask: page layout and route-specific views.
- Tailwind CSS CDN: utility-first styling configured in `templates/layout.html`.
- Custom CSS: `static/css/custom.css` for polish, responsive fixes, scrollbars, and page-specific visual refinements.
- Vanilla JavaScript: AJAX upload, validation, cleaning, and chunk generation.
- Chart.js CDN: validation charts and score visualizations.
- Google Fonts: Inter and Outfit via CDN.

There is no React/Vue/Svelte build pipeline. The UI is simple to run because it depends on Flask templates plus static assets.

### Backend

- Flask: web framework, route dispatch, sessions, templates, JSON responses.
- Pandas: CSV parsing, chunk processing, duplicate detection, profiling, and output writing.
- NumPy: null handling and preprocessing support.
- phonenumbers: country-aware phone parsing, E.164 formatting, validation, national number extraction.
- python-dateutil: flexible date/time parsing.
- gunicorn: production WSGI server for deployment.

### Database and Storage

There is no database.

The app uses filesystem storage:

- Uploaded raw CSVs: `static/uploads/`
- Cleaned and report artifacts: `processed/`
- Chunk files and ZIP archives: `chunks/`
- Session state: Flask signed cookie session containing paths, metadata, and some summary results.

Because state is file-based and session-based, a production deployment should consider cleanup, per-user isolation, and persistent disk configuration.

### Important Dependencies

- `Flask`: web application framework.
- `pandas`: CSV IO, chunked processing, row/column transformations, stats.
- `numpy`: missing-value normalization.
- `phonenumbers`: robust international phone validation.
- `gunicorn`: production server.

The code also imports `dateutil.parser`. It is usually installed as a Pandas dependency, but if dependency resolution fails in a fresh environment, add `python-dateutil` explicitly to `requirements.txt`.

## 3. Folder Structure

### Root Files

#### `app.py`

Application factory and entrypoint.

- Configures logging.
- Creates the Flask app.
- Loads `Config`.
- Ensures `UPLOAD_FOLDER`, `PROCESSED_FOLDER`, and `CHUNKS_FOLDER` exist.
- Registers blueprints:
  - `upload_bp`
  - `validation_bp`
  - `cleaning_bp`
  - `chunking_bp`
- Defines `/` home route.
- Defines generic 404 and 500 handlers.

The architecture uses Flask's application factory pattern lightly through `create_app()`, though it still creates a global `app` at import time for Gunicorn.

#### `config.py`

Central configuration object.

Important settings:

- `SECRET_KEY`: Flask session signing key, read from environment or defaulted.
- `BASE_DIR`: project root.
- `UPLOAD_FOLDER`: `static/uploads`.
- `PROCESSED_FOLDER`: `processed`.
- `CHUNKS_FOLDER`: `chunks`.
- `ALLOWED_EXTENSIONS`: currently only `csv`.
- `MAX_CONTENT_LENGTH`: 50 MB.
- `PREVIEW_ROWS`: 10.

#### `requirements.txt`

Python dependency list.

#### `README.md`

High-level project overview, setup, and deployment guide. `PROJECT_DOCUMENTATION.md` expands on that with implementation details.

#### Test Files

- `test_imports.py`: import sanity checks.
- `test_pipeline.py`: end-to-end parser, validation, cleaning, chunking test.
- `test_schema_agnostic.py`: tests dynamic schema discovery and validation behavior across different dataset shapes.
- `test_cleaning_improvements.py`: tests newer cleaning improvements including date inference, phone handling, and duplicate cleanup behavior.

### `blueprints/`

Blueprints are route/controller modules. They keep request/session handling separate from the service layer.

#### `blueprints/upload/routes.py`

Routes:

- `GET /upload`: renders upload page and optionally resets session state.
- `POST /upload`: validates file presence/type, sanitizes filename, saves CSV, calls `parse_csv_metadata`, stores metadata in session, and returns preview JSON.

Key functions:

- `allowed_file(filename)`: extension allow-list check.
- `upload_file()`: upload controller.

Why it exists: keeps upload validation and session bootstrapping separate from downstream validation and cleaning logic.

#### `blueprints/validation/routes.py`

Routes:

- `GET /validate`: renders validation dashboard if an uploaded file exists.
- `POST /validate/run`: calls `validate_csv(filepath)` and returns validation JSON.

Why it exists: validation can be rerun from the UI without re-uploading the file.

#### `blueprints/cleaning/routes.py`

Routes:

- `GET /clean`: renders cleaning dashboard.
- `POST /clean/run`: runs `clean_csv` with selected mode.
- `GET /download/cleaned`: downloads cleaned CSV.
- `GET /download/errors`: downloads error rows.
- `GET /download/warnings`: downloads warning rows.
- `GET /download/duplicates`: downloads removed duplicate rows.
- `GET /download/audit`: downloads JSON audit trail.
- `GET /download/removed_columns`: downloads removed empty-column metadata.

Why it exists: cleaning creates several output artifacts, so this blueprint owns file naming, session output paths, and secure downloads through `send_from_directory`.

#### `blueprints/chunking/routes.py`

Routes:

- `GET /chunk`: renders chunking UI after a cleaned file exists.
- `POST /chunk/generate`: calls `split_csv`.
- `GET /download/chunks`: serves generated `chunks.zip`.

Why it exists: chunking is a post-cleaning workflow and is intentionally separated from validation/cleaning.

### `services/`

The `services` directory is the core business logic layer.

#### `services/csv_parser.py`

Functions:

- `get_file_size_kb(filepath)`: returns file size.
- `parse_csv_metadata(filepath)`: reads CSV in chunks to count rows, reads first 10 rows for preview, returns filename, row count, column count, headers, size, and preview rows.

Interaction:

- Called by upload route immediately after saving the file.
- The returned metadata is displayed in `upload.html` by `static/js/upload.js`.

#### `services/validator.py`

Main validation engine.

Important responsibilities:

- Preprocesses CSV using `preprocess_csv`.
- Resolves varied headers to known logical fields using `DEFAULT_ALIASES`.
- Classifies dataset type with `classify_dataset_from_headers`.
- Computes schema confidence.
- Infers column types.
- Calculates completeness.
- Calls `detect_all_duplicates`.
- Validates missing values, duplicate records, email, phone, country, date, time, numeric amount, currency, payment mode, and text integrity.
- Produces rule statuses, affected row counts, profiles, issue summaries, validation logs, and quality scores.

Important functions:

- `preprocess_csv(filepath)`: normalizes whitespace/null-like values, drops fully empty rows, and overwrites the input file.
- `normalize_header(header)`: removes spaces/underscores/dashes and lowercases headers.
- `resolve_columns(df_columns)`: maps CSV headers to canonical logical fields.
- `is_missing_value(val)`: detects missing values.
- `validate_numeric(val)`: validates numeric-like values after stripping currency symbols/codes.
- `validate_text(val)`: rejects control-character corruption.
- `normalize_payment_mode(pay_val)`: maps payment modes to a standard label.
- `is_known_payment_mode(pay_val)`: validates payment modes.
- `validate_currency(currency_val)`: validates supported currencies.
- `validate_csv(filepath)`: main orchestration function.

Why it exists: validation must summarize dataset quality without necessarily mutating all values. It generates the data needed by the validation dashboard and informs the cleaner.

#### `services/cleaner.py`

Main cleaning engine.

Important responsibilities:

- Calls validation first to reuse field mapping, column types, and dataset classification.
- Runs a global analyzer to find duplicate IDs, empty columns, imputation values, and date format confidence.
- Processes CSV in chunks of 50,000 rows.
- Drops empty rows and empty columns.
- Handles duplicates.
- Standardizes phone, date, time, email, currency, payment mode, country, names, and text.
- Handles missing values in `SMART` mode with median/mode imputation where allowed.
- Writes cleaned rows, error rows, warning rows, duplicate rows, removed-column metadata, and audit JSON.
- Removes final normalized business duplicates from the fully cleaned output.
- Returns cleaning stats and a limited audit trail preview.

Important functions:

- `clean_phone(phone_val, country_val)`
- `clean_date(date_val, dayfirst=None)`
- `clean_email(email_val)`
- `clean_currency(val)`
- `clean_payment_mode(val)`
- `clean_country(val)`
- `clean_text(val)`
- `clean_name(val)`
- `is_empty_row(row_dict)`
- `remove_cleaned_business_duplicates(output_filepath, duplicates_path, audit_trail)`
- `analyze_csv_globally(input_filepath, col_map, column_types, dataset_type)`
- `clean_csv(input_filepath, output_filepath, removed_filepath, mode='SMART')`

Cleaning modes:

- `STRICT`: retains only rows with no errors and no warnings.
- `SMART`: retains rows with warnings but removes rows with errors. Also imputes some missing non-mandatory values.
- `SOFT`: retains all rows and adds a `status` column (`VALID`, `WARNING`, `ERROR`).

Why it exists: validation identifies quality problems; cleaning applies transformations and creates the final downloadable dataset.

#### `services/phone_validator.py`

Phone validation and normalization.

Important functions:

- `map_country_to_region(country_str)`: maps country names/codes to ISO regions used by `phonenumbers`.
- `get_country_key(country_str)`: wrapper for region resolution.
- `normalize_phone_value(phone)`: strips formatting to digits.
- `validate_phone_details(phone, country)`: country-aware validation using `phonenumbers`.
- `validate_phone(phone, country, rules=None)`: boolean wrapper.
- `clean_phone_val(phone_val, country_val)`: returns national-format digits for valid phone numbers.

Why it exists: phone validation is complex and country-specific; using `phonenumbers` avoids fragile regex-only logic.

#### `services/date_validator.py`

Date parsing, validation, warning generation, and standardization.

Important functions:

- `parse_date(date_val, dayfirst=None)`: uses `dateutil.parser.parse`.
- `validate_date(date_str, dayfirst=None)`: checks parseability.
- `check_date_warnings(date_str, dayfirst=None)`: flags future dates and dates before 2000.
- `clean_date_val(date_val, dayfirst=None)`: standardizes to `YYYY-MM-DD`.
- `infer_date_format_and_confidence(date_strings)`: infers day-first/month-first/year-first and confidence.

Why it exists: CSVs often contain mixed date formats; this module centralizes parsing and ambiguity handling.

#### `services/time_validator.py`

Time parsing, validation, and standardization.

Accepted forms include:

- `HH:MM`
- `HH:MM:SS`
- fractional seconds
- `AM`/`PM`
- ISO timestamps such as `2026-06-18T14:30:45Z`

Important functions:

- `parse_time(time_val)`: parses time-only values or ISO timestamps.
- `validate_time(time_val)`: boolean validation.
- `normalize_time(time_val)`: returns `HH:MM:SS`, severity, and message.
- `clean_time_val(time_val)`: simpler clean/changed tuple.

#### `services/email_validator.py`

Email validation.

Rules include:

- No whitespace.
- Exactly one `@`.
- No double dots.
- Domain must contain a TLD of at least two characters.
- Rejects replacement-character corruption.
- Rejects temporary domains in `TEMP_DOMAINS`.
- Uses a standard email regex for final format validation.

#### `services/duplicate_detector.py`

Duplicate detection utilities.

It detects:

- Duplicate transaction IDs.
- Duplicate emails.
- Duplicate phone numbers.
- Duplicate business records after excluding row identifiers.

Important functions:

- `normalize_header_name(column)`: canonicalizes a header for comparison.
- `is_identifier_column(column)`: detects known identifier columns such as `id`, `testid`, `rowid`, `serialnumber`, `recordno`, `index`, etc.
- `looks_like_row_identifier(series)`: treats a highly unique numeric first column as a generated row identifier.
- `get_business_key_columns(df)`: returns columns that define business uniqueness.
- `normalize_business_value(value, column, country_value='')`: normalizes phone/date/time/country/text values before duplicate comparison.
- `build_business_key_frame(df)`: builds the normalized DataFrame used for duplicate comparison.
- `get_duplicate_mask(df, column, is_phone=False)`: duplicate mask for a single field.
- `detect_all_duplicates(df, col_map)`: returns masks/counts/examples for all duplicate categories.

Why it exists: duplicate rules are shared between validation and final cleaning. The current strategy ignores row IDs and compares normalized business fields, so rows with different IDs but identical business data are treated as duplicates.

#### `services/profiling.py`

Dataset and column profiling.

Important functions:

- `classify_dataset_from_headers(headers)`: scores headers to classify customer, transaction, employee, product, hospital, mixed, or unknown datasets.
- `calculate_schema_confidence(resolved_cols, dataset_type)`: compares resolved columns against expected fields.
- `infer_column_type(df, col)`: classifies columns as email, time, date, numeric, phone, boolean, or text.
- `generate_column_profiles(df, col_map)`: builds per-column completeness and stats.

Why it exists: the validation dashboard needs schema confidence, inferred column types, and profiling metadata without requiring fixed schemas.

#### `services/quality_score.py`

Quality score utilities.

- `get_issue_severity(rule_type)`: maps rules to severity.
- `classify_quality_rating(score)`: Excellent/Good/Average/Poor tiers.
- `calculate_overall_score(completeness, validity, uniqueness)`: weighted score:
  - 30% completeness
  - 50% validity
  - 20% uniqueness

#### `services/chunker.py`

CSV chunking.

Function:

- `split_csv(input_filepath, chunk_size, output_dir)`

It clears old chunks, reads the cleaned CSV in Pandas chunks, writes `chunk_001.csv`, `chunk_002.csv`, etc., and creates `chunks.zip`.

#### `services/reports.py`

Contains `generate_validation_summary(results)`, a text formatter for validation summaries. It is useful for logs or future report export features.

### `templates/`

Templates are server-rendered pages that load the relevant JavaScript for each workflow step.

- `layout.html`: shared shell, navigation, Tailwind configuration, Chart.js import, footer, custom CSS.
- `home.html`: landing page and feature overview.
- `upload.html`: drag-and-drop upload UI and preview table.
- `validate.html`: validation dashboard, score widgets, expectation cards, issue logs.
- `cleaned.html`: cleaning mode selector, cleaned file download buttons, stats, audit log table.
- `chunk.html`: chunk-size selector and generated chunk list.

### `static/`

#### `static/js/upload.js`

Handles drag/drop file upload using `XMLHttpRequest` so upload progress can be displayed. Renders metadata and preview rows from `/upload`.

#### `static/js/validate.js`

Calls `/validate/run`, computes display labels, updates score widgets, progress bars, rule cards, duplicate panels, profile tables, and issue logs.

#### `static/js/clean.js`

Calls `/clean/run`, passes the selected cleaning mode, renders retained/removed/corrected counts, issue-repair metrics, date confidence, and audit trail filters.

#### `static/js/chunk.js`

Calls `/chunk/generate`, validates custom chunk size, and renders chunk filenames.

#### `static/js/responsive.js`

Responsive behavior helpers for the UI.

#### `static/css/custom.css`

Custom styling layered on top of Tailwind CDN utilities.

### Runtime Output Folders

#### `static/uploads/`

Uploaded CSVs. These are session-linked but stored on disk.

#### `processed/`

Generated cleaning and validation artifacts:

- `*_cleaned.csv`
- `*_errors.csv`
- `*_warnings.csv`
- `*_duplicates.csv`
- `*_removed.csv`
- `*_audit_report.json`
- `*_removed_columns.json`

#### `chunks/`

Generated chunk CSVs and `chunks.zip`.

## 4. Application Flow

### Upload

Frontend:

- `upload.html`
- `static/js/upload.js`

Backend:

- `upload_file()` in `blueprints/upload/routes.py`
- `parse_csv_metadata()` in `services/csv_parser.py`

Flow:

1. User selects or drops a CSV.
2. JavaScript posts multipart form data to `/upload`.
3. Flask validates extension and saves the file.
4. Parser counts rows with Pandas chunks and reads the first 10 rows.
5. Session stores `csv_filepath` and `csv_metadata`.

### Parsing

`parse_csv_metadata` uses `pd.read_csv(..., chunksize=50000, dtype=str)` to count rows safely for larger files. It reads `nrows=10` separately for preview.

### Validation

Frontend:

- `validate.html`
- `static/js/validate.js`

Backend:

- `run_validation()` in `blueprints/validation/routes.py`
- `validate_csv()` in `services/validator.py`

Flow:

1. UI calls `/validate/run`.
2. Validator preprocesses the CSV.
3. Columns are resolved using aliases.
4. Dataset type and schema confidence are calculated.
5. Validators run row-by-row.
6. Quality metrics and issue summaries are returned as JSON.

### Cleaning and Standardization

Frontend:

- `cleaned.html`
- `static/js/clean.js`

Backend:

- `run_cleaning()` in `blueprints/cleaning/routes.py`
- `clean_csv()` in `services/cleaner.py`

Flow:

1. UI sends mode to `/clean/run`.
2. Cleaner validates input to reuse mapping and type info.
3. Global analyzer computes imputation values and empty columns.
4. CSV is processed in chunks.
5. Each row is standardized and categorized.
6. Output files are written.
7. Final normalized business duplicate removal runs on the completed cleaned CSV.
8. Audit JSON and stats are returned.

### Metrics

Metrics are generated in Python and displayed in JavaScript:

- Validation metrics: `validate_csv`
- Cleaning metrics: `clean_csv`
- UI rendering: `validate.js` and `clean.js`

### Download

Downloads are handled by `send_from_directory` in `blueprints/cleaning/routes.py` and `blueprints/chunking/routes.py`. This avoids direct arbitrary path serving.

## 5. Validation Engine

### Missing Values

Missing values are handled in two layers.

`preprocess_csv(filepath)`:

- Replaces whitespace-only cells with `NaN`.
- Converts string `null`, `undefined`, and `nan` to `NaN`.
- Drops rows where all cells are empty/null-like.
- Resets the index.
- Overwrites the uploaded file.

`is_missing_value(val)`:

- Treats `None`, Pandas `NaN`, empty strings, whitespace-only strings, `null`, `undefined`, and `nan` as missing.

Note: `N/A` and `None` are mentioned in product expectations but `is_missing_value` currently does not explicitly include `n/a` or `none`. `cleaner.is_empty_row` does include `none` for fully empty row checks. Extending `is_missing_value` to include `none`, `n/a`, `na`, and `nil` would make missing-value handling more complete.

Validation uses missing checks for:

- Mandatory fields.
- Non-mandatory mapped fields.
- Time fields, with special handling if a time can be extracted from a timestamp/date column.

### Duplicate Detection

Duplicate logic lives in `services/duplicate_detector.py`.

The app detects field-level duplicates:

- Transaction ID duplicates.
- Email duplicates.
- Phone duplicates.

It also detects business-record duplicates:

- Identifier columns are ignored.
- Known identifiers include `id`, `testid`, `rowid`, `row`, `rownumber`, `serialnumber`, `serialno`, `serial`, `srno`, `sno`, `slno`, `recordid`, `recordno`, and `index`.
- A highly unique numeric first column is also treated as a generated row identifier.
- Remaining business columns are normalized and compared.

Normalization for duplicate comparison:

- Phone/mobile columns: `clean_phone_val` with country context, fallback to digit-only normalization.
- Date columns: `clean_date_val`.
- Time columns: `normalize_time`.
- Country/nation columns: mapped to canonical lower-case country names.
- Other text: lowercased and whitespace-collapsed.

Comparison approach:

- Builds a normalized business-key DataFrame with `build_business_key_frame`.
- Uses Pandas `duplicated(keep='first')` to mark only later duplicates.
- Uses `duplicated(keep=False)` where all duplicate members are needed.

Validation behavior:

- Later duplicate business records are logged as warning entries:
  - `column`: `Entire_Row`
  - `message`: `Duplicate Record Detected`
  - `severity`: `WARNING`
- The first occurrence is considered the canonical row.

Cleaning behavior:

- Final duplicate removal happens after cleaning/normalization.
- It uses `remove_cleaned_business_duplicates`.
- Removed rows are written to `*_duplicates.csv`.
- Audit trail entries use:
  - `column`: `Entire_Row`
  - `action`: `Duplicate Removed`
  - `severity`: `INFO`

### Phone Validation

Phone validation is implemented in `services/phone_validator.py` using the `phonenumbers` library.

Supported country mappings include:

- India / IN / IND
- Singapore / SG / SGP
- USA / US / United States
- UK / GB / United Kingdom
- Australia / AU / AUS
- UAE / AE / United Arab Emirates

Additional mappings include Canada, Germany, France, Japan, China, Brazil, Italy, Spain, Russia, Netherlands, Switzerland, Sweden, Norway, Denmark, Finland, New Zealand, South Africa, and Hong Kong.

Validation process:

1. Map country string to a region code.
2. Parse phone using `phonenumbers.parse`.
3. Check `is_possible_number` and `is_valid_number`.
4. Format valid numbers as:
   - E.164
   - national
   - international
5. Extract national digits.
6. Enforce strict national-prefix behavior for regions such as GB, AU, and AE.
7. Return detailed metadata or invalid result.

`validate_phone` returns `True` for unknown countries because unknown-country cases are treated as warnings rather than hard validation failures.

`clean_phone_val` returns national-format digits when the phone is valid.

### Date Validation

Date validation is implemented in `services/date_validator.py`.

Parser:

- `dateutil.parser.parse`

Accepted formats:

- Many common formats accepted by dateutil, including `YYYY-MM-DD`, `DD-MM-YYYY`, `MM/DD/YYYY`, timestamps, and variants with separators.

Safeguards:

- Short numeric strings under 8 digits are not parsed as dates.
- Parser exceptions are caught.
- Timezone-aware parsed dates are converted to naive datetimes.

Leap years and invalid dates:

- Handled by `dateutil.parser`.
- Invalid dates like impossible day/month combinations fail parsing.

Ambiguity handling:

- `infer_date_format_and_confidence` inspects date strings and votes for:
  - day-first
  - month-first
  - year-first
  - mixed/ambiguous
- US country rows force month-first parsing through `dayfirst_for_country`.
- Other countries use inferred behavior when available.

Warnings:

- Future dates: `INFO`
- Dates before year 2000: `WARNING`

Cleaning:

- `clean_date_val` standardizes valid dates to `YYYY-MM-DD`.

### Time Validation

Time validation is implemented in `services/time_validator.py`.

Accepted formats:

- `HH:MM`
- `HH:MM:SS`
- fractional seconds
- `AM`/`PM`
- ISO timestamps

Parser:

- Regex determines whether the input is time-only or ISO timestamp.
- `dateutil.parser.parse` handles time-only values.
- `dateutil.parser.isoparse` handles ISO timestamps.

Validation rejects:

- Missing/null-like values.
- Non-matching strings.
- Out-of-range hour/minute/second values.

Cleaning:

- `normalize_time` standardizes valid times to `HH:MM:SS`.
- Missing or invalid times return `ERROR`.

### Email Validation

Implemented in `services/email_validator.py`.

Validation rejects:

- Empty values.
- Spaces or tabs.
- Double dots.
- More or fewer than one `@`.
- Missing local part or domain.
- Missing TLD.
- TLD shorter than 2 characters.
- Temporary domains such as `mailinator.com`, `yopmail.com`, `tempmail.com`, `10minutemail.com`, `dispostable.com`, `guerrillamail.com`, and `trashmail.com`.
- Unicode replacement-character corruption.
- Values failing the final regex.

Cleaning:

- `clean_email` trims, removes whitespace, lowercases, and accepts the cleaned value only if it validates.

### Numeric Validation

Numeric validation is implemented in `validator.validate_numeric`.

Process:

- Strip commas.
- Strip leading/trailing currency symbols, currency codes, and spaces.
- Attempt `float(...)`.
- Negative amount values are flagged as errors for transaction datasets.

Supported currency validation:

- `USD`
- `INR`
- `SGD`
- `AED`
- `GBP`
- `AUD`

## 6. Cleaning Engine

### Missing Value Handling

The cleaner starts with `preprocess_csv`, then uses `analyze_csv_globally` to compute:

- Empty columns.
- Median values for numeric columns.
- Mode values for text-like columns.
- Date format inference.

In `SMART` mode, missing non-mandatory fields can be imputed from `global_impute`.

Mandatory fields are not imputed. Missing mandatory fields become row errors.

Fully empty rows are removed by `is_empty_row`.

Columns with 0% completeness are removed from the cleaned output and listed in `*_removed_columns.json`.

### Duplicate Removal Strategies

The cleaner has two duplicate paths:

1. Legacy ID duplicate handling:
   - `analyze_csv_globally` finds duplicate transaction/customer IDs.
   - Rows with duplicate IDs are written to the duplicates file and removed in `STRICT`/`SMART`.
2. Final normalized business duplicate handling:
   - After cleaned CSV generation, `remove_cleaned_business_duplicates` reloads the cleaned output.
   - It builds a normalized business-key frame.
   - Identifier columns are ignored.
   - Later duplicates are removed.
   - Removed rows are appended to `*_duplicates.csv`.
   - Audit entries are appended.

The second path is important because records can become duplicates only after standardization. For example, `+919876543210` and `9876543210` can become the same national phone number after cleaning.

### Phone Normalization and E.164

`validate_phone_details` computes E.164, national, and international formats for valid phone numbers. The cleaned CSV stores the national digits returned by `clean_phone_val`, not the E.164 string.

The E.164 conversion still matters because it is used internally by `phonenumbers` to validate that a number is real and country-consistent.

### Date Standardization

Dates are standardized to:

```text
YYYY-MM-DD
```

The cleaner uses inferred `dayfirst` behavior and country-specific override for US rows.

### Time Standardization

Times are standardized to:

```text
HH:MM:SS
```

The cleaner also attempts to extract time from date/timestamp-like source values when the mapped time field is missing.

### Text Trimming, Capitalization, and Unicode Normalization

`clean_text`:

- Replaces tabs/newlines with spaces.
- Removes non-ASCII control/corrupt characters.
- Collapses repeated whitespace.
- Trims leading/trailing whitespace.

`clean_name`:

- Applies `clean_text`.
- Title-cases words.
- Preserves known abbreviations like `ID`, `USD`, `EUR`, `AED`, `GBP`, `AUD`, `UAE`, `UPI`, `PAYPAL`, and `SGD`.

## 7. Standardization Module

Standardization is implemented inside `services.cleaner` and helper validators rather than a separate `standardizer.py` module.

### Categorical Values

#### Payment Mode Mapping

`clean_payment_mode` maps:

- `card`, `credit card` -> `Credit Card`
- `upi payment`, `upi` -> `UPI`
- `wire`, `bank transfer` -> `Bank Transfer`
- `cash`, `cod` -> `COD`

`validator.normalize_payment_mode` also recognizes:

- `wallet`, `wallets`, `e-wallet` -> `Wallet`
- `debit card`, `cards` -> `Credit Card`
- `bank_transfer`, `transfer` -> `Bank Transfer`
- `cash on delivery` -> `COD`

There is some overlap but not perfect duplication between validator and cleaner payment-mode mappings. A future refactor should centralize these dictionaries.

#### Currency Mapping

`clean_currency` maps:

- `USD`, `$` -> `USD`
- `INR`, `RS` -> `INR`
- `AED` -> `AED`

Validation accepts `USD`, `INR`, `SGD`, `AED`, `GBP`, and `AUD`.

### Countries

`clean_country` maps:

- `IN`, `INDIA` -> `India`
- `USA`, `US`, `UNITED STATES` -> `United States`
- `AE`, `UNITED ARAB EMIRATES` -> `United Arab Emirates`
- `SG`, `SINGAPORE` -> `Singapore`
- `UK`, `UNITED KINGDOM` -> `United Kingdom`
- `AU`, `AUSTRALIA` -> `Australia`

`phone_validator.map_country_to_region` contains a broader mapping for phone validation.

### Phone Numbers

Phone values are standardized with `clean_phone_val`, which returns national digits for valid numbers.

Examples:

- `+91 98765 43210` with country India -> `9876543210`
- `98765-43210` with country India -> `9876543210`

### Dates

Dates are standardized with `clean_date_val` to `YYYY-MM-DD`.

### Times

Times are standardized with `normalize_time` to `HH:MM:SS`.

### States and Gender

There is no dedicated state or gender standardization module in the current codebase. These values would currently be treated as generic text unless their headers map to one of the known aliases. To add state/gender normalization, create new aliases and cleaning branches, or introduce a dedicated standardization utility.

## 8. Metrics Generation

### Validation Metrics

Generated in `validate_csv`.

Counts:

- `total_records`
- `valid_records`
- `invalid_records`
- `warning_records`
- `error_records`
- `affected_rows` per rule

Scores:

- `completeness_score`: average column completeness.
- `validity_score`: average validity across relevant field types.
- `uniqueness_score`: based on business duplicates, email duplicates, and phone duplicates where applicable.
- `overall_score`: weighted score from `calculate_overall_score`.
- `quality_rating`: Excellent, Good, Average, or Poor.
- `success_rate`: valid records divided by total records.

Profiles:

- `date_profile`
- `email_profile`
- `phone_profile`
- `time_profile`
- `duplicate_profile`
- `column_types`
- `column_completeness`

Issue summaries:

- Aggregated from row errors and warnings.
- Used by validation UI issue logs and recommendation cards.

### Cleaning Metrics

Generated in `clean_csv`.

Counters:

- `total_processed`
- `rows_corrected`
- `rows_removed`
- `rows_retained`
- `phones_fixed`
- `emails_fixed`
- `dates_fixed`
- `times_fixed`
- `currencies_fixed`
- `countries_fixed`
- `payment_modes_fixed`
- `duplicates_removed`
- `empty_rows_removed`
- `empty_columns_removed`
- `rows_imputed`

Post-clean metrics:

- `total_records`
- `total_rows`
- `valid_rows`
- `invalid_rows`
- `unique_records`
- `unique_rows`
- `uniqueness_score`
- `validity_score`
- `completeness_score`
- `quality_score`
- `quality_rating`
- `success_rate`

### Charts and UI Display

Charts and dashboard widgets are rendered client-side.

- `static/js/validate.js` consumes validation JSON, updates score rings, progress bars, rule cards, duplicate panels, issue logs, and profile tables.
- `static/js/clean.js` consumes cleaning JSON, updates cleaned/removed/corrected counts, issue resolution rate, date confidence, and audit log tables.
- Chart.js is loaded globally in `layout.html`.

## 9. AI Components

The application does not use AI, LLMs, prompts, embeddings, or model calls.

All validation, cleaning, profiling, duplicate detection, and metric generation are deterministic Python/Pandas rules.

## 10. Performance and Security

### Performance

CSV parsing:

- `parse_csv_metadata` reads in chunks of 50,000 rows for row counting.

Cleaning:

- `clean_csv` reads input in chunks of 50,000 rows.
- It writes chunk outputs incrementally to avoid holding every cleaned row in memory.

Global analysis:

- `analyze_csv_globally` performs a two-pass-style analysis to compute duplicate IDs, imputation data, empty columns, and date format inference.

Chunking:

- `split_csv` uses Pandas `chunksize=chunk_size`.

Potential bottlenecks:

- `validate_csv` reads the full CSV into memory.
- Final business duplicate removal reloads the cleaned output into memory.
- Duplicate business-key normalization uses row-wise Pandas `apply`, which is simpler but slower than vectorized operations for very large files.

The README claims support up to 1M rows / 50 MB. The 50 MB limit is enforced. True 1M-row behavior depends on row width and available memory because validation and final dedupe are not fully streaming.

### Security

Implemented safeguards:

- File extension allow-list for CSV.
- Flask `MAX_CONTENT_LENGTH` of 50 MB.
- `secure_filename` for uploaded filenames.
- Download endpoints use `send_from_directory`, reducing path traversal risk.
- Session paths are checked for existence before use.

Security concerns and future hardening:

- Default `SECRET_KEY` is hardcoded for development; production must set `SECRET_KEY`.
- Uploaded files are stored under `static/uploads`, which can expose files if static serving is configured broadly.
- No authentication or per-user authorization.
- Session isolation uses filenames and a default chunk session ID; concurrent users with same filenames can overwrite outputs.
- No scheduled cleanup of uploaded, processed, or chunk files.
- CSV formula injection is not mitigated. If cleaned files are opened in spreadsheet apps, cells beginning with `=`, `+`, `-`, or `@` can be risky.

### Temporary File Handling

Files are stored permanently until manually deleted or overwritten:

- Uploads in `static/uploads`.
- Artifacts in `processed`.
- Chunks in `chunks`.

`split_csv` clears old CSV/ZIP files inside its output directory before writing new chunk files. Upload and processed folders do not have general cleanup.

## 11. Limitations and Future Improvements

Current limitations:

- CSV only; no XLSX, JSON, Parquet, or TSV support.
- No database or persistent job tracking.
- No authentication.
- No background jobs; long validations run inside web requests.
- Validation loads full CSV into memory.
- Final duplicate cleanup loads full cleaned CSV into memory.
- Some standardization mappings are duplicated across validator and cleaner.
- Missing-value handling does not consistently include all variants such as `N/A`, `NA`, or `None`.
- State and gender standardization are not implemented.
- Uploaded and processed files are not automatically cleaned up.
- No user/project namespace, so filename collisions can overwrite files.
- Some output artifacts from previous test/manual runs live in `processed` and `chunks`.
- Frontend uses CDN dependencies, requiring internet access for Tailwind, Chart.js, and fonts.

Future improvements:

- Add background job queue for validation/cleaning.
- Store runs in a database with job IDs and user ownership.
- Add streaming validation or chunked metrics aggregation.
- Centralize standardization dictionaries.
- Add state/gender mappings.
- Add XLSX support.
- Add file cleanup/retention policy.
- Add CSV formula-injection protection.
- Add more configurable duplicate business-key rules.
- Add unit tests around every validator and cleaner branch.
- Add OpenAPI-style documentation for JSON routes.
- Add production-safe logging and structured audit storage.

## 12. Developer Guide

### Installation

Prerequisites:

- Python 3.12+
- pip

Install dependencies:

```bash
pip install -r requirements.txt
```

If `dateutil` is missing in a fresh environment:

```bash
pip install python-dateutil
```

### Running Locally

```bash
python app.py
```

Open:

```text
http://localhost:5000
```

### Environment Variables

Recommended:

```bash
SECRET_KEY=<secure-random-secret>
```

If not set, the app uses the development fallback in `config.py`.

### Running Tests

Useful smoke tests:

```bash
python test_imports.py
python test_pipeline.py
python test_schema_agnostic.py
python test_cleaning_improvements.py
```

These tests write temporary files under `processed` and `chunks`.

### Adding a New Validator

1. Decide whether the validator is field-specific or generic.
2. If it needs header detection, add aliases to `DEFAULT_ALIASES` in `services/validator.py`.
3. Add any parsing/validation helpers to a focused service module, following the pattern of `email_validator.py`, `phone_validator.py`, `date_validator.py`, or `time_validator.py`.
4. In `validate_csv`:
   - Add the rule to `run_checks`.
   - Add affected-index tracking.
   - Add row-level validation in the row loop.
   - Add `set_status(...)`.
   - Add profile counts/examples if the UI needs them.
   - Include the rule in `validation_results`.
   - Include the issue in `get_friendly_rule_name`.
5. Update `static/js/validate.js` and `templates/validate.html` only if the dashboard needs new UI fields.
6. Add tests.

### Adding a New Cleaning Rule

1. Add helper function to `services/cleaner.py` or a dedicated module.
2. Add a branch in the `for field, col_name in col_map.items()` loop inside `clean_csv`.
3. Update stats counters if needed.
4. Append audit entries with:
   - row
   - column
   - original
   - cleaned
   - action
   - severity
5. Decide behavior by mode:
   - error means removal in `STRICT` and `SMART`
   - warning means removal only in `STRICT`
   - `SOFT` retains rows with status
6. Add focused tests.

### Adding a New Standardization Dictionary

Recommended approach:

1. Put the dictionary near the helper function or in a new central module.
2. Normalize keys consistently: trim, lowercase/uppercase as appropriate.
3. Return `(cleaned_value, changed_bool)`.
4. Log standardization actions in the audit trail.
5. Update duplicate normalization if the standardized field affects business-key uniqueness.

### Deployment Process

For Render or similar platforms:

1. Push the repository to GitHub/GitLab.
2. Create a Python web service.
3. Build command:

```bash
pip install -r requirements.txt
```

4. Start command:

```bash
gunicorn app:app
```

5. Set `SECRET_KEY`.
6. Ensure the platform provides writable storage for `static/uploads`, `processed`, and `chunks`, or replace filesystem storage with object storage.

## 13. Conclusion

This project uses a modular Flask MVC/service-layer architecture:

- Flask blueprints act as controllers.
- Jinja templates and static JavaScript act as the view layer.
- `services/` modules contain the validation, cleaning, profiling, duplicate detection, scoring, parsing, and chunking business logic.
- The data workflow is a pipeline: upload, parse, validate, clean, standardize, deduplicate, score, download, and optionally chunk.

The most important design choice is separation of route handling from data-quality logic. Routes only coordinate HTTP requests, sessions, filenames, and downloads. Services own the actual CSV transformations and metrics. This makes the project understandable and extendable: new validators and cleaning rules should usually be added in `services/`, then surfaced through the existing JSON dashboards only when UI changes are required.

