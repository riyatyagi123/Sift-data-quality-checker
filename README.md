# Sift Data Validator

Sift Data Validator is a production-ready, high-performance Flask web application built to parse, validate, clean, and chunk large CSV transaction datasets (up to 1M rows, 50MB). It features a clean, responsive layout with TailwindCSS, real-time AJAX uploads, interactive Chart.js quality reports, and file export packages.

---

## Features

1. **Memory-Efficient CSV Parsing**:
   - Uses Pandas chunking to process large files without exhausting RAM.
   - Infers columns and provides a 10-row HTML preview.
2. **Configurable Rule Validation**:
   - Dynamic phone number verification based on country-specific digits and prefixes loaded from `country_rules.json` (supported countries: India, Singapore, USA, UK, Australia, UAE).
   - Multi-format date string validation.
   - Missing mandatory fields check.
   - Transaction ID duplication scans and negative amount errors.
   - Restrictive currency and payment mode compliance filters.
3. **Data Cleaning & Standardization**:
   - Automated phone digit normalization and country prefix stripping.
   - Date formats normalized to `YYYY-MM-DD`.
   - String trimming, hidden characters removal, and case alignment.
   - Discards error-flagged records and saves them separately.
4. **CSV Chunking**:
   - Split large CSV files into preset (1,000, 5,000, 10,000) or custom sized files.
   - Preserves column headers and generates a single downloadable `.zip` package.

---

## Project Structure

```text
project/
│
├── app.py                # Flask entry point and logger config
├── config.py             # App environment limits and secret keys
├── country_rules.json    # Configurable phone validation thresholds
├── requirements.txt      # Dependency package specification
├── README.md             # Project documentation and Render deployment guide
│
├── blueprints/           # Flask modular blueprint routing controllers
│   ├── upload/           # CSV Upload routes
│   ├── validation/       # Analytics reporting routes
│   ├── cleaning/         # Cleaning logs and file output routes
│   └── chunking/         # CSV splitting and zip download routes
│
├── services/             # Core service engine layers
│   ├── csv_parser.py     # Chunked reader and metadata parser
│   ├── validator.py      # Rule engine validator
│   ├── cleaner.py        # Value standardizer and row drop filter
│   ├── chunker.py        # CSV splitter and zip packer
│   └── reports.py        # Terminal formatting and logger helpers
│
├── templates/            # Jinja2 Layout and views
│   ├── layout.html       # Global navbar, scripts, and Inter font layout
│   ├── home.html         # Landing hero and validation mockup dashboard
│   ├── upload.html       # Dropzone card and preview table
│   ├── validate.html     # Summary cards, live Chart.js donut and issue logs
│   ├── cleaned.html      # Cleaning results metrics and CSV download
│   └── chunk.html        # Sizing selections and Zip generator
│
└── static/               # Public assets
    ├── css/              # Custom stylesheets (animations, grid backgrounds)
    ├── js/               # Step-by-step frontend AJAX controller scripts
    └── uploads/          # Temporary cache folder for original CSVs
```

---

## Local Development Installation

### Prerequisites
- Python 3.12+
- pip

### Setup Instructions
1. Clone the project files.
2. Open a terminal in the project directory.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the local development server:
   ```bash
   python app.py
   ```
5. Open your browser and navigate to `http://localhost:5000`.

---

## Deployment Guide for Render

This application is fully compatible with [Render](https://render.com/) for quick cloud hosting.

### Step 1: Push Project to GitHub / GitLab
Make sure all project files (including `requirements.txt` and `app.py`) are pushed to a public or private repository on GitHub or GitLab.

### Step 2: Create a Web Service on Render
1. Log in to your Render Dashboard.
2. Click **New +** and select **Web Service**.
3. Connect your GitHub repository containing the Sift Data Validator.

### Step 3: Configure Settings
- **Name**: `sift-data-validator`
- **Region**: Select a region closest to your users.
- **Branch**: `main` (or your active branch)
- **Root Directory**: Leave empty if your project files are in the repository root.
- **Runtime**: `Python`
- **Build Command**:
  ```bash
  pip install -r requirements.txt
  ```
- **Start Command**:
  Use `gunicorn` to run the production-grade WSGI server:
  ```bash
  gunicorn app:app
  ```

### Step 4: Environment Variables (Optional but Recommended)
Under the **Environment** tab, click **Add Environment Variable**:
- Key: `SECRET_KEY`
- Value: *[A long, secure random string]*

### Step 5: Deploy
Click **Create Web Service**. Render will pull the repository, build dependencies, run Gunicorn, and allocate a free `https://*.onrender.com` URL.

---

## Architecture & Code Quality Features

- **Decoupled Architecture**: Routes only manage request decoding and session data. Calculations are executed in isolated, type-hinted service layers (`csv_parser.py`, `validator.py`, etc.).
- **Stream Processing**: By combining Pandas chunksize limits and Cap buffers on log display, the system can parse massive files safely on small VMs.
- **Path Traversal Shield**: All download endpoints (`/download/cleaned`, `/download/chunks`) route through secure path-building modules (`send_from_directory`) to prevent arbitrary directory file disclosure.
