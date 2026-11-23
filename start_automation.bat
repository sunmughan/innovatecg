@echo off
title Data Entry Automation Runner (Any CSV)
echo ========================================================
echo   Running Universal Data Entry Automation...
echo ========================================================

cd /d "%~dp0"
call .\venv\Scripts\activate

python -u run_direct.py %*

pause
