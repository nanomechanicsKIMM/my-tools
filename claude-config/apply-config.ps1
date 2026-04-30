# apply-config.ps1 — wrapper around apply-config.py
# Pass --dry-run to validate without writing.
$ErrorActionPreference = "Stop"
$python = if ($env:PYTHON) { $env:PYTHON } else { "python" }
$script = Join-Path $PSScriptRoot "apply-config.py"
& $python $script @args
