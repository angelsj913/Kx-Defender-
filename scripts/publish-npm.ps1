# Publish kx-defender to https://registry.npmjs.org (fixes npx E404)
# Run once from the repo root after creating an npm account.
#
#   npm login
#   .\scripts\publish-npm.ps1
#
# Then:
#   npx --yes kx-defender add --all -g

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "Checking npm login..."
npm whoami
if ($LASTEXITCODE -ne 0) {
  Write-Host "Not logged in. Run: npm login"
  exit 1
}

Write-Host "Publishing kx-defender..."
npm publish --access public
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Published. Install with:"
Write-Host "  npx --yes kx-defender add --all -g"
