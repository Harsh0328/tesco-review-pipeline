import os
import smtplib
import glob
from email.message import EmailMessage
from datetime import datetime

# ══════════════════════════════════════════════════════════════════════════
# EMAIL CONFIGURATION (Loaded from environment variables)
# ══════════════════════════════════════════════════════════════════════════

SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.office365.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "")

# Comma-separated list of recipients
RECIPIENTS = os.environ.get("RECIPIENT_EMAILS", "qa-team@cranswick.example.com,logistics@cranswick.example.com")


def get_latest_report(output_dir):
    """Finds the most recently generated Excel report in the output directory."""
    list_of_files = glob.glob(os.path.join(output_dir, "*.xlsx"))
    if not list_of_files:
        return None
    # Return the file with the most recent modification time
    return max(list_of_files, key=os.path.getctime)


def send_weekly_email(report_path):
    """Sends the report via email using SMTP."""
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("⚠️  Email delivery skipped: SMTP credentials (SENDER_EMAIL, SENDER_PASSWORD) not configured.")
        return False

    print(f"\n📧 Preparing to email report: {os.path.basename(report_path)}")
    
    msg = EmailMessage()
    msg['Subject'] = f"Automated Tesco Review Intelligence Report - {datetime.today().strftime('%Y-%m-%d')}"
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENTS

    body = f"""Hello Team,

Attached is the automated Tesco Customer Review Intelligence Report for the past 7 days.

This report contains:
- An Executive Summary of all products monitored.
- A detailed breakdown of new reviews.
- Automatic triaging for Critical QA Risks and Logistics Issues.

Please review the 'Reviews' tab for any critical alerts.

Best regards,
Cranswick Automated Data Pipeline
"""
    msg.set_content(body)

    # Attach the Excel file
    with open(report_path, 'rb') as f:
        file_data = f.read()
        file_name = os.path.basename(report_path)

    msg.add_attachment(
        file_data, 
        maintype='application', 
        subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
        filename=file_name
    )

    try:
        print(f"   Connecting to SMTP server {SMTP_SERVER}:{SMTP_PORT}...")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            
        print("   ✅ Email successfully sent to recipients!")
        return True
    except Exception as e:
        print(f"   ❌ Failed to send email: {e}")
        return False


if __name__ == "__main__":
    # Test execution
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
    latest_report = get_latest_report(OUTPUT_DIR)
    
    if latest_report:
        send_weekly_email(latest_report)
    else:
        print("❌ No reports found in the output directory.")
