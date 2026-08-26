@echo off
title Rion Snooker Lounge - Web Server
echo ===================================================
echo   Rion Snooker Lounge - Local Web Server
echo ===================================================
cd /d "%~dp0"

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate
    echo Installing required packages...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate
)

echo Starting Web Server at http://localhost:8000 ...
start http://localhost:8000
python server.py
