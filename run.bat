@echo off
cd /d "%~dp0"
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
if "%PORT%"=="" set PORT=8000
.venv\Scripts\uvicorn main:app --host 0.0.0.0 --port %PORT%
