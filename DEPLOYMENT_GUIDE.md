# Cranswick Enterprise IT Deployment Guide
**Project:** Tesco Automated Review Intelligence Pipeline
**Type:** Headless Playwright / Python Automation
**Schedule:** Weekly (Suggested: Mondays @ 3:00 AM)

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
The script is configured to automatically email the Excel report to stakeholders upon completion.
1. Locate `.env.example` in the project folder.
2. Rename it to `.env`.
3. Open it and fill in the SMTP credentials for your corporate email server (e.g., Office365) and the recipient list:
   ```env
   SMTP_SERVER=smtp.office365.com
   SMTP_PORT=587
   SENDER_EMAIL=bot@cranswick.example.com
   SENDER_PASSWORD=your_secure_password
   RECIPIENT_EMAILS=qa.manager@cranswick.co.uk,logistics@cranswick.co.uk
   ```

## 4. Automation via Windows Task Scheduler
To make this run completely hands-off every week:
1. Open **Task Scheduler** on the Windows Server.
2. Click **Create Basic Task**.
    - **Name:** "Tesco Review Scraper"
    - **Trigger:** Weekly -> Monday -> 3:00 AM
    - **Action:** Start a Program
3. **Program/Script:** Browse and select the `run_pipeline.bat` file inside the project folder.
4. **Start in (IMPORTANT):** Enter the absolute path to the project folder (e.g., `C:\Scripts\Tesco_Project_Final\Production_Code\`). *If you leave this blank, the script will crash.*
5. In the final properties window, check **"Run whether user is logged on or not"** and **"Run with highest privileges"**.

## 5. Maintenance
* **Updating Products:** If QA wants to track new products, simply open `input/products_to_track.xlsx` and add the new NAV code, Product Name, and Tesco URL. The script will automatically pick it up on the next run.
