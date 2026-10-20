# Windows PowerShell bootstrap script for AI Voice Sales Bot

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Starting AI Voice Sales Bot (Sankar Group Assignment)    " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Locate Python
$PYTHON = "C:\Users\mksin\AppData\Local\Programs\Python\Python312\python.exe"
if (-not (Test-Path $PYTHON)) {
    $PYTHON = "python"
}

# Ensure data directories exist
New-Item -ItemType Directory -Force -Path "data\recordings" | Out-Null

# Clear stale process holding port 8000 if present
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

# Clear any orphaned sales agent workers
Get-CimInstance Win32_Process -Filter "name = 'python.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*app.agent*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

Write-Host "1. Starting LiveKit Realtime Agent Worker..." -ForegroundColor Green
$agentProcess = Start-Process -FilePath $PYTHON -ArgumentList "-m", "app.agent", "start" -PassThru

Write-Host "2. Starting FastAPI Application Server on http://127.0.0.1:8000..." -ForegroundColor Green
try {
    & $PYTHON -m uvicorn app.server:app --host 127.0.0.1 --port 8000
}
finally {
    if ($agentProcess -and -not $agentProcess.HasExited) {
        Write-Host "Stopping LiveKit Agent Worker..." -ForegroundColor Yellow
        Stop-Process -Id $agentProcess.Id -Force -ErrorAction SilentlyContinue
    }
}
