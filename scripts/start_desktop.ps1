# Start ApiDog in desktop window mode (dev, uses %AppData%\ApiDog)
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"
$Pip = Join-Path $Backend ".venv\Scripts\pip.exe"
$FrontendDist = Join-Path $Root "frontend\dist\index.html"

if (-not (Test-Path $Python)) {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        throw "Python not found"
    }
    python -m venv (Join-Path $Backend ".venv")
}

& $Pip install -r (Join-Path $Backend "requirements.txt") -q

if (-not (Test-Path $FrontendDist)) {
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        throw "frontend/dist missing and npm not found"
    }
    Push-Location (Join-Path $Root "frontend")
    if (-not (Test-Path "node_modules")) {
        npm install
    }
    npm run build
    Pop-Location
}

$env:APIDOG_USE_APPDATA = "1"
Push-Location $Backend
& $Python "desktop_launcher.py"
$exitCode = $LASTEXITCODE
Pop-Location
exit $exitCode
