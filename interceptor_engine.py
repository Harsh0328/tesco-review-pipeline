"""
╔══════════════════════════════════════════════════════════════════════════╗
║  CRANSWICK / TESCO — WEEKLY CUSTOMER REVIEW INTELLIGENCE PIPELINE      ║
║  Architecture: V2 Direct API Injection (Stealth Headless Chrome)       ║
║  Author: Cranswick Data Engineering Team                               ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import re
import logging
from datetime import datetime, timedelta

import pandas as pd
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth


# ══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR   = os.path.join(SCRIPT_DIR, "input")
OUTPUT_DIR  = os.path.join(SCRIPT_DIR, "output")
LOG_DIR     = os.path.join(SCRIPT_DIR, "logs")
INPUT_FILE  = os.path.join(INPUT_DIR, "products_to_track.xlsx")

# How many days back to include in the weekly report
REPORT_WINDOW_DAYS = 7

# Max retries per product if a transient error occurs
MAX_RETRIES = 3

# Fallback API key (intercepted from Tesco frontend)
FALLBACK_API_KEY = "TvOSZJHlEk0pjniDGQFAc9Q59WGAR4dA"

# Smart Triaging Keywords
QA_KEYWORDS = [
    'smell', 'blown', 'sick', 'plastic', 'bone', 'sour',
    'discoloured', 'colour', 'mould', 'hair', 'foreign',
    'contaminated', 'rotten', 'expired', 'green', 'slime', 'slimy'
]
LOGISTICS_KEYWORDS = [
    'driver', 'missing', 'substitute', 'late', 'delivery',
    'damaged', 'squashed', 'crushed', 'broken', 'torn'
]

# Words that cause false positives with simple substring matching
# These are checked with word-boundary regex instead
BOUNDARY_QA_KEYWORDS = ['off']
BOUNDARY_LOGISTICS_KEYWORDS = []


# ══════════════════════════════════════════════════════════════════════════
# LOGGING SETUP
# ══════════════════════════════════════════════════════════════════════════

def setup_logging():
    """Configure dual logging: console + rotating log file."""
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, f"pipeline_{datetime.today().strftime('%Y-%m-%d')}.log")

    logger = logging.getLogger("tesco_pipeline")
    logger.setLevel(logging.INFO)

    # Prevent duplicate handlers on re-runs
    if logger.handlers:
        return logger

    formatter = logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# ══════════════════════════════════════════════════════════════════════════
# INPUT LOADER
# ══════════════════════════════════════════════════════════════════════════

def load_products():
    """Load product list from the input Excel file."""
    os.makedirs(INPUT_DIR, exist_ok=True)
    if not os.path.exists(INPUT_FILE):
        template_df = pd.DataFrame([
            {"NAV Code": "10011247", "Product Name": "Example Product 1", "Tesco URL": "https://www.tesco.com/shop/en-GB/products/316177140"},
            {"NAV Code": "10100822", "Product Name": "Example Product 2", "Tesco URL": "https://www.tesco.com/shop/en-GB/products/303881155"}
        ])
        template_df.to_excel(INPUT_FILE, index=False)
        return template_df.to_dict('records')

    df = pd.read_excel(INPUT_FILE)
    # Drop any junk columns
    df = df[[c for c in df.columns if not c.startswith("Unnamed")]]
    # Strip Google Analytics tracking from URLs
    df['Tesco URL'] = df['Tesco URL'].apply(lambda u: re.sub(r'\?.*$', '', str(u).strip()))
    # Remove duplicates
    df = df.drop_duplicates(subset=['Tesco URL'])
    return df.to_dict('records')


# ══════════════════════════════════════════════════════════════════════════
# TRIAGE LOGIC
# ══════════════════════════════════════════════════════════════════════════

def triage_review(text: str) -> tuple[str, str]:
    """Classify review text into QA Risk, Logistics Issue, or None."""
    if not text:
        return "None", ""
    text_lower = text.lower()

    # Standard substring keywords
    for kw in QA_KEYWORDS:
        if kw in text_lower:
            return "🔴 Critical QA Risk", kw
    for kw in LOGISTICS_KEYWORDS:
        if kw in text_lower:
            return "🟠 Logistics Issue", kw

    # Word-boundary keywords (avoids false positives like "offer", "coffee")
    for kw in BOUNDARY_QA_KEYWORDS:
        if re.search(rf'\b{kw}\b', text_lower):
            return "🔴 Critical QA Risk", kw
    for kw in BOUNDARY_LOGISTICS_KEYWORDS:
        if re.search(rf'\b{kw}\b', text_lower):
            return "🟠 Logistics Issue", kw

    return "None", ""


# ══════════════════════════════════════════════════════════════════════════
# GRAPHQL FETCHER
# ══════════════════════════════════════════════════════════════════════════

def fetch_reviews_page(context, tpnb, offset):
    """Fetch a single page of reviews from the Tesco GraphQL API."""
    payload = [{
        "operationName": "GetReviews",
        "extensions": {"mfeName": "mfe-pdp"},
        "variables": {"tpnb": tpnb, "offset": offset, "count": 10},
        "query": "query GetReviews($tpnb: String, $offset: Int, $count: Int) { reviews(tpnb: $tpnb, offset: $offset, count: $count) { info { total } entries { rating { value } summary text submissionDateTime } } }"
    }]
    return context.request.post(
        "https://xapi.tesco.com/",
        headers={"x-apikey": FALLBACK_API_KEY, "content-type": "application/json", "origin": "https://www.tesco.com"},
        data=json.dumps(payload)
    )


# ══════════════════════════════════════════════════════════════════════════
# CORE ENGINE
# ══════════════════════════════════════════════════════════════════════════

def run_interception_pipeline():
    log = setup_logging()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    products = load_products()
    cutoff_date = datetime.now() - timedelta(days=REPORT_WINDOW_DAYS)
    cutoff_str = cutoff_date.strftime("%Y-%m-%d")
    today_str  = datetime.today().strftime("%Y-%m-%d")

    all_reviews = []
    product_summary = []

    log.info("═" * 65)
    log.info("  CRANSWICK / TESCO — WEEKLY REVIEW PIPELINE")
    log.info(f"  Report Window: {cutoff_str}  →  {today_str}  ({REPORT_WINDOW_DAYS} days)")
    log.info(f"  Products to scan: {len(products)}")
    log.info("═" * 65)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            channel="chrome",
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--window-size=1920,1080",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ]
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="en-GB",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = context.new_page()
        Stealth().apply_stealth_sync(page)

        # V2: Block heavy resources for blazing fast page loads
        page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media", "font", "stylesheet"] else route.continue_())

        for idx, product in enumerate(products, 1):
            name = product.get("Product Name", "Unknown")
            nav  = product.get("NAV Code", "N/A")
            url  = str(product.get("Tesco URL", ""))

            log.info(f"[{idx}/{len(products)}] {name}")

            if not url.startswith("http"):
                log.warning(f"  SKIP: Invalid URL. Check your Excel file.")
                product_summary.append({"NAV Code": nav, "Product Name": name, "Total Reviews": "N/A", "Weekly Reviews": 0, "Status": "❌ Invalid URL"})
                continue

            intercepted_data = []
            success = False

            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    # 1. Load HTML only (fast — images/css blocked)
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)

                    # 2. Extract TPNB instantly from raw HTML
                    html = page.content()
                    tpnb_match = re.search(r'tpnb[^\d]*(\d{5,9})', html, re.IGNORECASE)

                    if not tpnb_match:
                        log.warning(f"  Could not find internal TPNB ID on page. Skipping.")
                        product_summary.append({"NAV Code": nav, "Product Name": name, "Total Reviews": "?", "Weekly Reviews": 0, "Status": "⚠️ No TPNB found"})
                        success = True  # Not a transient error, don't retry
                        break

                    tpnb = tpnb_match.group(1)

                    # 3. Direct API Injection — first page
                    resp = fetch_reviews_page(context, tpnb, 0)
                    if not resp.ok:
                        log.warning(f"  API rejected (Status {resp.status}). Attempt {attempt}/{MAX_RETRIES}.")
                        if attempt < MAX_RETRIES:
                            page.wait_for_timeout(5000 * attempt)
                            continue
                        product_summary.append({"NAV Code": nav, "Product Name": name, "Total Reviews": "?", "Weekly Reviews": 0, "Status": f"❌ API Block ({resp.status})"})
                        success = True
                        break

                    data = resp.json()
                    if not data or not data[0].get('data', {}).get('reviews'):
                        log.info(f"  No reviews available for this product.")
                        product_summary.append({"NAV Code": nav, "Product Name": name, "Total Reviews": 0, "Weekly Reviews": 0, "Status": "— No reviews"})
                        success = True
                        break

                    total = data[0]['data']['reviews']['info'].get('total', 0)
                    entries = data[0]['data']['reviews'].get('entries', [])
                    intercepted_data.extend(entries)

                    # 4. Fetch remaining pages
                    if total > 10:
                        for offset in range(10, total, 10):
                            try:
                                resp = fetch_reviews_page(context, tpnb, offset)
                                if resp.ok:
                                    offset_data = resp.json()
                                    if offset_data and offset_data[0].get('data'):
                                        batch = offset_data[0]['data']['reviews'].get('entries', [])
                                        intercepted_data.extend(batch)

                                        # EARLY EXIT: if entire batch is older than cutoff
                                        old_count = 0
                                        for e in batch:
                                            try:
                                                d = datetime.strptime(e.get('submissionDateTime', '')[:10], "%Y-%m-%d")
                                                if d < cutoff_date:
                                                    old_count += 1
                                            except Exception:
                                                pass
                                        if batch and old_count == len(batch):
                                            break
                            except Exception:
                                pass

                    # 5. Filter to weekly window and triage
                    weekly_count = 0
                    for entry in intercepted_data:
                        date_str = entry.get('submissionDateTime', '')[:10]
                        try:
                            review_date = datetime.strptime(date_str, "%Y-%m-%d")
                            if review_date < cutoff_date:
                                continue
                        except Exception:
                            continue

                        rating = entry.get('rating', {}).get('value', 'N/A')
                        title  = entry.get('summary', '')
                        text   = entry.get('text', '')
                        category, trigger = triage_review(f"{title} {text}")

                        sort_priority = 3
                        if "QA" in category:
                            sort_priority = 1
                        elif rating == 1:
                            sort_priority = 2

                        all_reviews.append({
                            "_sort": sort_priority,
                            "NAV Code": nav,
                            "Product Name": name,
                            "Star Rating": rating,
                            "Review Date": date_str,
                            "Review Title": title,
                            "Review Text": text,
                            "Triage Category": category,
                            "Trigger Word": trigger
                        })
                        weekly_count += 1

                    status = f"✅ {weekly_count} new" if weekly_count > 0 else "— No new reviews"
                    log.info(f"  Total: {total}  |  This week: {weekly_count}  |  {status}")
                    product_summary.append({"NAV Code": nav, "Product Name": name, "Total Reviews": total, "Weekly Reviews": weekly_count, "Status": status})
                    success = True
                    break

                except Exception as e:
                    log.error(f"  Error (attempt {attempt}/{MAX_RETRIES}): {e}")
                    if attempt < MAX_RETRIES:
                        page.wait_for_timeout(5000 * attempt)
                    else:
                        product_summary.append({"NAV Code": nav, "Product Name": name, "Total Reviews": "?", "Weekly Reviews": 0, "Status": "❌ Error"})

        browser.close()

    # ══════════════════════════════════════════════════════════════════════════
    # REPORT GENERATION
    # ══════════════════════════════════════════════════════════════════════════

    output_filename = os.path.join(OUTPUT_DIR, f"Tesco_Weekly_Report_{today_str}.xlsx")

    # Build the reviews dataframe
    if all_reviews:
        df = pd.DataFrame(all_reviews)
        df['Star Rating'] = pd.to_numeric(df['Star Rating'], errors='coerce')
        df = df.drop_duplicates(subset=["Review Date", "Review Title", "Review Text"])
        df = df.sort_values(by=["_sort", "Star Rating", "Review Date"], ascending=[True, True, False])
        df = df.drop(columns=["_sort"])
    else:
        df = pd.DataFrame()

    # Build the summary dataframe
    summary_df = pd.DataFrame(product_summary)

    log.info("═" * 65)
    log.info("  GENERATING WEEKLY REPORT")
    log.info(f"  Window: {cutoff_str} → {today_str}")
    log.info(f"  Reviews found this week: {len(df)}")
    log.info(f"  Products scanned: {len(products)}")
    log.info("═" * 65)

    with pd.ExcelWriter(output_filename, engine='xlsxwriter') as writer:
        workbook = writer.book

        # ── SHEET 1: Executive Summary ──
        summary_df.to_excel(writer, index=False, sheet_name='Summary', startrow=2)
        ws_summary = writer.sheets['Summary']

        title_fmt  = workbook.add_format({'bold': True, 'font_size': 16, 'font_color': '#00539F'})
        sub_fmt    = workbook.add_format({'italic': True, 'font_size': 11, 'font_color': '#666666'})
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#00539F', 'font_color': '#FFFFFF', 'border': 1})

        ws_summary.write(0, 0, "Cranswick / Tesco — Weekly Review Summary", title_fmt)
        ws_summary.write(1, 0, f"Report generated: {today_str}  |  Window: {cutoff_str} to {today_str}  |  Products: {len(products)}  |  New reviews: {len(df)}", sub_fmt)

        for col_num, value in enumerate(summary_df.columns):
            ws_summary.write(2, col_num, value, header_fmt)

        ws_summary.set_column('A:A', 14)
        ws_summary.set_column('B:B', 45)
        ws_summary.set_column('C:C', 14)
        ws_summary.set_column('D:D', 16)
        ws_summary.set_column('E:E', 25)
        ws_summary.freeze_panes(3, 0)
        ws_summary.autofilter(2, 0, len(summary_df) + 2, len(summary_df.columns) - 1)

        # Highlight rows with new reviews in green
        green_fmt = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
        for row_idx, row in summary_df.iterrows():
            if row['Weekly Reviews'] > 0:
                for col_idx in range(len(summary_df.columns)):
                    ws_summary.write(row_idx + 3, col_idx, row.iloc[col_idx], green_fmt)

        # ── SHEET 2: Review Details ──
        if not df.empty:
            df.to_excel(writer, index=False, sheet_name='Reviews', startrow=2)
            ws_reviews = writer.sheets['Reviews']

            ws_reviews.write(0, 0, "Cranswick / Tesco — Weekly Review Detail", title_fmt)
            ws_reviews.write(1, 0, f"Showing reviews from {cutoff_str} to {today_str} only", sub_fmt)

            for col_num, value in enumerate(df.columns):
                ws_reviews.write(2, col_num, value, header_fmt)

            # Conditional formatting: low star ratings
            rating_col = list(df.columns).index("Star Rating")
            red_fmt = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
            ws_reviews.conditional_format(3, rating_col, len(df) + 2, rating_col,
                {'type': 'cell', 'criteria': '<=', 'value': 2, 'format': red_fmt})

            # Conditional formatting: triage categories
            triage_col = list(df.columns).index("Triage Category")
            crit_fmt = workbook.add_format({'bg_color': '#FF0000', 'font_color': '#FFFFFF', 'bold': True})
            log_fmt  = workbook.add_format({'bg_color': '#FFA500', 'font_color': '#000000'})
            ws_reviews.conditional_format(3, triage_col, len(df) + 2, triage_col,
                {'type': 'text', 'criteria': 'containing', 'value': 'QA Risk', 'format': crit_fmt})
            ws_reviews.conditional_format(3, triage_col, len(df) + 2, triage_col,
                {'type': 'text', 'criteria': 'containing', 'value': 'Logistics', 'format': log_fmt})

            # Column widths
            ws_reviews.set_column('A:A', 14)   # NAV Code
            ws_reviews.set_column('B:B', 40)   # Product Name
            ws_reviews.set_column('C:C', 12)   # Star Rating
            ws_reviews.set_column('D:D', 14)   # Review Date
            ws_reviews.set_column('E:E', 35, workbook.add_format({'text_wrap': True}))  # Title
            ws_reviews.set_column('F:F', 60, workbook.add_format({'text_wrap': True}))  # Text
            ws_reviews.set_column('G:G', 22)   # Triage Category
            ws_reviews.set_column('H:H', 16)   # Trigger Word

            ws_reviews.freeze_panes(3, 0)
            ws_reviews.autofilter(2, 0, len(df) + 2, len(df.columns) - 1)
        else:
            # Write an empty reviews sheet with a message
            ws_reviews = workbook.add_worksheet('Reviews')
            ws_reviews.write(0, 0, "No new reviews found in the past 7 days.", title_fmt)

    log.info(f"  Report saved to: {output_filename}")
    log.info(f"  Sheet 1 — 'Summary': {len(products)} products scanned")
    log.info(f"  Sheet 2 — 'Reviews': {len(df)} new reviews this week")


if __name__ == "__main__":
    run_interception_pipeline()
