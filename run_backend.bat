@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  where py >nul 2>&1
  if %errorlevel% equ 0 (
    py -3 -m venv .venv
  ) else (
    python -m venv .venv
  )
  if errorlevel 1 exit /b 1
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 exit /b 1

python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

python -m backend.app.init_db
if errorlevel 1 exit /b 1

python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
