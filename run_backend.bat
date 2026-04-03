@echo off
REM 워크스페이스 루트(a)에서 실행 — ai_coding_web\run_backend.bat 로 위임
setlocal
set "INNER=%~dp0ai_coding_web\run_backend.bat"
if not exist "%INNER%" (
  echo [오류] 다음 파일이 없습니다: %INNER%
  pause
  exit /b 1
)
call "%INNER%"
