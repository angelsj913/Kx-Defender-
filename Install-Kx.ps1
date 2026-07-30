#requires -Version 5.1
<#
.SYNOPSIS
  Launch Kx-Defender from PowerShell (short any-PC entry).

.EXAMPLE
  npx -y --prefer-online angelsj913/Kx-Defender-

.EXAMPLE
  irm https://raw.githubusercontent.com/angelsj913/Kx-Defender-/main/Install-Kx.ps1 | iex

.EXAMPLE
  .\Install-Kx.ps1 -All -Global
#>
[CmdletBinding()]
param(
    [switch]$All,
    [Alias("g")]
    [switch]$Global,
    [switch]$NoServe,
    [string]$Bind = "127.0.0.1:8787",
    [switch]$SkillsOnly
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
  DEFENDER  ·  Self-Built Only
────────────────────────────────────────

"@
    Write-Host $banner -ForegroundColor Cyan
}

Show-KxBanner

# Prefer local repo launcher when present; otherwise npx from GitHub
$repoRoot = $null
if ($PSScriptRoot -and (Test-Path (Join-Path $PSScriptRoot "package.json"))) {
    $repoRoot = $PSScriptRoot
} elseif ($PSScriptRoot) {
    $parent = Split-Path -Parent $PSScriptRoot
    if (Test-Path (Join-Path $parent "package.json")) { $repoRoot = $parent }
}

$npxArgs = @("-y", "--prefer-online", "angelsj913/Kx-Defender-")
if ($SkillsOnly) {
    $npxArgs += @("add", "--all", "-g")
} else {
    if ($All) { $npxArgs += "--all" }
    if ($Global) { $npxArgs += "-g" }
    if ($NoServe) { $npxArgs += "--no-serve" }
    if ($Bind -and $Bind -ne "127.0.0.1:8787") { $npxArgs += @("--bind", $Bind) }
}

if ($repoRoot -and (Test-Path (Join-Path $repoRoot "scripts\npx-entry.js"))) {
    Write-Host "[Kx] Local launch: $repoRoot" -ForegroundColor DarkCyan
    $nodeArgs = @()
    if ($SkillsOnly) { $nodeArgs += @("add", "--all", "-g") }
    else {
        if ($All) { $nodeArgs += "--all" }
        if ($Global) { $nodeArgs += "-g" }
        if ($NoServe) { $nodeArgs += "--no-serve" }
        if ($Bind -and $Bind -ne "127.0.0.1:8787") { $nodeArgs += @("--bind", $Bind) }
    }
    & node (Join-Path $repoRoot "scripts\npx-entry.js") @nodeArgs
    exit $LASTEXITCODE
}

Write-Host "[Kx] PowerShell → npx $($npxArgs -join ' ')" -ForegroundColor DarkCyan
& npx @npxArgs
exit $LASTEXITCODE
