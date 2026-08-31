"""
╔══════════════════════════════════════════════════════════════════════════╗
║  CRANSWICK / TESCO — WEEKLY CUSTOMER REVIEW INTELLIGENCE PIPELINE      ║
║  Architecture: Hybrid Network Interception (Stealth Headless Chrome)   ║
║  Author: Cranswick Data Engineering Team                               ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import os
import json
import re
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
INPUT_FILE  = os.path.join(INPUT_DIR, "products_to_track.xlsx")

# How many days back to include in the weekly report
REPORT_WINDOW_DAYS = 7

# Fallback API key (intercepted from Tesco frontend)
FALLBACK_API_KEY = "TvOSZJHlEk0pjniDGQFAc9Q59WGAR4dA"

# Smart Triaging Keywords
QA_KEYWORDS = [
    'smell', 'blown', 'sick', 'plastic', 'bone', 'sour',
    'discoloured', 'off', 'colour', 'mould', 'hair', 'foreign',
    'contaminated', 'rotten', 'expired', 'green', 'slime', 'slimy'
]
LOGISTICS_KEYWORDS = [
    'driver', 'missing', 'substitute', 'late', 'delivery',
    'damaged', 'squashed', 'crushed', 'broken', 'torn'
]


# ══════════════════════════════════════════════════════════════════════════
# INPUT LOADER
# ══════════════════════════════════════════════════════════════════════════

def load_products():
    """Load product list from the input Excel file."""
    os.makedirs(INPUT_DIR, exist_ok=True)
    if not os.path.exists(INPUT_FILE):
        print(f"⚠️  Input file not found. Creating template at:\n   {INPUT_FILE}")
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
    for kw in QA_KEYWORDS:
        if kw in text_lower:
            return "🔴 Critical QA Risk", kw
    for kw in LOGISTICS_KEYWORDS:
        if kw in text_lower:
            return "🟠 Logistics Issue", kw
    return "None", ""


# ══════════════════════════════════════════════════════════════════════════
# CORE INTERCEPTION ENGINE
# ══════════════════════════════════════════════════════════════════════════

def run_interception_pipeline():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    products = load_products()
    cutoff_date = datetime.now() - timedelta(days=REPORT_WINDOW_DAYS)
    cutoff_str = cutoff_date.strftime("%Y-%m-%d")
    today_str  = datetime.today().strftime("%Y-%m-%d")

    all_reviews = []
    product_summary = []  # Track per-product stats for the summary sheet

    print("═" * 65)
    print(f"  🚀  CRANSWICK / TESCO — WEEKLY REVIEW PIPELINE")
    print(f"  📅  Report Window: {cutoff_str}  →  {today_str}  ({REPORT_WINDOW_DAYS} days)")
    print(f"  📦  Products to scan: {len(products)}")
    print("═" * 65)

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

        for idx, product in enumerate(products, 1):
            name = product.get("Product Name", "Unknown")
            nav  = product.get("NAV Code", "N/A")
            url  = str(product.get("Tesco URL", ""))

            print(f"\n[{idx}/{len(products)}] 📦 {name}")

            if not url.startswith("http"):
                print(f"   ❌ SKIP: Invalid URL (not a link). Check your Excel file.")
                product_summary.append({"NAV Code": nav, "Product Name": name, "Total Reviews": "N/A", "Weekly Reviews": 0, "Status": "❌ Invalid URL"})
                continue

            intercepted_data = []
            api_state = {"key": None, "total": 0, "tpnb": None}

            # --- Network listeners ---
            def handle_request(request):
                if "xapi.tesco.com" in request.url and request.method == "POST":
                    key = request.headers.get("x-apikey") or request.headers.get("x-api-key")
                    if key:
                        api_state["key"] = key
                    try:
                        post_json = request.post_data_json
                        if isinstance(post_json, list):
                            for op in post_json:
                                if op.get("operationName") == "GetReviews":
                                    tpnb = op.get("variables", {}).get("tpnb")
                                    if tpnb:
                                        api_state["tpnb"] = tpnb
                    except Exception:
                        pass

            def handle_response(response):
                if "xapi.tesco.com" in response.url and response.request.method == "POST":
                    try:
                        json_data = response.json()
                        if isinstance(json_data, list) and len(json_data) > 0:
                            data_block = json_data[0].get('data', {})
                            if 'reviews' in data_block and 'entries' in data_block['reviews']:
                                info = data_block['reviews'].get('info', {})
                                api_state["total"] = max(api_state["total"], info.get('total', 0))
                                entries = data_block['reviews']['entries']
                                if entries:
                                    intercepted_data.extend(entries)
                    except Exception:
                        pass

            page.on("request", handle_request)
            page.on("response", handle_response)

            try:
                # 1. Load page to generate Akamai tokens
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3000)

                # Dismiss cookie banner if present
                for sel in ["button:has-text('Accept all')", "button:has-text('Accept')"]:
                    btn = page.query_selector(sel)
                    if btn and btn.is_visible():
                        btn.click()
                        page.wait_for_timeout(1000)
                        break

                # 2. Scroll to trigger reviews API call
                page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.7)")
                page.wait_for_timeout(5000)

                if not api_state["key"]:
                    api_state["key"] = FALLBACK_API_KEY

                # 3. Fetch remaining pages via background API calls
                if api_state["key"] and api_state["tpnb"] and api_state["total"] > 10:
                    total = api_state["total"]
                    tpnb  = api_state["tpnb"]

                    for offset in range(10, total, 10):
                        try:
                            payload = [{
                                "operationName": "GetReviews",
                                "extensions": {"mfeName": "mfe-pdp"},
                                "variables": {"tpnb": tpnb, "offset": offset, "count": 10},
                                "query": "query GetReviews($tpnb: String, $offset: Int, $count: Int) { reviews(tpnb: $tpnb, offset: $offset, count: $count) { entries { rating { value } summary text submissionDateTime } } }"
                            }]
                            resp = context.request.post(
                                "https://xapi.tesco.com/",
                                headers={"x-apikey": api_state["key"], "content-type": "application/json", "origin": "https://www.tesco.com"},
                                data=json.dumps(payload)
                            )
                            if resp.ok:
                                data = resp.json()
                                if data and len(data) > 0 and 'data' in data[0]:
                                    entries = data[0]['data']['reviews'].get('entries', [])
                                    intercepted_data.extend(entries)

                                    # Early exit: if ALL reviews on this page are older than cutoff, stop
                                    old_count = 0
                                    for e in entries:
                                        try:
                                            d = datetime.strptime(e.get('submissionDateTime', '')[:10], "%Y-%m-%d")
                                            if d < cutoff_date:
                                                old_count += 1
                                        except Exception:
                                            pass
                                    if entries and old_count == len(entries):
                                        break

                            page.wait_for_timeout(1000)
                        except Exception:
                            pass

                # 4. Filter to weekly window and triage
                weekly_count = 0
                for entry in intercepted_data:
                    date_str = entry.get('submissionDateTime', '')[:10]
                    try:
                        review_date = datetime.strptime(date_str, "%Y-%m-%d")
                        if review_date < cutoff_date:
                            continue  # Skip old reviews
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
                print(f"   Total: {api_state['total']}  |  This week: {weekly_count}  |  {status}")
                product_summary.append({"NAV Code": nav, "Product Name": name, "Total Reviews": api_state['total'], "Weekly Reviews": weekly_count, "Status": status})

            except Exception as e:
                print(f"   ❌ Error: {e}")
                product_summary.append({"NAV Code": nav, "Product Name": name, "Total Reviews": "?", "Weekly Reviews": 0, "Status": f"❌ {str(e)[:40]}"})
            finally:
                page.remove_listener("request", handle_request)
                page.remove_listener("response", handle_response)

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

    print(f"\n{'═' * 65}")
    print(f"  📊  GENERATING WEEKLY REPORT")
    print(f"  📅  Window: {cutoff_str} → {today_str}")
    print(f"  📝  Reviews found this week: {len(df)}")
    print(f"  📦  Products scanned: {len(products)}")
    print(f"{'═' * 65}")

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

    print(f"\n  ✅  Report saved to: {output_filename}")
    print(f"  📋  Sheet 1 — 'Summary': {len(products)} products scanned")
    print(f"  📋  Sheet 2 — 'Reviews': {len(df)} new reviews this week")
    print()


if __name__ == "__main__":
    run_interception_pipeline()
