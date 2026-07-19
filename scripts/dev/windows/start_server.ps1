param(
    [ValidateSet("interactive", "shared", "trusted_lan")]
    [string]$AuthMode = "interactive",
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8000,
    [string]$QdrantDirectory = ""
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
if (-not $QdrantDirectory) {
    $QdrantDirectory = Join-Path $root "qdrant"
}
$qdrantDirectoryPath = (Resolve-Path $QdrantDirectory).Path
$qdrantBinary = Join-Path $qdrantDirectoryPath "qdrant.exe"
$qdrantConfig = Join-Path $root "packaging\qdrant\production.yaml"
$qdrantStorage = Join-Path $qdrantDirectoryPath "storage"

if (-not (Test-Path -LiteralPath $qdrantBinary -PathType Leaf)) {
    throw "Qdrant executable not found: $qdrantBinary"
}
if (-not (Test-Path -LiteralPath $qdrantConfig -PathType Leaf)) {
    throw "Qdrant configuration not found: $qdrantConfig"
}

$pythonCandidates = @(
    (Join-Path $root ".venv\Scripts\python.exe"),
    (Join-Path $root "venv_win\Scripts\python.exe")
)
$python = $pythonCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if (-not $python) {
    throw "No project Python environment found. Create .venv before starting the server."
}

$env:APP_MODE = "SERVER"
$env:AUTH_MODE = $AuthMode
$env:QDRANT_MODE = "bundled"
$env:QDRANT_URL = "http://127.0.0.1:6333"
$env:BUNDLED_QDRANT_BINARY = $qdrantBinary
$env:BUNDLED_QDRANT_CONFIG_PATH = $qdrantConfig
$env:BUNDLED_QDRANT_STORAGE_DIR = $qdrantStorage

Push-Location $root
try {
    & $python "scripts\dev\preflight.py"
    if ($LASTEXITCODE -ne 0) {
        throw "Lumeward preflight failed. Resolve the reported checks before startup."
    }
    & $python -m backend.main --mode server --auth-mode $AuthMode --host $HostAddress --port $Port
    if ($LASTEXITCODE -ne 0) {
        throw "Lumeward server exited with code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
