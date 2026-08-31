import os
from interceptor_engine import run_interception_pipeline
from email_delivery import send_weekly_email, get_latest_report

def main():
    print("=" * 65)
    print("🚀 INITIATING AUTOMATED PIPELINE BATCH JOB")
    print("=" * 65)
    
    # 1. Run the Web Scraper & Generate Excel
    run_interception_pipeline()
    
    # 2. Find the generated report
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    latest_report = get_latest_report(output_dir)
    
    # 3. Email the report to stakeholders
    if latest_report:
        send_weekly_email(latest_report)
    else:
        print("\n❌ Pipeline completed, but no report was generated to email.")

if __name__ == "__main__":
    main()
