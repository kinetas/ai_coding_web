# README: frontend 에서 python -m http.server 5500 — Cursor 터미널용
$ErrorActionPreference = 'Stop'
$frontend = Join-Path $PSScriptRoot 'frontend'
Set-Location $frontend
if (-not (Test-Path 'index.html')) {
  Write-Error "index.html 없음: $frontend"
  exit 1
}
Write-Host ''
Write-Host ' Open: http://127.0.0.1:5500/index.html'
Write-Host ' For API: run .\run_backend.ps1 (or parent folder)'
Write-Host ' Stop: Ctrl+C'
Write-Host ''
if (Get-Command py -ErrorAction SilentlyContinue) {
  & py -3 -m http.server 5500
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
  & python -m http.server 5500
} else {
  Write-Error 'python 또는 py 가 없습니다. Python을 설치하세요.'
  exit 1
}
