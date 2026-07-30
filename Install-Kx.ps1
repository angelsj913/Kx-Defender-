#requires -Version 5.1
<#
.SYNOPSIS
  Launch Kx-Defender eDEX-style HUD inside PowerShell (no web server by default).

.EXAMPLE
  npx -y --prefer-online angelsj913/Kx-Defender-

.EXAMPLE
  irm https://raw.githubusercontent.com/angelsj913/Kx-Defender-/main/Install-Kx.ps1 | iex
#>
[CmdletBinding()]
param(
    [switch]$All,
    [Alias("g")]
    [switch]$Global,
    [switch]$Serve,
    [switch]$Classic,
    [string]$Bind = "127.0.0.1:8787",
    [switch]$SkillsOnly,
    [switch]$Fresh
)

$ErrorActionPreference = "Stop"

function Enable-KxConsoleTheme {
    try {
        $Host.UI.RawUI.BackgroundColor = "Black"
        $Host.UI.RawUI.ForegroundColor = "Cyan"
        Clear-Host
    } catch {
        # Windows Terminal / non-classic hosts may ignore RawUI colors
    }
    # Enable VT sequences on Windows 10+ when possible
    try {
        $null = & cmd /c "echo." 2>$null
    } catch { }
}

function Show-KxBanner {
    $banner = @"

██╗  ██╗██╗  ██╗
██║ ██╔╝╚██╗██╔╝
█████╔╝  ╚███╔╝
██╔═██╗  ██╔██╗
██║  ██╗██╔╝ ██╗
╚═╝  ╚═╝╚═╝  ╚═╝
  DEFENDER  ·  eDEX HUD  ·  TRON LINK
────────────────────────────────────────

"@
    Write-Host $banner -ForegroundColor Cyan
}

Enable-KxConsoleTheme
Show-KxBanner

if ($Fresh) {
    Write-Host "[Kx] Fresh: clearing npx cache / broken portable Python ..." -ForegroundColor DarkCyan
    try { & npx clear-npx-cache 2>$null } catch { }
    $pyHome = Join-Path $env:USERPROFILE ".kx-defender\python"
    if (Test-Path -LiteralPath $pyHome) {
        Remove-Item -LiteralPath $pyHome -Recurse -Force -ErrorAction SilentlyContinue
    }
}

$repoRoot = $null
if ($PSScriptRoot -and (Test-Path (Join-Path $PSScriptRoot "package.json"))) {
    $repoRoot = $PSScriptRoot
} elseif ($PSScriptRoot) {
    $parent = Split-Path -Parent $PSScriptRoot
    if (Test-Path (Join-Path $parent "package.json")) { $repoRoot = $parent }
}

function global:kx {
    param([Parameter(ValueFromRemainingArguments = $true)]$CommandArgs)
    if (-not $CommandArgs -or $CommandArgs.Count -eq 0) {
        & npx -y --prefer-online angelsj913/Kx-Defender- kx /h
        return
    }
    & npx -y --prefer-online angelsj913/Kx-Defender- kx @CommandArgs
}

$binDir = Join-Path $env:LOCALAPPDATA "Kx-Defender\bin"
if (Test-Path -LiteralPath $binDir) {
    $env:PATH = "$binDir;$env:PATH"
}

if ($SkillsOnly) {
    if ($repoRoot -and (Test-Path (Join-Path $repoRoot "scripts\npx-entry.js"))) {
        & node (Join-Path $repoRoot "scripts\npx-entry.js") add --all -g
    } else {
        & npx -y --prefer-online angelsj913/Kx-Defender- add --all -g
    }
    exit $LASTEXITCODE
}

$launchArgs = @()
if ($All) { $launchArgs += "--all" }
if ($Global) { $launchArgs += "-g" }
if ($Classic) { $launchArgs += "--classic" }
if ($Serve) {
    $launchArgs += "--serve"
    if ($Bind) { $launchArgs += @("--bind", $Bind) }
}

Write-Host "[Kx] eDEX HUD launching in this PowerShell window..." -ForegroundColor DarkCyan
Write-Host "[Kx] Commands: /h | lang ko|en | roast tickets --scope lab --sim | exit" -ForegroundColor DarkCyan
Write-Host ""

if ($repoRoot -and (Test-Path (Join-Path $repoRoot "scripts\npx-entry.js"))) {
    Write-Host "[Kx] Local launch: $repoRoot" -ForegroundColor DarkCyan
    & node (Join-Path $repoRoot "scripts\npx-entry.js") @launchArgs
    exit $LASTEXITCODE
}

& npx -y --prefer-online angelsj913/Kx-Defender- @launchArgs
exit $LASTEXITCODE
