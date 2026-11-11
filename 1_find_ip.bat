@echo off
cd /d "%~dp0"
echo Scanning network for Vending Machine Android Box...
python find_vending_box_ip.py
echo.
pause
