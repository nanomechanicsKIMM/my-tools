$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
Write-Host "Installing docling-tools dependencies..."
pip install -r (Join-Path $ScriptDir "requirements.txt")
Write-Host "docling-tools installed." -ForegroundColor Green
