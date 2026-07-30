#requires -Version 5.1
<#
.SYNOPSIS
  Install and launch Kx-Defender with one PowerShell command (Self-Built Only).

.DESCRIPTION
  - Finds/uses Python 3.9+
  - Creates .venv
  - pip installs this repo (editable)
  - Starts Console (`kx serve`) unless -NoServe

.EXAMPLE
  # From a cloned repo:
  .\Install-Kx.ps1

.EXAMPLE
  # One-liner from the internet (no prior clone):
  irm https://raw.githubusercontent.com/angelsj913/Kx-Defender-/cursor/kx-attack-modules-7992/Install-Kx.ps1 | iex

.EXAMPLE
  .\Install-Kx.ps1 -NoServe
  .\Install-Kx.ps1 -Bind 127.0.0.1:9090
#>
[CmdletBinding()]
param(
    [switch]$NoServe,
    [string]$Bind = "127.0.0.1:8787",
    [string]$RepoUrl = "https://github.com/angelsj913/Kx-Defender-.git",
    [string]$Branch = "cursor/kx-attack-modules-7992",
    [string]$InstallDir = ""
)

$ErrorActionPreference = "Stop"

function Write-Kx([string]$Message, [string]$Color = "Cyan") {
    Write-Host "[Kx] $Message" -ForegroundColor $Color
}

function Test-IsRepoRoot([string]$Path) {
    return (Test-Path (Join-Path $Path "pyproject.toml")) -and (Test-Path (Join-Path $Path "services\orchestrator\kx_defender"))
}

function Find-Python {
    $candidates = @(
        "py -3.12",
        "py -3.11",
        "py -3.10",
        "py -3.9",
        "py -3",
        "python",
        "python3"
    )
    foreach ($c in $candidates) {
        try {
            $parts = $c -split " "
            $exe = $parts[0]
            $argList = @()
            if ($parts.Count -gt 1) { $argList = $parts[1..($parts.Count - 1)] }
            $argList += @("-c", "import sys; assert sys.version_info[:2] >= (3, 9); print(sys.executable)")
            $out = & $exe @argList 2>$null
            if ($LASTEXITCODE -eq 0 -and $out) {
                return $out.Trim()
            }
        } catch {
            continue
        }
    }
    return $null
}

function Get-RepoRoot {
    if ($PSScriptRoot -and (Test-IsRepoRoot $PSScriptRoot)) {
        return $PSScriptRoot
    }
    if ($PSScriptRoot) {
        $parent = Split-Path -Parent $PSScriptRoot
        if (Test-IsRepoRoot $parent) { return $parent }
    }
    if (Test-IsRepoRoot (Get-Location).Path) {
        return (Get-Location).Path
    }
    return $null
}

Write-Kx "Kx-Defender bootstrap (Self-Built Only)"
Write-Kx "Authorized & lawful use only." "Yellow"

$repoRoot = Get-RepoRoot
if (-not $repoRoot) {
    if (-not $InstallDir) {
        $InstallDir = Join-Path $env:USERPROFILE "Kx-Defender"
    }
    Write-Kx "Repo not found locally. Cloning into $InstallDir ..."
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "git is required to clone the repository. Install Git for Windows, or run this script from a cloned repo."
    }
    if (Test-Path $InstallDir) {
        if (-not (Test-IsRepoRoot $InstallDir)) {
            throw "InstallDir exists but is not a Kx-Defender repo: $InstallDir"
        }
        Write-Kx "Using existing checkout: $InstallDir"
    } else {
        git clone --branch $Branch --depth 1 $RepoUrl $InstallDir
        if ($LASTEXITCODE -ne 0) { throw "git clone failed" }
    }
    $repoRoot = $InstallDir
}

Set-Location $repoRoot
Write-Kx "Repo: $repoRoot"

$python = Find-Python
if (-not $python) {
    throw "Python 3.9+ not found. Install from https://www.python.org/downloads/ and ensure 'py' or 'python' is on PATH."
}
Write-Kx "Python: $python"

$venvPath = Join-Path $repoRoot ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Kx "Creating virtualenv .venv ..."
    & $python -m venv $venvPath
    if ($LASTEXITCODE -ne 0) { throw "Failed to create venv" }
}

$venvPython = (Resolve-Path $venvPython).Path
Write-Kx "Upgrading pip / installing Kx-Defender ..."
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }
& $venvPython -m pip install -e ".[dev]"
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

$kxCmd = Join-Path $venvPath "Scripts\kx.exe"
if (-not (Test-Path $kxCmd)) {
    # console_script fallback
    $kxCmd = Join-Path $venvPath "Scripts\kx.exe"
}
if (-not (Test-Path $kxCmd)) {
    throw "kx entry point missing after install. Expected: $kxCmd"
}

# Session PATH helper so `kx` works in this shell
$scriptsDir = Join-Path $venvPath "Scripts"
if ($env:Path -notlike "*$scriptsDir*") {
    $env:Path = "$scriptsDir;" + $env:Path
}

Write-Kx "Install complete." "Green"
Write-Host ""
Write-Host "  Quick commands:" -ForegroundColor DarkCyan
Write-Host "    kx /h"
Write-Host "    kx watch procs --scope lab --live"
Write-Host "    kx roast tickets --scope lab --realm lab.local --sim"
Write-Host ""

if ($NoServe) {
    & $kxCmd /h
    exit $LASTEXITCODE
}

Write-Kx "Starting Console at http://$Bind/  (Ctrl+C to stop)" "Green"
try {
    Start-Process "http://$Bind/"
} catch {
    Write-Kx "Open manually: http://$Bind/" "Yellow"
}
& $kxCmd serve --bind $Bind
