@echo off
cd /d "%~dp0"
echo Connecting to Vending Machine...
python connect_to_machine.py
echo.
pause
