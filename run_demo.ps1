# Feature Flag Engine - Quick Demo Launcher
# Run this script to spin up the local backend and TUI dashboard automatically.

$ErrorActionPreference = "Stop"

Clear-Host
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "     FEATURE FLAG ENGINE - DEMO LAUNCHER" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Checking Python Installation
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python is not installed or not in your PATH. Please install Python 3.10+." -ForegroundColor Red
    Exit
}

# 2. Installing Python Dependencies
Write-Host "`n[1/4] Installing Python dependencies..." -ForegroundColor Yellow
Write-Host "Running: pip install -r backend/requirements.txt" -ForegroundColor DarkGray
python -m pip install -r backend/requirements.txt --quiet
Write-Host "Running: pip install -r tui/requirements.txt" -ForegroundColor DarkGray
python -m pip install -r tui/requirements.txt --quiet
Write-Host "Python dependencies installed successfully!" -ForegroundColor Green

# 3. Starting FastAPI Backend
Write-Host "`n[2/4] Launching FastAPI Backend on http://localhost:8000..." -ForegroundColor Yellow
Start-Process cmd -ArgumentList "/k title FF Backend Server && python -m uvicorn main:app --reload" -WorkingDirectory "backend"

# 4. Waiting for Backend to initialize DB
Write-Host "`n[3/4] Waiting 3 seconds for database initialization..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# 5. Starting Terminal Dashboard (TUI)
Write-Host "`n[4/4] Launching Textual Control Panel TUI..." -ForegroundColor Yellow
Start-Process cmd -ArgumentList "/k title FF TUI Dashboard && python app.py" -WorkingDirectory "tui"

# 6. Flutter Instructions
Write-Host "`n==================================================" -ForegroundColor Green
Write-Host "   BACKEND & TUI CONTROL PANEL RUNNING!" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
Write-Host "The backend and TUI are running in separate terminal windows."
Write-Host ""
Write-Host "To start the Flutter Example App, open a terminal and run:" -ForegroundColor Cyan
Write-Host "   cd feature_flag_example" -ForegroundColor DarkYellow
Write-Host "   flutter pub get" -ForegroundColor DarkYellow
Write-Host "   flutter run -d chrome" -ForegroundColor DarkYellow
Write-Host ""
Write-Host "Ready to start the demo walk! Press any key to exit this launcher." -ForegroundColor Gray
