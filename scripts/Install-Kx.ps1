# Thin wrapper so both .\Install-Kx.ps1 and .\scripts\Install-Kx.ps1 work.
$root = Split-Path -Parent $PSScriptRoot
& (Join-Path $root "Install-Kx.ps1") @args
