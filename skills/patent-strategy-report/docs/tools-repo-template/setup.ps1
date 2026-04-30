# 도구 통합 레포에서 실행: skills/ 내용을 Codex 스킬 디렉터리로 복사
$ErrorActionPreference = "Stop"
$RepoRoot = $PSScriptRoot
$CodexSkills = if ($env:CODEX_HOME) { Join-Path $env:CODEX_HOME "skills" } else { Join-Path $env:USERPROFILE ".codex\skills" }

if (-not (Test-Path $CodexSkills)) { New-Item -ItemType Directory -Path $CodexSkills -Force | Out-Null }

$SkillsSrc = Join-Path $RepoRoot "skills"
if (-not (Test-Path $SkillsSrc)) { Write-Host "No skills/ folder found."; exit 1 }

Get-ChildItem -Path $SkillsSrc -Directory | ForEach-Object {
    $dest = Join-Path $CodexSkills $_.Name
    Write-Host "Deploying skill: $($_.Name) -> $dest"
    if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
    Copy-Item -Path $_.FullName -Destination $dest -Recurse -Force
}
Write-Host "Done. Restart Codex to load skills."
