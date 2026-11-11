@echo off
cd /d "%~dp0"
echo Starting Vending Machine Motor Test Automation...
python vending_adb_automator.py %*
echo.
pause
