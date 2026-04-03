# 워크스페이스 루트(a)에서 실행 — ai_coding_web 백엔드로 위임
# (a 폴더에서 직접 pip/python 쓰지 말고, 이 스크립트 또는 ai_coding_web\run_backend.bat 사용)
$ErrorActionPreference = 'Stop'
$inner = Join-Path $PSScriptRoot 'ai_coding_web\run_backend.bat'
if (-not (Test-Path $inner)) {
  Write-Error "다음 경로가 없습니다. 워크스페이스 루트에서 실행했는지 확인하세요: $inner"
  exit 1
}
& $inner
