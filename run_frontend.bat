@echo off
REM README: cd frontend 후 python -m http.server 5500 — Cursor 터미널에서 동일 동작
setlocal
cd /d "%~dp0frontend"
if not exist "index.html" (
  echo [오류] index.html 이 없습니다: %CD%
  exit /b 1
)
echo.
echo  Open: http://127.0.0.1:5500/index.html
echo  For API: run run_backend.bat ^(or parent folder^)
echo  Stop: Ctrl+C
echo.
REM Windows: py 런처를 먼저 쓰면 Store 스텁 python.exe 보다 실제 설치본을 씁니다.
where py >nul 2>&1
if %errorlevel% equ 0 goto :run_py
where python >nul 2>&1
if %errorlevel% equ 0 goto :run_python
echo [오류] py 또는 python 을 찾을 수 없습니다. https://www.python.org/ 에서 Python을 설치하세요.
exit /b 1
:run_py
py -3 -m http.server 5500
exit /b %errorlevel%
:run_python
python -m http.server 5500
exit /b %errorlevel%
