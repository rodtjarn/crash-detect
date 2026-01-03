#!/bin/bash
# Wrapper script to run ML-based daily analysis with correct Python venv
# Runs at 2:00 PM CST (3:00 PM ET) daily - 1 hour before market close
# Sends ALERT or INFO email based on ML crash detection

# Set the project directory
PROJECT_DIR="/home/per/Work/crash-detect"

# Change to project directory
cd "$PROJECT_DIR" || exit 1

# Use the venv Python directly (no need to activate)
"$PROJECT_DIR/venv/bin/python" "$PROJECT_DIR/auto_daily_analysis.py"

# Set next wake time for tomorrow (or next trading day)
"$PROJECT_DIR/set_rtc_wake.sh"

# Exit with the same code as the Python script
exit $?
