@echo off
title Vending Machine Complete End-to-End Automation
echo =======================================================================
echo VENDING MACHINE: COMPLETE END-TO-END AUTOMATION
echo (Auto-Login from Tray-1 -> Machine Diagnostics -> 45 Motor Stress Test)
echo =======================================================================
echo.

cd /d "%~dp0"

echo [Phase 1] Auto-navigating to Machine Diagnostics...
python boot_to_diagnostics.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Login/Navigation encountered an issue.
    echo Please check the kiosk screen.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo =======================================================================
echo [Phase 2] Successfully on Diagnostics! Starting 45-Motor Test from Bin 100...
echo =======================================================================
echo.
python vending_adb_automator.py

pause
