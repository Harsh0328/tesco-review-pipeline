import os
import argparse
from interceptor_engine import run_interception_pipeline
from email_delivery import send_weekly_email, get_latest_report

def main():
    parser = argparse.ArgumentParser(description="Tesco Review Pipeline")
    parser.add_argument('--days', type=int, help="Override the default number of days to look back")
    parser.add_argument('--monthly', action='store_true', help="Run in strict previous-calendar-month mode")
    args = parser.parse_args()

    print("=" * 65)
    mode_str = "MONTHLY" if args.monthly else (f"{args.days}-DAY" if args.days else "STANDARD")
    print(f"🚀 INITIATING AUTOMATED PIPELINE BATCH JOB ({mode_str} MODE)")
    print("=" * 65)
    
    # 1. Run the Web Scraper & Generate Excel
    run_interception_pipeline(days_override=args.days, is_monthly=args.monthly)
    
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
