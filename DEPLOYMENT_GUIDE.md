# Cranswick Enterprise IT Deployment Guide
**Project:** Tesco Automated Review Intelligence Pipeline
**Type:** Headless Playwright / Python Automation
**Schedule:** Weekly (Mondays) AND Monthly (1st of the month)

---

## 1. Hosting Requirements
This script uses advanced network interception and TLS fingerprinting to bypass Tesco's Akamai bot protection. 
* **DO NOT** deploy this to a standard AWS/Azure Linux cloud server unless you route traffic through a residential proxy. Akamai will instantly block AWS datacenter IP addresses.
* **RECOMMENDED SETUP:** Deploy on an internal Cranswick **Windows Server VM** located on the corporate network (or a spare office desktop). This ensures the traffic looks like legitimate UK residential/corporate web traffic.

## 2. Server Provisioning
1. Install **Python 3.10+** (Ensure `python` and `pip` are added to system PATH).
2. Clone or copy the `Production_Code/` folder to the server.
3. Open a Command Prompt in the folder and install dependencies:
   ```cmd
   pip install pandas playwright playwright-stealth openpyxl xlsxwriter
   playwright install chromium
   ```

## 3. Email & Environment Configuration
The script is configured to automatically email the Excel report to stakeholders upon completion, and dynamically adjust its lookback window.
1. Locate `.env.example` in the project folder and rename it to `.env`.
2. Open it and configure the rolling days and SMTP credentials:
   ```env
   DEFAULT_REPORT_DAYS=7
   
   SMTP_SERVER=smtp.office365.com
   SMTP_PORT=587
   SENDER_EMAIL=bot@cranswick.co.uk
   SENDER_PASSWORD=your_secure_password
   RECIPIENT_EMAILS=qa.manager@cranswick.co.uk,logistics@cranswick.co.uk
   ```

## 4. Automation via Windows Task Scheduler
To make this run completely hands-off, you will need to set up **TWO** Scheduled Tasks:

### Task A: The Weekly Rolling Report
1. Open **Task Scheduler** and click **Create Basic Task**.
2. **Name:** "Tesco Review Scraper - Weekly"
3. **Trigger:** Weekly -> Monday -> 3:00 AM
4. **Action:** Start a Program
5. **Program/Script:** Select the `run_pipeline.bat` file inside the project folder.
6. **Start in (IMPORTANT):** Enter the absolute path to the project folder (e.g., `C:\Scripts\Tesco_Project\Production_Code\`).
7. Check **"Run whether user is logged on or not"** and **"Run with highest privileges"**.

### Task B: The Monthly Calendar Report
1. Create a second Basic Task.
2. **Name:** "Tesco Review Scraper - Monthly"
3. **Trigger:** Monthly -> Select all months -> Days: 1st -> 4:00 AM
4. **Program/Script:** Select the `run_pipeline_monthly.bat` file inside the project folder.
5. **Start in (IMPORTANT):** Enter the absolute path to the project folder (same as above).
6. Check **"Run whether user is logged on or not"** and **"Run with highest privileges"**.

## 5. Maintenance & Logs
* **Updating Products:** If QA wants to track new products, they simply open `input/products_to_track.xlsx` and add the new NAV code, Product Name, and Tesco URL. (The script automatically parses hidden Excel hyperlinks).
* **Logs:** If a scheduled task fails, check the `logs/` folder for timestamped debug information.
