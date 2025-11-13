# PowerShell script to restart backend and run tests
Write-Host "=" -NoNewline; for($i=0; $i -lt 79; $i++){Write-Host "=" -NoNewline}; Write-Host ""
Write-Host "Restarting Backend and Running Tests"
Write-Host "=" -NoNewline; for($i=0; $i -lt 79; $i++){Write-Host "=" -NoNewline}; Write-Host ""

# Step 1: Stop existing backend
Write-Host "`n[Step 1] Stopping existing backend..."
$port8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($port8000) {
    $pid = $port8000.OwningProcess
    Write-Host "  Found process $pid on port 8000"
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    Write-Host "  Process stopped"
    Start-Sleep -Seconds 2
} else {
    Write-Host "  No process found on port 8000"
}

# Step 2: Start new backend in background
Write-Host "`n[Step 2] Starting new backend..."
$backendPath = "web\backend\api_gateway"
$startInfo = New-Object System.Diagnostics.ProcessStartInfo
$startInfo.FileName = "uvicorn"
$startInfo.Arguments = "main:app --host 0.0.0.0 --port 8000 --reload"
$startInfo.WorkingDirectory = $backendPath
$startInfo.UseShellExecute = $false
$startInfo.CreateNoWindow = $true

try {
    $process = [System.Diagnostics.Process]::Start($startInfo)
    Write-Host "  Backend started (PID: $($process.Id))"
    Write-Host "  Waiting 10 seconds for backend to initialize..."
    Start-Sleep -Seconds 10
} catch {
    Write-Host "  ERROR: Failed to start backend: $_"
    exit 1
}

# Step 3: Test backend health
Write-Host "`n[Step 3] Testing backend health..."
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "  [OK] Backend is healthy"
        $json = $response.Content | ConvertFrom-Json
        Write-Host "  Service: $($json.service)"
    } else {
        Write-Host "  [ERROR] Backend returned status $($response.StatusCode)"
    }
} catch {
    Write-Host "  [ERROR] Backend health check failed: $_"
}

# Step 4: Run simulation tests
Write-Host "`n[Step 4] Running simulation tests..."
Write-Host "  Executing: python continue_simulation_tests.py"
Write-Host ""
python continue_simulation_tests.py

Write-Host "`n" 
Write-Host "=" -NoNewline; for($i=0; $i -lt 79; $i++){Write-Host "=" -NoNewline}; Write-Host ""
Write-Host "Test execution complete!"
Write-Host "=" -NoNewline; for($i=0; $i -lt 79; $i++){Write-Host "=" -NoNewline}; Write-Host ""







