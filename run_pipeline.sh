#!/bin/bash
# ==============================================================================
# CRANSWICK / TESCO AUTOMATED PIPELINE ENTRY POINT (LINUX/MAC)
# This file should be targeted by Cron
# ==============================================================================

echo "Starting Tesco Pipeline Batch Job..."

# Change directory to where the script is located
cd "$(dirname "$0")"

# Load Environment Variables (SMTP Passwords, etc.)
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | awk '/=/ {print $1}')
fi

# Execute the Python Pipeline (adjust python3 path if using virtual environments)
python3 run_pipeline_batch.py

echo "Pipeline Execution Complete."
