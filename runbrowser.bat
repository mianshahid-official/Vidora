@echo off
title OmniDownloader Pro (Browser Mode)
cd /d "%~dp0"

echo ========================================================
echo   OmniDownloader Pro - Launching in Web Browser
echo   Local Address: http://localhost:8000
echo ========================================================
echo.

:: Open default browser after 2 seconds
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:8000"

:: Start the Python backend server
python server.py

pause
