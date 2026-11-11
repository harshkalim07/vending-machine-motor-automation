# PowerShell Setup Script for Android Platform-Tools (ADB)
# Used for Vending Machine Motor Test Automation

Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host " VENDING MACHINE MOTOR TEST AUTOMATION - ADB SETUP" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan

$CurrentDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PlatformToolsDir = Join-Path $CurrentDir "platform-tools"
$AdbExe = Join-Path $PlatformToolsDir "adb.exe"

# 1. Check if ADB exists in PATH or local directory
$HasAdb = $false
try {
    $res = Get-Command adb -ErrorAction Stop
    $AdbExe = "adb"
    $HasAdb = $true
    Write-Host "[OK] Found ADB in system PATH." -ForegroundColor Green
} catch {
    if (Test-Path $AdbExe) {
        $HasAdb = $true
        Write-Host "[OK] Found local ADB at: $AdbExe" -ForegroundColor Green
    }
}

# 2. Download official Google platform-tools if not found
if (-not $HasAdb) {
    Write-Host "[INFO] ADB not found. Downloading Google Platform-Tools (Official)..." -ForegroundColor Yellow
    $ZipPath = Join-Path $CurrentDir "platform-tools.zip"
    $Url = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
    
    try {
        Invoke-WebRequest -Uri $Url -OutFile $ZipPath -UseBasicParsing
        Expand-Archive -Path $ZipPath -DestinationPath $CurrentDir -Force
        Remove-Item $ZipPath -Force -ErrorAction SilentlyContinue
        if (Test-Path $AdbExe) {
            Write-Host "[SUCCESS] Downloaded and extracted ADB to: $PlatformToolsDir" -ForegroundColor Green
            $HasAdb = $true
        }
    } catch {
        Write-Host "[ERROR] Could not download platform-tools automatically: $_" -ForegroundColor Red
        Write-Host "Please download platform-tools manually from: $Url" -ForegroundColor Yellow
        exit 1
    }
}

# 3. Test ADB devices
Write-Host "`n[INFO] Checking connected devices..." -ForegroundColor Cyan
& $AdbExe devices

Write-Host "`n---------------------------------------------------------"
Write-Host "HOW DO YOU WANT TO CONNECT TO THE VENDING MACHINE?" -ForegroundColor Yellow
Write-Host "1. USB Cable (Plug laptop directly into vending machine board)"
Write-Host "2. Wi-Fi / LAN (Both laptop and vending machine on same network)"
Write-Host "---------------------------------------------------------"

$choice = Read-Host "Select option (1 or 2)"

if ($choice -eq "2") {
    $ip = Read-Host "Enter Vending Machine IP address (e.g. 192.168.1.100)"
    if ($ip) {
        Write-Host "Connecting to $ip:5555..." -ForegroundColor Cyan
        & $AdbExe connect "$($ip):5555"
        & $AdbExe devices
    }
}

Write-Host "`n[DONE] ADB setup verified! You can now start test automation by running:" -ForegroundColor Green
Write-Host "python vending_adb_automator.py" -ForegroundColor Cyan
