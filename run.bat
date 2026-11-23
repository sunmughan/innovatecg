@echo off
title Automated Data Entry Program
echo ========================================================
echo   Starting Data Entry Automation Program...
echo ========================================================

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo [!] Virtual environment not found. Creating one...
    python -m venv venv
    call .\venv\Scripts\activate
    pip install flask playwright selenium pandas requests
    playwright install chromium
) else (
    call .\venv\Scripts\activate
)

echo Starting web server on http://localhost:5000 ...
start "" "http://localhost:5000"
python app.py
pause
