#!/bin/bash
# Double-clickable macOS launcher for Transaction AI Scanner

# Navigate to the script's directory
cd "$(dirname "$0")"

# Check if venv exists
if [ -d "venv" ]; then
    PYTHON_EXEC="./venv/bin/python"
else
    PYTHON_EXEC="python3"
fi

# Run the desktop application
$PYTHON_EXEC app.py
