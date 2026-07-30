# Kx-Defender Clean Script - Remove local cache and data only

param([switch]$Force)

$kxHome = Join-Path $HOME ".kx-defender"
$projectUa = ".ua"

if (-not $Force) {
    Write-Host "제거될 항목:"
    Write-Host "  • ~/.kx-defender"
    Write-Host "  • .ua/"
    Write-Host ""
    $confirm = Read-Host "계속하시겠습니까? (yes/no)"
    if ($confirm -ne "yes") { exit 0 }
}

Write-Host "제거 중..."
if (Test-Path $kxHome) {
    Remove-Item -Path $kxHome -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "✓ $kxHome 제거됨"
}

if (Test-Path $projectUa) {
    Remove-Item -Path $projectUa -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "✓ $projectUa 제거됨"
}

Write-Host "완료!"
