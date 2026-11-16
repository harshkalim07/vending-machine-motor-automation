@echo off
title Vendiman Vending Motor QA Bench
color 0E
cd /d "%~dp0"
cls

echo ======================================================================
echo          VENDIMAN VENDING MOTOR TEST BENCH - TESTER APP
echo ======================================================================
echo.

:: Detect Python executable
set "PY_CMD=python"
where python >nul 2>&1
if %errorlevel% neq 0 (
    if exist "C:\Python312\python.exe" (
        set "PY_CMD=C:\Python312\python.exe"
    ) else if exist "C:\Python311\python.exe" (
        set "PY_CMD=C:\Python311\python.exe"
    ) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
        set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    ) else (
        echo [ERROR] Python was not found in PATH or standard install paths.
        echo Please ensure Python 3 is installed.
        pause
        exit /b 1
    )
)

echo [1/2] Verified Python runtime (%PY_CMD%)...
echo [2/2] Starting Tester Web Dashboard Server...
echo.
echo ======================================================================
echo   Dashboard URL: http://127.0.0.1:5000
echo   The dashboard will automatically open in your default browser.
echo.
echo   * KEEP THIS TERMINAL WINDOW OPEN WHILE RUNNING TESTS *
echo   * To stop the server, press Ctrl + C or close this window *
echo ======================================================================
echo.

%PY_CMD% app.py

echo.
echo ======================================================================
echo   The server has stopped.
echo ======================================================================
pause
