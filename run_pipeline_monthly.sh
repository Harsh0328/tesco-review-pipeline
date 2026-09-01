#!/bin/bash
# ==============================================================================
# CRANSWICK / TESCO AUTOMATED PIPELINE ENTRY POINT (MONTHLY)
# This file should be targeted by Cron on the 1st of every month
# ==============================================================================

echo "Starting Tesco Pipeline Monthly Batch Job..."

# Change directory to where the script is located
cd "$(dirname "$0")"

# Load Environment Variables (SMTP Passwords, etc.)
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Execute the Python Pipeline in Monthly Mode
python3 run_pipeline_batch.py --monthly

echo "Pipeline Execution Complete."
