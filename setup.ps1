# my-tools setup: Codex skills + Claude Code plugins
$ErrorActionPreference = "Stop"
$RepoRoot = $PSScriptRoot

# ─── 1. Skills → Codex ────────────────────────────────────────────────────────
function Install-CodexSkills {
    $CodexSkills = if ($env:CODEX_HOME) { Join-Path $env:CODEX_HOME "skills" } else { Join-Path $env:USERPROFILE ".codex\skills" }
    $SkillsSrc = Join-Path $RepoRoot "skills"
    if (-not (Test-Path $SkillsSrc)) { Write-Host "No skills/ folder; skipping."; return }
    New-Item -ItemType Directory -Path $CodexSkills -Force | Out-Null
    Get-ChildItem -Path $SkillsSrc -Directory | ForEach-Object {
        $dest = Join-Path $CodexSkills $_.Name
        Write-Host "Deploying skill: $($_.Name) -> $dest"
        if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
        Copy-Item -Path $_.FullName -Destination $dest -Recurse -Force
    }
    Write-Host "Skills installed."
}

# ─── 2. Claude Code Plugins ───────────────────────────────────────────────────
function Update-PluginRegistries {
    param(
        [string]$PluginsDir,
        [string]$MarketplaceName,
        [string]$GitHubRepo,
        [string]$PluginName,
        [string]$Version,
        [string]$InstallPath,
        [string]$GitCommitSha
    )
    $now = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
    $pluginKey = "${PluginName}@${MarketplaceName}"

    # installed_plugins.json
    $ipPath = Join-Path $PluginsDir "installed_plugins.json"
    $ip = if (Test-Path $ipPath) { Get-Content $ipPath -Raw | ConvertFrom-Json } `
          else { [PSCustomObject]@{ version = 2; plugins = [PSCustomObject]@{} } }
    $entry = [PSCustomObject]@{
        scope        = "user"
        installPath  = $InstallPath
        version      = $Version
        installedAt  = $now
        lastUpdated  = $now
        gitCommitSha = $GitCommitSha
    }
    if ($ip.plugins.PSObject.Properties[$pluginKey]) {
        $ip.plugins.PSObject.Properties[$pluginKey].Value = @($entry)
    } else {
        $ip.plugins | Add-Member -MemberType NoteProperty -Name $pluginKey -Value @($entry)
    }
    $ip | ConvertTo-Json -Depth 10 | Set-Content $ipPath -Encoding UTF8

    # known_marketplaces.json
    $kmPath = Join-Path $PluginsDir "known_marketplaces.json"
    $km = if (Test-Path $kmPath) { Get-Content $kmPath -Raw | ConvertFrom-Json } `
          else { [PSCustomObject]@{} }
    $mktEntry = [PSCustomObject]@{
        source          = [PSCustomObject]@{ source = "github"; repo = $GitHubRepo }
        installLocation = Join-Path $PluginsDir "marketplaces\$MarketplaceName"
        lastUpdated     = $now
    }
    if ($km.PSObject.Properties[$MarketplaceName]) {
        $km.PSObject.Properties[$MarketplaceName].Value = $mktEntry
    } else {
        $km | Add-Member -MemberType NoteProperty -Name $MarketplaceName -Value $mktEntry
    }
    $km | ConvertTo-Json -Depth 10 | Set-Content $kmPath -Encoding UTF8
    Write-Host "  Registry updated."
}

function Install-BkitPlugin {
    $marketplace = "bkit-marketplace"
    $repo        = "popup-studio-ai/bkit-claude-code"
    $pluginName  = "bkit"
    $PluginsDir  = Join-Path $env:USERPROFILE ".claude\plugins"
    $CacheDir    = Join-Path $PluginsDir "cache\$marketplace\$pluginName"
    $TempDir     = Join-Path $env:TEMP "cc-plugin-bkit"

    Write-Host "`nInstalling bkit plugin..."
    if (Test-Path $TempDir) { Remove-Item $TempDir -Recurse -Force }
    & git clone --depth 1 "https://github.com/$repo" $TempDir --quiet 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "git clone failed for $repo" }

    $sha     = (& git -C $TempDir rev-parse HEAD).Trim()
    $cfgPath = Join-Path $TempDir "bkit.config.json"
    $version = if (Test-Path $cfgPath) {
        (Get-Content $cfgPath -Raw | ConvertFrom-Json).version
    } else { $sha.Substring(0, 12) }

    $installPath = Join-Path $CacheDir $version
    if (Test-Path $installPath) {
        Write-Host "  bkit $version already installed — skipping."
        Remove-Item $TempDir -Recurse -Force
    } else {
        New-Item -ItemType Directory -Path $installPath -Force | Out-Null
        Get-ChildItem $TempDir -Force | Copy-Item -Destination $installPath -Recurse -Force
        Remove-Item $TempDir -Recurse -Force
        Write-Host "  Installed bkit $version -> $installPath"
    }

    Update-PluginRegistries `
        -PluginsDir      $PluginsDir `
        -MarketplaceName $marketplace `
        -GitHubRepo      $repo `
        -PluginName      $pluginName `
        -Version         $version `
        -InstallPath     $installPath `
        -GitCommitSha    $sha
}

function Install-PlaywrightPlugin {
    $marketplace = "claude-plugins-official"
    $repo        = "anthropics/claude-plugins-official"
    $pluginName  = "playwright"
    $PluginsDir  = Join-Path $env:USERPROFILE ".claude\plugins"
    $CacheDir    = Join-Path $PluginsDir "cache\$marketplace\$pluginName"

    Write-Host "`nInstalling playwright plugin..."
    $sha     = ((& git ls-remote "https://github.com/$repo" HEAD) -split "\s+")[0].Trim()
    $version = $sha.Substring(0, 12)
    $installPath = Join-Path $CacheDir $version

    if (Test-Path (Join-Path $installPath ".mcp.json")) {
        Write-Host "  playwright $version already installed — skipping."
    } else {
        New-Item -ItemType Directory -Path $installPath -Force | Out-Null
        @{ playwright = @{ command = "npx"; args = @("@playwright/mcp@latest") } } |
            ConvertTo-Json -Depth 5 | Set-Content (Join-Path $installPath ".mcp.json") -Encoding UTF8
        New-Item -ItemType File -Path (Join-Path $installPath ".claude-plugin") -Force | Out-Null
        Write-Host "  Installed playwright $version -> $installPath"
    }

    Update-PluginRegistries `
        -PluginsDir      $PluginsDir `
        -MarketplaceName $marketplace `
        -GitHubRepo      $repo `
        -PluginName      $pluginName `
        -Version         $version `
        -InstallPath     $installPath `
        -GitCommitSha    $sha
}

# ─── Main ─────────────────────────────────────────────────────────────────────
Write-Host "=== my-tools setup ===" -ForegroundColor Cyan
Install-CodexSkills
New-Item -ItemType Directory -Path (Join-Path $env:USERPROFILE ".claude\plugins\cache") -Force | Out-Null
Install-BkitPlugin
Install-PlaywrightPlugin
Write-Host "`nDone! Restart Claude Code to activate plugins." -ForegroundColor Green
