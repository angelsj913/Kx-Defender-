#!/usr/bin/env pwsh
# kx-Defender ← → Maltego 양방향 동기화

param([string]$MaltegoInstall = "$env:LOCALAPPDATA")

$transforms = "$MaltegoInstall\Maltego\Maltego Files\local\transforms"
$script_dir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "[INFO] Checking Maltego..." -ForegroundColor Cyan
if (-not (Test-Path $transforms)) {
    Write-Host "[WARN] Creating: $transforms" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $transforms -Force | Out-Null
}

Write-Host "[INFO] Installing Transform files..." -ForegroundColor Cyan
@(
    "kx_maltego_transform.py",
    "kx_command_mapping.csv",
    "kx_maltego_graph.mmd"
) | ForEach-Object {
    if (Test-Path "$script_dir\$_") {
        Copy-Item "$script_dir\$_" "$transforms\$_" -Force
        Write-Host "[OK] $_" -ForegroundColor Green
    }
}

Write-Host "[INFO] Creating configuration..." -ForegroundColor Cyan
@{
    "version" = "1.0"
    "transforms" = 27
    "entities" = @("KxCommand", "KxExecution", "KxThreat", "KxFinding", "KxAlert", "KxProcess", "KxNetwork")
} | ConvertTo-Json | Out-File "$transforms\kx_maltego_config.json" -Encoding UTF8

Write-Host "[OK] Configuration saved" -ForegroundColor Green
Write-Host "[INFO] Entity definitions registered" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next: Restart Maltego → Manage Transforms → Local Transforms" -ForegroundColor Yellow
Write-Host "Path: $transforms" -ForegroundColor Gray
