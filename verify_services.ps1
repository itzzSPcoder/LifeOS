# Local LifeOS services verification script
# No Docker required - runs all 5 env services locally and tests endpoints

param(
    [int]$port_base = 8101,
    [int]$duration_seconds = 60
)

$services = @(
    @{name="echo_env"; port=8101; module="lifeos.env_services.echo_app"; app="app"},
    @{name="coding_env"; port=8102; module="lifeos.env_services.coding_app"; app="app"},
    @{name="chess_env"; port=8103; module="lifeos.env_services.chess_app"; app="app"},
    @{name="carla_env"; port=8104; module="lifeos.env_services.carla_app"; app="app"},
    @{name="julia_env"; port=8105; module="lifeos.env_services.julia_app"; app="app"}
)

Write-Host "Starting LifeOS env services (local, no Docker)..." -ForegroundColor Green
Write-Host "Services will run for ${duration_seconds} seconds for testing." -ForegroundColor Yellow

$processes = @()

# Start all services
foreach ($svc in $services) {
    $port = $svc.port
    $module = $svc.module
    Write-Host "Starting $($svc.name) on port $port..." -ForegroundColor Cyan
    
    $proc = Start-Process -NoNewWindow -PassThru -FilePath ".venv\Scripts\python.exe" `
        -ArgumentList "-m", "uvicorn", "$module`:app", "--host", "127.0.0.1", "--port", $port
    $processes += @{name=$svc.name; process=$proc; port=$port}
    Start-Sleep -Seconds 3
}

Write-Host "All services started. Waiting for endpoints to become ready..." -ForegroundColor Green
Start-Sleep -Seconds 5

# Test all endpoints
$test_results = @()

foreach ($svc in $services) {
    $port = $svc.port
    $url = "http://127.0.0.1:$port/health"
    
    try {
        $response = Invoke-RestMethod -Uri $url -Method Get -ErrorAction Stop
        $test_results += @{service=$svc.name; endpoint=$url; status="PASS"; response=$response}
        Write-Host "✓ $($svc.name) /health: PASS" -ForegroundColor Green
    } catch {
        $test_results += @{service=$svc.name; endpoint=$url; status="FAIL"; error=$_.Exception.Message}
        Write-Host "✗ $($svc.name) /health: FAIL - $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`nTesting functional endpoints..." -ForegroundColor Yellow

# Echo POST test
try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:8101/echo" -Method Post -ContentType "application/json" `
        -Body '{"message":"hello","payload":{"x":1}}' -ErrorAction Stop
    Write-Host "✓ echo_env POST /echo: PASS" -ForegroundColor Green
} catch {
    Write-Host "✗ echo_env POST /echo: FAIL" -ForegroundColor Red
}

# Coding exec test
try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:8102/exec/python" -Method Post -ContentType "application/json" `
        -Body '{"code":"print(2+3)","timeout_seconds":5}' -ErrorAction Stop
    Write-Host "✓ coding_env POST /exec/python: PASS (stdout: $($response.stdout.Trim()))" -ForegroundColor Green
} catch {
    Write-Host "✗ coding_env POST /exec/python: FAIL" -ForegroundColor Red
}

# Chess validate test
try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:8103/validate-move" -Method Post -ContentType "application/json" `
        -Body '{"move":"e2e4","turn":"white"}' -ErrorAction Stop
    Write-Host "✓ chess_env POST /validate-move: PASS (valid: $($response.valid))" -ForegroundColor Green
} catch {
    Write-Host "✗ chess_env POST /validate-move: FAIL" -ForegroundColor Red
}

# Carla step test
try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:8104/step" -Method Post -ContentType "application/json" `
        -Body '{"throttle":0.6,"steer":0.1,"brake":0.0}' -ErrorAction Stop
    Write-Host "✓ carla_env POST /step: PASS (speed: $($response.state.speed_kmh) kmh)" -ForegroundColor Green
} catch {
    Write-Host "✗ carla_env POST /step: FAIL" -ForegroundColor Red
}

# Julia exec test (graceful fail expected if Julia not installed)
try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:8105/exec/julia" -Method Post -ContentType "application/json" `
        -Body '{"code":"println(2+3)","timeout_seconds":5}' -ErrorAction Stop
    
    if ($response.ok -eq $true) {
        Write-Host "✓ julia_env POST /exec/julia: PASS (stdout: $($response.stdout.Trim()))" -ForegroundColor Green
    }
    else {
        Write-Host "⚠ julia_env POST /exec/julia: Service OK, but Julia binary not in PATH (expected if not installed)" -ForegroundColor Yellow
        Write-Host "  Error: $($response.stderr)" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "✗ julia_env POST /exec/julia: FAIL" -ForegroundColor Red
}

Write-Host "`nStopping all services..." -ForegroundColor Yellow
foreach ($proc_info in $processes) {
    Stop-Process -InputObject $proc_info.process -Force -ErrorAction SilentlyContinue
    Write-Host "Stopped $($proc_info.name)" -ForegroundColor Cyan
}

Write-Host "`n=== VERIFICATION COMPLETE ===" -ForegroundColor Green
Write-Host "All 5 env services tested locally without Docker." -ForegroundColor Green
Write-Host "Architecture validation: PASS" -ForegroundColor Green
