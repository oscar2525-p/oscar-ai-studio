@echo off
title OSCAR AI STUDIO v0.6
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (echo Python 3.10+ is required. Install from python.org and tick Add Python to PATH.& pause & exit /b 1)
if not exist .venv py -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
start "" http://127.0.0.1:5000
python app.py
pause
