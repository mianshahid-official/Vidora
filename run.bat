@echo off
title Vidora - Media Downloader & Converter
echo ========================================================
echo Starting Vidora...
echo ========================================================

REM Run main application
python main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application exited with an error code.
    pause
)
