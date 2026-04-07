@echo off
cd /d "%~dp0"
python checkpoint_runner.py %*
pause
