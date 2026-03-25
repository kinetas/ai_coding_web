$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

if (-not (Test-Path '.venv\Scripts\python.exe')) {
  Write-Host 'Creating virtual environment...'
  if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 -m venv .venv
  } else {
    python -m venv .venv
  }
}

& '.\.venv\Scripts\Activate.ps1'
python -m pip install -r requirements.txt
python -m backend.app.init_db
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
