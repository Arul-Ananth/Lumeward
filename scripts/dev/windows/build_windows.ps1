# Lumeward Beta 1.0 Windows Build Script
Write-Host "Starting Lumeward Windows build..."

# Activate Venv
$d = ".\venv_win\Scripts\activate.ps1"
if (Test-Path $d) {
    . $d
}
else {
    Write-Host "Error: venv_win not found."
    exit 1
}

Write-Host "Running PyInstaller from tracked spec..."
pyinstaller --noconfirm packaging\pyinstaller\Lumeward.spec

if ($LASTEXITCODE -eq 0) {
    Write-Host "Folder build successful: dist\Lumeward\Lumeward.exe"
}
else {
    Write-Host "Build Failed."
    exit $LASTEXITCODE
}

$iscc = Get-Command iscc -ErrorAction SilentlyContinue
if ($iscc) {
    Write-Host "Inno Setup detected. Building installer..."
    iscc packaging\installers\windows\Lumeward.iss
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installer build failed."
        exit $LASTEXITCODE
    }
    Write-Host "Installer build complete."
}
else {
    Write-Host "Inno Setup not found. Skipping installer; folder build is ready."
}
