# Cranswick / Tesco — Weekly Review Intelligence Pipeline

## Overview
This pipeline automatically extracts customer reviews from all Cranswick products listed on Tesco.com, triages them for Quality Assurance (QA) risks and Logistics issues, and generates a professional weekly Excel report.

## Architecture
The engine uses a **Hybrid Network Interception** approach:
1. Launches an invisible Google Chrome browser (headless stealth mode)
2. Navigates to each product page to generate valid Akamai security tokens
3. Intercepts the hidden GraphQL API responses containing review data
4. Programmatically fetches all remaining pages via background API calls
5. Filters to the past 7 days, triages, and exports to Excel

## Quick Start

### Prerequisites
```bash
pip install pandas playwright playwright-stealth openpyxl xlsxwriter
playwright install chromium
```

### Usage
1. Open `input/products_to_track.xlsx` and ensure your product list is up to date
2. Run the pipeline:
```bash
python3 interceptor_engine.py
```
3. Open the report from the `output/` folder

### Configuration
Edit the top of `interceptor_engine.py` to adjust:
- `REPORT_WINDOW_DAYS` — Number of days to include (default: 7)
- `QA_KEYWORDS` — Words that flag a review as a Critical QA Risk
- `LOGISTICS_KEYWORDS` — Words that flag a review as a Logistics Issue

## Output
The Excel report contains two sheets:
- **Summary** — One row per product showing total reviews, weekly count, and status
- **Reviews** — Full detail of every new review this week, sorted with QA risks at the top

## File Structure
```
Production_Code/
├── interceptor_engine.py    # Main pipeline script
├── requirements.txt         # Python dependencies
├── PROJECT_PLAN.md          # Architecture documentation
├── README.md                # This file
├── input/
│   └── products_to_track.xlsx   # Your product list (NAV Code, Name, URL)
└── output/
    └── Tesco_Weekly_Report_YYYY-MM-DD.xlsx   # Generated reports
```
