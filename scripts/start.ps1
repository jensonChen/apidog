$Root = "F:\ApiWorkbench"
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"
$Pip = Join-Path $Backend ".venv\Scripts\pip.exe"
$HealthUrl = "http://127.0.0.1:19527/api/health"
$AppUrl = "http://127.0.0.1:19527"

function Show-Error([string]$Message) {
    Add-Type -AssemblyName System.Windows.Forms
    [void][System.Windows.Forms.MessageBox]::Show($Message, "ApiWorkbench")
}

function Stop-Port([int]$Port) {
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}

if (-not (Test-Path $Root)) {
    Show-Error "Path not found: F:\ApiWorkbench"
    exit 1
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Show-Error "Python not found. Install Python 3.10+ first."
    exit 1
}

Stop-Port 19527
Stop-Port 5173

if (-not (Test-Path (Join-Path $Backend ".venv"))) {
    python -m venv (Join-Path $Backend ".venv")
}

& $Pip install -r (Join-Path $Backend "requirements.txt") -q | Out-Null

$DistIndex = Join-Path $Frontend "dist\index.html"
if (-not (Test-Path $DistIndex)) {
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        Show-Error "npm not found. Cannot build frontend."
        exit 1
    }
    Push-Location $Frontend
    if (-not (Test-Path "node_modules")) {
        npm install | Out-Null
    }
    npm run build | Out-Null
    Pop-Location
}

Start-Process -WindowStyle Hidden -WorkingDirectory $Backend -FilePath $Python -ArgumentList "main.py"

$ready = $false
for ($i = 0; $i -lt 25; $i++) {
    Start-Sleep -Seconds 1
    try {
        $resp = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) {
            $ready = $true
            break
        }
    }
    catch {
        continue
    }
}

if (-not $ready) {
    Show-Error "Backend failed to start. Run F:\ApiWorkbench\stop.bat and retry."
    exit 1
}

Start-Process $AppUrl
exit 0
