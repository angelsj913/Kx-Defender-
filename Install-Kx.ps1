#requires -Version 5.1
<#
.SYNOPSIS
  Launch Kx DEFCOM native Operator Client inside PowerShell.

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
    [switch]$Classic,
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

  _  __
 | |/ /__  __
 | ' </\ \/ /
 |_|\_\\_/\_\
  DEFCOM OPERATOR CLIENT
----------------------------------------

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
        # Bare `kx` starts the program (HUD)
        Invoke-KxNode
        return
    }
    # kx update → updater
    if ($CommandArgs.Count -ge 1 -and ($CommandArgs[0] -eq "update" -or $CommandArgs[0] -eq "upgrade")) {
        Invoke-KxNode update
        return
    }
    # kx login → re-enter HUD
    if ($CommandArgs.Count -ge 1 -and $CommandArgs[0] -eq "login") {
        Invoke-KxNode login kx
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
    if ($Target -match 'kx' -or $Target -eq "" -or $null -eq $Target) {
        Write-Host "[Kx] entering..." -ForegroundColor DarkCyan
        Invoke-KxNode
        return
    }
    # Any remaining args that mention kx
    $joined = (@($Target) + @($Rest)) -join " "
    if ($joined -match 'kx') {
        Invoke-KxNode
        return
    }
    Write-Host "[Kx] include kx in the command to enter" -ForegroundColor Yellow
}

# Allow typing: [login kx]  (PowerShell parses [login as a command name in some hosts)
Set-Item -Path "function:global:[login" -Value {
    param([Parameter(ValueFromRemainingArguments = $true)]$Rest)
    Invoke-KxNode
} -Force -ErrorAction SilentlyContinue

function global:Update-Kx {
    Write-Host "[Kx] Updating (no full reinstall)..." -ForegroundColor DarkCyan
    Invoke-KxNode update
}

Set-Alias -Name update -Value Update-Kx -Scope Global -Force -ErrorAction SilentlyContinue

function Test-KxEntryLine {
    param([string]$Line)
    # Any input containing "kx" enters the program (except exit)
    return ($Line -match 'kx')
}

function Enter-KxLoginLoop {
    Write-Host ""
    Write-Host "[Kx] Session ended. Type anything with kx to re-enter, update, or exit." -ForegroundColor DarkCyan
    while ($true) {
        Write-Host -NoNewline "kx> "
        $line = Read-Host
        if ($null -eq $line) { break }
        $t = $line.Trim()
        if ($t -match '^(exit|quit|q)$') { break }
        if ($t -match '^(update|upgrade)$' -or $t -match '(?i)kx\s+update') {
            Update-Kx
            continue
        }
        if (Test-KxEntryLine $t) {
            Invoke-KxNode
            Write-Host "[Kx] Session ended. Type anything with kx to re-enter, or exit." -ForegroundColor DarkCyan
            continue
        }
        Write-Host "  include kx to enter  |  update  |  exit" -ForegroundColor Yellow
    }
}

# Any unknown PowerShell command whose name contains "kx" launches the program
$ExecutionContext.InvokeCommand.CommandNotFoundAction = {
    param($CommandName, $CommandLookupEventArgs)
    if ($CommandName -match 'kx') {
        Invoke-KxNode
        $CommandLookupEventArgs.CommandScriptBlock = { }
        $CommandLookupEventArgs.StopSearch = $true
    }
}

Enable-KxConsoleTheme
Show-KxBanner

# UTF-8 console so Korean KxLang messages do not mojibake
try {
    chcp 65001 | Out-Null
    $OutputEncoding = [System.Text.UTF8Encoding]::new($false)
    [Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
    [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
    $env:PYTHONUTF8 = "1"
    $env:PYTHONIOENCODING = "utf-8"
} catch { }

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

Write-Host "[Kx] Native operator client  ·  Ctrl+C → type kx to resume  ·  update" -ForegroundColor DarkCyan
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

Write-Host "[Kx] Native operator client launching..." -ForegroundColor DarkCyan
Write-Host ""

Invoke-KxNode @launchArgs

# After HUD exits (Ctrl+C kill / exit), offer [login kx] re-entry without reinstall
Enter-KxLoginLoop
exit 0
