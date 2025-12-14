# Deploy script for EDMC-PlanetPOI plugin
# Copies plugin files to EDMC plugins directory

$ErrorActionPreference = "Stop"

# Source is current directory
$SourceDir = $PSScriptRoot

# Destination is the same folder (we're already in the plugin directory)
$DestDir = "$env:LOCALAPPDATA\EDMarketConnector\plugins\EDMC-PlanetPOI"

Write-Host "EDMC-PlanetPOI Deploy Script" -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Source:      $SourceDir" -ForegroundColor Yellow
Write-Host "Destination: $DestDir" -ForegroundColor Yellow
Write-Host ""

# Check if we're already in the destination directory
if ($SourceDir -eq $DestDir) {
    Write-Host "Already running from plugin directory. No deployment needed." -ForegroundColor Green
    Write-Host ""
    Write-Host "If you're developing from another location, run this script from there." -ForegroundColor Yellow
    exit 0
}

# Create destination if it doesn't exist
if (-not (Test-Path $DestDir)) {
    Write-Host "Creating plugin directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $DestDir -Force | Out-Null
}

# Files to copy
$FilesToCopy = @(
    "load.py",
    "overlay.py",
    "README.md"
)

# Directories to copy
$DirectoriesToCopy = @(
    "L10n",
    "images"
)

# Copy individual files
Write-Host "Copying files..." -ForegroundColor Cyan
foreach ($file in $FilesToCopy) {
    $source = Join-Path $SourceDir $file
    if (Test-Path $source) {
        Write-Host "  - $file" -ForegroundColor Gray
        Copy-Item -Path $source -Destination $DestDir -Force
    } else {
        Write-Host "  - $file (not found, skipping)" -ForegroundColor DarkGray
    }
}

# Copy directories
Write-Host ""
Write-Host "Copying directories..." -ForegroundColor Cyan
foreach ($dir in $DirectoriesToCopy) {
    $source = Join-Path $SourceDir $dir
    if (Test-Path $source) {
        Write-Host "  - $dir\" -ForegroundColor Gray
        $dest = Join-Path $DestDir $dir
        if (Test-Path $dest) {
            Remove-Item -Path $dest -Recurse -Force
        }
        Copy-Item -Path $source -Destination $dest -Recurse -Force
    } else {
        Write-Host "  - $dir\ (not found, skipping)" -ForegroundColor DarkGray
    }
}

# Handle poi.json specially - don't overwrite if it exists
$poiSource = Join-Path $SourceDir "poi.json"
$poiDest = Join-Path $DestDir "poi.json"
Write-Host ""
if (Test-Path $poiDest) {
    Write-Host "poi.json already exists in destination - preserving existing file" -ForegroundColor Yellow
} elseif (Test-Path $poiSource) {
    Write-Host "Copying poi.json..." -ForegroundColor Cyan
    Copy-Item -Path $poiSource -Destination $poiDest -Force
}

Write-Host ""
Write-Host "Deployment complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Note: Restart EDMC to load the updated plugin." -ForegroundColor Yellow
