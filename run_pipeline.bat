@echo off
REM ==============================================================================
REM CRANSWICK / TESCO AUTOMATED PIPELINE ENTRY POINT (WINDOWS)
REM This file should be targeted by the Windows Task Scheduler
REM ==============================================================================

echo Starting Tesco Pipeline Batch Job...

REM Change directory to where the script is located
cd /d "%~dp0"

REM Load Environment Variables (SMTP Passwords, etc.)
if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
        set %%A=%%B
    )
)

REM Execute the Python Pipeline
python run_pipeline_batch.py

echo Pipeline Execution Complete.
