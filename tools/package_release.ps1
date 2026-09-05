<#!
.SYNOPSIS
Creates a GitHub Release ZIP containing the verified Windows EXE and its notices.

.DESCRIPTION
Run after a successful PyInstaller build. The script never changes source files,
never creates a Git commit, and writes only into the ignored release/ directory.
#>
[CmdletBinding()]
param(
    [string]$Version = "1.0.1",
    [string]$ExecutablePath = "dist\\POICollector.exe"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$exe = Join-Path $repoRoot $ExecutablePath

if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
    throw "Executable not found: $exe`nBuild it first: venv\\Scripts\\pyinstaller.exe POICollector.spec --noconfirm"
}

$releaseRoot = Join-Path $repoRoot "release"
$packageName = "POICollector-v$Version-windows-x64"
$stage = Join-Path $releaseRoot $packageName
$zip = Join-Path $releaseRoot "$packageName.zip"
$releaseNotes = Join-Path $repoRoot "docs\releases\RELEASE_NOTES_v$Version.md"

if (-not (Test-Path -LiteralPath $releaseNotes -PathType Leaf)) {
    throw "Release notes not found: $releaseNotes"
}

if (Test-Path -LiteralPath $stage) {
    Remove-Item -LiteralPath $stage -Recurse -Force
}
if (Test-Path -LiteralPath $zip) {
    Remove-Item -LiteralPath $zip -Force
}

New-Item -ItemType Directory -Path $stage | Out-Null
Copy-Item -LiteralPath $exe -Destination (Join-Path $stage "POICollector.exe")
Copy-Item -LiteralPath (Join-Path $repoRoot "LICENSE") -Destination $stage
Copy-Item -LiteralPath (Join-Path $repoRoot "README.md") -Destination $stage
Copy-Item -LiteralPath (Join-Path $repoRoot "README_EN.md") -Destination $stage
Copy-Item -LiteralPath $releaseNotes -Destination $stage
Copy-Item -LiteralPath (Join-Path $repoRoot "LICENSES") -Destination (Join-Path $stage "LICENSES") -Recurse

$hash = (Get-FileHash -LiteralPath (Join-Path $stage "POICollector.exe") -Algorithm SHA256).Hash
Set-Content -LiteralPath (Join-Path $stage "SHA256SUMS.txt") -Encoding ascii -Value "$hash  POICollector.exe"
Compress-Archive -LiteralPath $stage -DestinationPath $zip -CompressionLevel Optimal

Write-Host "Release archive: $zip"
Write-Host "SHA-256: $hash"
