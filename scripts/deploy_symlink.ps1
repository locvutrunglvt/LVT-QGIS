# deploy_symlink.ps1
# ============================================================
# LVT Plugin — Development Symlink Setup
#
# Creates a symbolic link from the QGIS plugins directory
# to the source code directory, enabling live-edit workflow.
#
# USAGE (Run as Administrator):
#   .\deploy_symlink.ps1
#
# Author: Lộc Vũ Trung (LVT) / Slow Forest
# ============================================================

$SourceDir = "c:\Users\User\OneDrive\QGIS_Plugin\LVT"
$PluginsDir = "$env:APPDATA\QGIS\QGIS3\profiles\default\python\plugins"
$LinkPath = "$PluginsDir\LVT"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  LVT Plugin — Symlink Dev Mode Setup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check source exists
if (-not (Test-Path $SourceDir)) {
    Write-Host "[ERROR] Source directory not found: $SourceDir" -ForegroundColor Red
    exit 1
}

# Check plugins directory exists
if (-not (Test-Path $PluginsDir)) {
    Write-Host "[INFO] Creating plugins directory: $PluginsDir" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $PluginsDir -Force | Out-Null
}

# Remove existing LVT (folder or symlink)
if (Test-Path $LinkPath) {
    $item = Get-Item $LinkPath -Force
    if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        Write-Host "[INFO] Removing existing symlink: $LinkPath" -ForegroundColor Yellow
        (Get-Item $LinkPath).Delete()
    } else {
        Write-Host "[WARNING] Removing existing folder: $LinkPath" -ForegroundColor Yellow
        Remove-Item $LinkPath -Recurse -Force
    }
}

# Create symlink
try {
    New-Item -ItemType SymbolicLink -Path $LinkPath -Target $SourceDir | Out-Null
    Write-Host ""
    Write-Host "[SUCCESS] Symlink created!" -ForegroundColor Green
    Write-Host "  Link:   $LinkPath" -ForegroundColor White
    Write-Host "  Target: $SourceDir" -ForegroundColor White
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Open QGIS" -ForegroundColor White
    Write-Host "  2. Install 'Plugin Reloader' from Plugin Manager" -ForegroundColor White
    Write-Host "  3. Enable 'LVT' in Plugin Manager" -ForegroundColor White
    Write-Host "  4. Edit code -> Press 'Reload Plugin' -> Test!" -ForegroundColor White
}
catch {
    Write-Host ""
    Write-Host "[ERROR] Failed to create symlink. Run PowerShell as Administrator!" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Red
}
