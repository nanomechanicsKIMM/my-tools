# install-prereqs.ps1 -- Install OS-level prerequisites via winget
# Idempotent: skips packages already installed.
$ErrorActionPreference = "Stop"

function Install-WingetPkg {
    param([string]$Id, [string]$DisplayName = $null)
    if (-not $DisplayName) { $DisplayName = $Id }
    $listed = winget list --id $Id --exact --accept-source-agreements 2>$null | Out-String
    if ($listed -match [regex]::Escape($Id)) {
        Write-Host "  [skip] $DisplayName already installed"
        return
    }
    Write-Host "  [install] $DisplayName ..."
    winget install --id $Id --exact --silent --accept-package-agreements --accept-source-agreements | Out-Null
}

Write-Host "=== install-prereqs (winget) ==="

# Core tools
Install-WingetPkg "Git.Git" "Git"
Install-WingetPkg "OpenJS.NodeJS.LTS" "Node.js LTS"
Install-WingetPkg "EclipseAdoptium.Temurin.21.JDK" "OpenJDK 21 (Temurin)"

# Python -- prefer Miniconda for parity with current setup
Install-WingetPkg "Anaconda.Miniconda3" "Miniconda3"

# Optional UI tools
Install-WingetPkg "Obsidian.Obsidian" "Obsidian"

Write-Host ""
Write-Host "=== Node.js global packages ==="
$npmPkgs = Get-Content (Join-Path $PSScriptRoot "npm-globals.txt") | Where-Object { $_ -and -not $_.StartsWith("#") }
foreach ($pkg in $npmPkgs) {
    Write-Host "  npm install -g $pkg"
    npm install -g $pkg --silent 2>&1 | Out-Null
}

Write-Host ""
Write-Host "=== Python packages ==="
$python = if ($env:PYTHON) { $env:PYTHON } else { "python" }
$reqFile = Join-Path $PSScriptRoot "python-requirements.txt"
if (Test-Path $reqFile) {
    & $python -m pip install --upgrade pip
    & $python -m pip install -r $reqFile
} else {
    Write-Host "  python-requirements.txt not found; skip"
}

Write-Host ""
Write-Host "Done. Open a NEW terminal so PATH changes take effect, then run clone-marketplaces.ps1."
