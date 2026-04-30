# clone-marketplaces.ps1 -- Clone external Claude Code marketplaces referenced
# in claude-config/settings.json.template's extraKnownMarketplaces.
# Idempotent: pulls if directory exists; clones otherwise.
$ErrorActionPreference = "Stop"

$repos = @(
    @{ Url = "https://github.com/orientpine/honeypot";        Dir = "honeypot" },
    @{ Url = "https://github.com/yeachan-heo/oh-my-claudecode"; Dir = "oh-my-claudecode" },
    @{ Url = "https://github.com/RobThePCGuy/Claude-Patent-Creator"; Dir = "Claude-Patent-Creator" }
)

Write-Host "=== clone-marketplaces ==="

foreach ($r in $repos) {
    $target = Join-Path $env:USERPROFILE $r.Dir
    if (Test-Path (Join-Path $target ".git")) {
        Write-Host "  [pull] $($r.Dir)"
        git -C $target pull --ff-only
    } else {
        Write-Host "  [clone] $($r.Url) -> $target"
        git clone $r.Url $target
    }
}

Write-Host ""
Write-Host "Done. claude-config/settings.json.template references:"
foreach ($r in $repos) {
    Write-Host "  $env:USERPROFILE\$($r.Dir)"
}
