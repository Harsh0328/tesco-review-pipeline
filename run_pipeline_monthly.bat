@echo off
REM ==============================================================================
REM CRANSWICK / TESCO AUTOMATED PIPELINE ENTRY POINT (MONTHLY)
REM This file should be targeted by the Windows Task Scheduler on the 1st of every month
REM ==============================================================================

echo Starting Tesco Pipeline Monthly Batch Job...

REM Change directory to where the script is located
cd /d "%~dp0"

REM Load Environment Variables
if exist ".env" (
    for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do (
        set %%A=%%B
    )
)

REM Execute the Python Pipeline in Monthly Mode
python run_pipeline_batch.py --monthly

echo Pipeline Execution Complete.
