# Cranswick / Tesco — Review Intelligence Pipeline

## Overview
This pipeline automatically extracts customer reviews from all Cranswick products listed on Tesco.com, triages them for Quality Assurance (QA) risks and Logistics issues, and generates professional Excel reports. It supports both **Rolling (e.g. 7-day)** and **Strict Calendar Month** reporting.

## Architecture (V2)
The engine uses a **V2 Direct API Injection** approach:
1. Launches an invisible Google Chrome browser (headless stealth mode)
2. Blocks all heavy visual resources (images, CSS) for instant page loads
3. Extracts the internal TPNB ID instantly using regex from the raw HTML
4. Directly injects GraphQL API calls into the browser context to fetch reviews
5. Filters to the date window, triages, exports to Excel, and emails stakeholders

## Quick Start

### Prerequisites
```bash
pip install pandas playwright playwright-stealth openpyxl xlsxwriter
playwright install chromium
```

### Usage
1. Open `input/products_to_track.xlsx` and ensure your product list is up to date.
2. Setup your `.env` file with SMTP credentials and default lookback days (see `.env.example`).
3. Run the automated pipeline (generates report AND sends email):

**Weekly / Rolling Report:**
```bash
# On Linux/Mac
./run_pipeline.sh

# On Windows
run_pipeline.bat
```

**Monthly Report (Previous Calendar Month):**
```bash
# On Linux/Mac
./run_pipeline_monthly.sh

# On Windows
run_pipeline_monthly.bat
```

## Output & Logging
- **Excel Reports:** Saved in the `output/` folder.
- **System Logs:** Saved in the `logs/` folder for IT troubleshooting.

## File Structure
```
Production_Code/
├── run_pipeline.bat / .sh           # Windows/Linux Weekly Entry Point
├── run_pipeline_monthly.bat / .sh   # Windows/Linux Monthly Entry Point
├── run_pipeline_batch.py            # Master script (Scrape + Email)
├── interceptor_engine.py            # Core V2 Playwright scraping engine
├── email_delivery.py                # Automated SMTP distribution module
├── requirements.txt                 # Python dependencies
├── DEPLOYMENT_GUIDE.md              # IT setup instructions
├── input/
│   └── products_to_track.xlsx       # Product list to track
└── output/
    └── Tesco_..._Report.xlsx
```
