#!/usr/bin/env pwsh
<#
.SYNOPSIS
kx-Defender Maltego Transform 설치 (27개 명령어)

.DESCRIPTION
kx_maltego_transform.py를 Maltego Local Transform으로 등록
Attack(7) + Defense(10) + Infrastructure(4) + Utility(7) = 25개 활성

.EXAMPLE
.\install_maltego_transform.ps1
#>

param([string]$MaltegoPath = "$env:LOCALAPPDATA\Maltego\Maltego Files\local\transforms")

$Green = [System.ConsoleColor]::Green
$Red = [System.ConsoleColor]::Red
$Yellow = [System.ConsoleColor]::Yellow

function Write-Status {
    param([string]$msg, [string]$status = "INFO")
    $color = @{ "OK" = $Green; "ERROR" = $Red; "WARN" = $Yellow }[$status] ?? $Green
    Write-Host "[$status] " -ForegroundColor $color -NoNewline
    Write-Host $msg
}

if (-not (Test-Path $MaltegoPath)) {
    Write-Status "Maltego not found: $MaltegoPath" "ERROR"
    exit 1
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Copy transform
Copy-Item "$scriptDir\kx_maltego_transform.py" "$MaltegoPath\kx_maltego_transform.py" -Force
Write-Status "Copied transform" "OK"

# Copy metadata
Copy-Item "$scriptDir\kx_command_mapping.csv" "$MaltegoPath\kx_command_mapping.csv" -Force
Write-Status "Copied metadata" "OK"

# Create config
@{
    "version" = "1.0"
    "commands" = @(
        "roast", "relay", "loot", "bait", "breach", "crack", "nexus",
        "sentry", "trace", "audit", "harden", "triage", "comply", "forge", "sig", "watch", "kill",
        "graph", "probe", "sweep",
        "lexicon", "lang", "update", "help", "exit"
    )
} | ConvertTo-Json | Out-File "$MaltegoPath\kx_maltego_config.json" -Encoding UTF8
Write-Status "Created config" "OK"

Write-Host ""
Write-Status "Installation Complete!" "OK"
Write-Host "  Path: $MaltegoPath"
Write-Host "  Commands: 25 (all from help)"
Write-Host ""
