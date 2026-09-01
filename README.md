# Cranswick / Tesco — Weekly Review Intelligence Pipeline

## Overview
This pipeline automatically extracts customer reviews from all Cranswick products listed on Tesco.com, triages them for Quality Assurance (QA) risks and Logistics issues, and generates a professional weekly Excel report.

## Architecture (V2)
The engine uses a **V2 Direct API Injection** approach:
1. Launches an invisible Google Chrome browser (headless stealth mode)
2. Blocks all heavy visual resources (images, CSS) for instant page loads
3. Extracts the internal TPNB ID instantly using regex from the raw HTML
4. Directly injects GraphQL API calls into the browser context to fetch reviews
5. Filters to the past 7 days, triages, exports to Excel, and emails stakeholders

## Quick Start

### Prerequisites
```bash
pip install pandas playwright playwright-stealth openpyxl xlsxwriter
playwright install chromium
```

### Usage
1. Open `input/products_to_track.xlsx` and ensure your product list is up to date
2. Setup your `.env` file with SMTP credentials (see `.env.example`)
3. Run the automated pipeline (generates report AND sends email):
```bash
# On Linux/Mac
./run_pipeline.sh

# On Windows
run_pipeline.bat
```

### Configuration
Edit the top of `interceptor_engine.py` to adjust:
- `REPORT_WINDOW_DAYS` — Number of days to include (default: 7)
- `MAX_RETRIES` — Number of retries on transient network errors (default: 3)
- `QA_KEYWORDS` — Words that flag a review as a Critical QA Risk

## Output & Logging
- **Excel Reports:** Saved in the `output/` folder.
- **System Logs:** Saved in the `logs/` folder for IT troubleshooting.

## File Structure
```
Production_Code/
├── run_pipeline.bat         # Windows Task Scheduler entry point
├── run_pipeline.sh          # Linux/Mac Cron entry point
├── run_pipeline_batch.py    # Master script (Scrape + Email)
├── interceptor_engine.py    # Core V2 Playwright scraping engine
├── email_delivery.py        # Automated SMTP distribution module
├── requirements.txt         # Python dependencies
├── DEPLOYMENT_GUIDE.md      # IT setup instructions
├── input/
│   └── products_to_track.xlsx   # Product list to track
└── output/
    └── Tesco_Weekly_Report_YYYY-MM-DD.xlsx
```
