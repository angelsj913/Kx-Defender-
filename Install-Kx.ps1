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
    [switch]$Fresh,
    [switch]$Update,
    [switch]$LoginOnly
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

function Get-KxRepoRoot {
    if ($PSScriptRoot -and (Test-Path (Join-Path $PSScriptRoot "package.json"))) {
        return $PSScriptRoot
    }
    if ($PSScriptRoot) {
        $parent = Split-Path -Parent $PSScriptRoot
        if (Test-Path (Join-Path $parent "package.json")) { return $parent }
    }
    $app = Join-Path $env:USERPROFILE ".kx-defender\app"
    if (Test-Path (Join-Path $app "package.json")) { return $app }
    return $null
}

function Invoke-KxNode {
    param([Parameter(ValueFromRemainingArguments = $true)]$NodeArgs)
    $repoRoot = Get-KxRepoRoot
    $binDir = Join-Path $env:LOCALAPPDATA "Kx-Defender\bin"
    if (Test-Path -LiteralPath $binDir) {
        $env:PATH = "$binDir;$env:PATH"
    }
    if ($repoRoot -and (Test-Path (Join-Path $repoRoot "scripts\npx-entry.js"))) {
        & node (Join-Path $repoRoot "scripts\npx-entry.js") @NodeArgs
        return $LASTEXITCODE
    }
    & npx -y --prefer-online angelsj913/Kx-Defender- @NodeArgs
    return $LASTEXITCODE
}

function global:kx {
    param([Parameter(ValueFromRemainingArguments = $true)]$CommandArgs)
    if (-not $CommandArgs -or $CommandArgs.Count -eq 0) {
        Invoke-KxNode kx /h
        return
    }
    # kx update → updater
    if ($CommandArgs.Count -ge 1 -and ($CommandArgs[0] -eq "update" -or $CommandArgs[0] -eq "upgrade")) {
        Invoke-KxNode update
        return
    }
    Invoke-KxNode kx @CommandArgs
}

function global:login {
    param(
        [Parameter(Position = 0)]
        [string]$Target = "kx",
        [Parameter(ValueFromRemainingArguments = $true)]$Rest
    )
    if ($Target -match '^(kx|\[kx\]|kx\])$' -or $Target -eq "" -or $null -eq $Target) {
        Write-Host "[Kx] login kx — re-entering HUD..." -ForegroundColor DarkCyan
        Invoke-KxNode login kx
        return
    }
    Write-Host "[Kx] use: login kx   or   [login kx]" -ForegroundColor Yellow
}

# Allow typing: [login kx]  (PowerShell parses [login as a command name in some hosts)
Set-Item -Path "function:global:[login" -Value {
    param([Parameter(ValueFromRemainingArguments = $true)]$Rest)
    $joined = (@($Rest) -join " ").Trim()
    if ($joined -match '^kx\]?$' -or $joined -eq "" -or $joined -match '^kx') {
        login kx
        return
    }
    Write-Host "[Kx] use: [login kx]" -ForegroundColor Yellow
} -Force -ErrorAction SilentlyContinue

function global:Update-Kx {
    Write-Host "[Kx] Updating (no full reinstall)..." -ForegroundColor DarkCyan
    Invoke-KxNode update
}

Set-Alias -Name update -Value Update-Kx -Scope Global -Force -ErrorAction SilentlyContinue

function Test-KxLoginLine {
    param([string]$Line)
    $s = ($Line -replace '[\[\]]', ' ').Trim().ToLower() -replace '\s+', ' '
    return ($s -eq "login kx" -or $s -eq "login-kx" -or $s -eq "loginkx")
}

function Enter-KxLoginLoop {
    Write-Host ""
    Write-Host "[Kx] Session ended. Type [login kx] to re-enter, update to refresh, or exit." -ForegroundColor DarkCyan
    while ($true) {
        Write-Host -NoNewline "[login kx]> "
        $line = Read-Host
        if ($null -eq $line) { break }
        $t = $line.Trim()
        if ($t -match '^(exit|quit|q)$') { break }
        if ($t -match '^(update|upgrade|kx update)$') {
            Update-Kx
            continue
        }
        if (Test-KxLoginLine $t) {
            Invoke-KxNode login kx
            Write-Host "[Kx] Session ended. Type [login kx] to re-enter, or exit." -ForegroundColor DarkCyan
            continue
        }
        Write-Host "  locked out — type [login kx]  |  update  |  exit" -ForegroundColor Yellow
    }
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

$binDir = Join-Path $env:LOCALAPPDATA "Kx-Defender\bin"
if (Test-Path -LiteralPath $binDir) {
    $env:PATH = "$binDir;$env:PATH"
}

Write-Host "[Kx] Tips: Ctrl+C locks HUD → type [login kx]  |  update refreshes without reinstall" -ForegroundColor DarkCyan
Write-Host ""

if ($SkillsOnly) {
    Invoke-KxNode add --all -g
    exit $LASTEXITCODE
}

if ($Update) {
    Update-Kx
    exit $LASTEXITCODE
}

if ($LoginOnly) {
    login kx
    Enter-KxLoginLoop
    exit 0
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
Write-Host ""

Invoke-KxNode @launchArgs

# After HUD exits (Ctrl+C kill / exit), offer [login kx] re-entry without reinstall
Enter-KxLoginLoop
exit 0
