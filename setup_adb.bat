@echo off
cd /d "%~dp0"
echo Setting up Android Platform-Tools (ADB)...
powershell -ExecutionPolicy Bypass -File setup_adb.ps1
echo.
pause
