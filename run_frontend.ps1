# 워크스페이스 루트(a)에서 실행 — ai_coding_web 프론트로 위임
$ErrorActionPreference = 'Stop'
$inner = Join-Path $PSScriptRoot 'ai_coding_web\run_frontend.ps1'
if (-not (Test-Path $inner)) {
  Write-Error "없음: $inner"
  exit 1
}
& $inner
