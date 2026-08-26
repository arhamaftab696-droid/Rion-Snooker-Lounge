@echo off
title Rion Snooker Lounge - Management Desktop App
echo ===================================================
echo   Rion Snooker Lounge - Desktop Launcher
echo ===================================================
cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH!
    echo Please install Python from https://www.python.org/
    pause
    exit /b
)

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate
    echo Installing required packages...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate
)

echo Starting Desktop App...
start "" python app.py
