#requires -Version 5.1
<#
.SYNOPSIS
  Launch Kx-Defender CLI inside PowerShell (no web server by default).

.EXAMPLE
  npx -y --prefer-online angelsj913/Kx-Defender-

.EXAMPLE
  irm https://raw.githubusercontent.com/angelsj913/Kx-Defender-/main/Install-Kx.ps1 | iex

.EXAMPLE
  .\Install-Kx.ps1 -Fresh
  .\Install-Kx.ps1 -Serve
#>
[CmdletBinding()]
param(
    [switch]$All,
    [Alias("g")]
    [switch]$Global,
    [switch]$Serve,
    [string]$Bind = "127.0.0.1:8787",
    [switch]$SkillsOnly,
    [switch]$Fresh
)

$ErrorActionPreference = "Stop"

function Show-KxBanner {
    $banner = @"

██╗  ██╗██╗  ██╗
██║ ██╔╝╚██╗██╔╝
█████╔╝  ╚███╔╝
██╔═██╗  ██╔██╗
██║  ██╗██╔╝ ██╗
╚═╝  ╚═╝╚═╝  ╚═╝
  DEFENDER  ·  CLI Shell (no server)
────────────────────────────────────────

"@
    Write-Host $banner -ForegroundColor Cyan
}

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

# Session helper: kx <args...> from this PowerShell
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
if ($Serve) {
    $launchArgs += "--serve"
    if ($Bind) { $launchArgs += @("--bind", $Bind) }
}

Write-Host "[Kx] PowerShell CLI ready. After launch, type commands at Kx> prompt." -ForegroundColor DarkCyan
Write-Host "[Kx] Examples: /h   |   roast tickets --scope lab --sim   |   exit" -ForegroundColor DarkCyan
Write-Host ""

if ($repoRoot -and (Test-Path (Join-Path $repoRoot "scripts\npx-entry.js"))) {
    Write-Host "[Kx] Local launch: $repoRoot" -ForegroundColor DarkCyan
    & node (Join-Path $repoRoot "scripts\npx-entry.js") @launchArgs
    exit $LASTEXITCODE
}

& npx -y --prefer-online angelsj913/Kx-Defender- @launchArgs
exit $LASTEXITCODE
