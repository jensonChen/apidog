# Build ApiDog desktop onedir (+ optional Inno installer)
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Packaging = Join-Path $Root "packaging"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"
$Pip = Join-Path $Backend ".venv\Scripts\pip.exe"
$DistIndex = Join-Path $Frontend "dist\index.html"
$Spec = Join-Path $Packaging "apidog.spec"
$PyInstallerDist = Join-Path $Packaging "dist\ApiDog"
$Iss = Join-Path $Packaging "inno\ApiDog.iss"

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

if (-not (Test-Path $Python)) {
    Require-Command "python"
    python -m venv (Join-Path $Backend ".venv")
}

& $Pip install -r (Join-Path $Backend "requirements.txt") -q
& $Pip install pyinstaller -q

Require-Command "npm"
Push-Location $Frontend
if (-not (Test-Path "node_modules")) {
    npm install
}
npm run build
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    throw "Frontend build failed"
}
Pop-Location

if (-not (Test-Path $DistIndex)) {
    throw "Frontend dist missing: $DistIndex"
}

Push-Location $Packaging
& $Python -m PyInstaller --noconfirm --clean $Spec
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    throw "PyInstaller failed"
}
Pop-Location

if (-not (Test-Path (Join-Path $PyInstallerDist "ApiDog.exe"))) {
    throw "ApiDog.exe not found under $PyInstallerDist"
}

$AppIco = Join-Path $Root "frontend\public\app.ico"
if (Test-Path $AppIco) {
    Copy-Item -Force $AppIco (Join-Path $PyInstallerDist "app.ico")
}

Write-Host "Desktop onedir ready: $PyInstallerDist"

$Iscc = Get-Command "iscc" -ErrorAction SilentlyContinue
if (-not $Iscc) {
    $defaultIsccPaths = @(
        "C:\Program Files\Inno Setup 7\ISCC.exe",
        "C:\Program Files (x86)\Inno Setup 7\ISCC.exe",
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    )
    foreach ($candidate in $defaultIsccPaths) {
        if (Test-Path $candidate) {
            $Iscc = Get-Item $candidate
            break
        }
    }
}

if ($Iscc) {
    $isccPath = if ($Iscc.Path) { $Iscc.Path } else { $Iscc.FullName }
    & $isccPath $Iss
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup compile failed"
    }
    Write-Host "Installer output: $(Join-Path $Packaging 'output')"
}
else {
    Write-Host "Inno Setup (iscc) not found. Skipped installer. onedir is still usable."
}

Write-Host "Done."
