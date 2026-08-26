#!/bin/bash
# Double-clickable macOS launcher for TransactionAI Web Server

cd "$(dirname "$0")"

if [ -d "venv" ]; then
    PYTHON_EXEC="./venv/bin/python"
else
    PYTHON_EXEC="python3"
fi

echo "Starting TransactionAI Web Server at http://localhost:8000 ..."
# Open browser in background after 1 second
(sleep 1.2 && open http://localhost:8000) &

$PYTHON_EXEC server.py
