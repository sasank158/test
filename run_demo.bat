@echo off
:: Batch wrapper to easily run the PowerShell demo launcher by double-clicking.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_demo.ps1"
pause
