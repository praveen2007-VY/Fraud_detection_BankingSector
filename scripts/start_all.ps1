# start_all.ps1
# Unified Startup Orchestrator for Windows PowerShell
# Starts native Kafka, native Neo4j, FastAPI Backend, and React Dashboard

param(
    [switch]$KeepAlive
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Enterprise Fraud Detection System - Unified Startup" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

# Function to test socket port connectivity
function Test-PortOpen($port, $timeoutMs = 1000) {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $iar = $tcp.BeginConnect("127.0.0.1", $port, $null, $null)
        $wait = $iar.AsyncWaitHandle.WaitOne($timeoutMs)
        if ($wait -and $tcp.Connected) {
            $tcp.EndConnect($iar)
            $tcp.Close()
            return $true
        } else {
            $tcp.Close()
            return $false
        }
    } catch {
        return $false
    }
}

# 1. Check & Start Apache Kafka
Write-Host "`n[1/4] Checking Apache Kafka Broker (localhost:9092)..." -ForegroundColor Yellow
if (Test-PortOpen 9092) {
    Write-Host "  [OK] Apache Kafka is already running on port 9092." -ForegroundColor Green
} else {
    Write-Host "  Starting Apache Kafka broker..." -ForegroundColor Yellow
    $javaExe = "C:\Program Files\Eclipse Adoptium\jdk-17.0.20.101-hotspot\bin\java.exe"
    $kfkHome = "C:\kfk"
    $kfkLogs = "C:\kfk-logs"
    if (!(Test-Path $kfkLogs)) { New-Item -ItemType Directory -Path $kfkLogs | Out-Null }
    
    $kafkaArgs = @(
        "-Xmx1G", "-Xms1G",
        "-Dlog4j.configuration=file:$kfkHome/config/log4j.properties",
        "-Dkafka.logs.dir=$kfkLogs",
        "-cp", "$kfkHome\libs\*",
        "kafka.Kafka",
        "$kfkHome\config\kraft\server.properties"
    )

    Start-Process -FilePath $javaExe -ArgumentList $kafkaArgs -WorkingDirectory $kfkHome -WindowStyle Hidden
    
    # Wait for Kafka port readiness
    $ready = $false
    for ($i = 1; $i -le 25; $i++) {
        Start-Sleep -Seconds 1
        if (Test-PortOpen 9092) {
            $ready = $true
            break
        }
    }

    if ($ready) {
        Write-Host "  [OK] Apache Kafka started and listening on port 9092." -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Kafka broker did not open port 9092 within 25s. Check C:\kfk-logs." -ForegroundColor Yellow
    }
}

# 2. Check & Start Neo4j
Write-Host "`n[2/4] Checking Neo4j Graph Database (localhost:7687)..." -ForegroundColor Yellow
if (Test-PortOpen 7687) {
    Write-Host "  [OK] Neo4j is already running on port 7687." -ForegroundColor Green
} else {
    Write-Host "  Starting Neo4j console service..." -ForegroundColor Yellow
    $neo4jBat = "C:\neo4j\bin\neo4j.bat"
    Start-Process -FilePath $neo4jBat -ArgumentList "console" -WorkingDirectory "C:\neo4j" -WindowStyle Hidden
    
    $ready = $false
    for ($i = 1; $i -le 30; $i++) {
        Start-Sleep -Seconds 1
        if (Test-PortOpen 7687) {
            $ready = $true
            break
        }
    }

    if ($ready) {
        Write-Host "  [OK] Neo4j started and listening on port 7687 (HTTP on 7474)." -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Neo4j did not respond within 30s. Check C:\neo4j\logs." -ForegroundColor Yellow
    }
}

# 3. Check & Start Apache Flink Pipeline
Write-Host "`n[3/5] Checking Apache Flink Pipeline (localhost:8081)..." -ForegroundColor Yellow
if (Test-PortOpen 8081) {
    Write-Host "  [OK] Apache Flink pipeline is already running on port 8081." -ForegroundColor Green
} else {
    Write-Host "  Starting Apache Flink streaming pipeline (fraud_detection.py)..." -ForegroundColor Yellow
    Start-Process -FilePath "python" -ArgumentList "flink/fraud_detection.py" -WorkingDirectory $ProjectRoot -WindowStyle Hidden
    
    $ready = $false
    for ($i = 1; $i -le 25; $i++) {
        Start-Sleep -Seconds 1
        if (Test-PortOpen 8081) {
            $ready = $true
            break
        }
    }

    if ($ready) {
        Write-Host "  [OK] Apache Flink started and listening on port 8081." -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Apache Flink did not open port 8081 within 25s." -ForegroundColor Yellow
    }
}

# 4. Check & Start FastAPI Backend
Write-Host "`n[4/5] Checking FastAPI Backend API (http://127.0.0.1:8000)..." -ForegroundColor Yellow
if (Test-PortOpen 8000) {
    Write-Host "  [OK] Backend server is already running on port 8000." -ForegroundColor Green
} else {
    Write-Host "  Starting FastAPI backend with uvicorn..." -ForegroundColor Yellow
    Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload" -WorkingDirectory $ProjectRoot -WindowStyle Hidden
    
    $ready = $false
    for ($i = 1; $i -le 15; $i++) {
        Start-Sleep -Seconds 1
        if (Test-PortOpen 8000) {
            $ready = $true
            break
        }
    }

    if ($ready) {
        Write-Host "  [OK] FastAPI backend running on http://127.0.0.1:8000." -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] FastAPI server failed to start on port 8000." -ForegroundColor Red
    }
}

# 5. Check & Start React Frontend
Write-Host "`n[5/5] Checking React Dashboard Server (http://localhost:5173)..." -ForegroundColor Yellow
$frontendDir = Join-Path $ProjectRoot "frontend\fraud-dashboard"
if (Test-PortOpen 5173) {
    Write-Host "  [OK] React Dashboard is already running on port 5173." -ForegroundColor Green
} else {
    Write-Host "  Starting Vite React development server..." -ForegroundColor Yellow
    Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev" -WorkingDirectory $frontendDir -WindowStyle Hidden
    
    $ready = $false
    for ($i = 1; $i -le 15; $i++) {
        Start-Sleep -Seconds 1
        if (Test-PortOpen 5173) {
            $ready = $true
            break
        }
    }

    if ($ready) {
        Write-Host "  [OK] React Dashboard running on http://localhost:5173." -ForegroundColor Green
    } else {
        Write-Host "  [WARN] React Dashboard server not yet responding on port 5173." -ForegroundColor Yellow
    }
}

# Summary
Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host " SYSTEM READY - ACTIVE ACCESS ENDPOINTS" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  * React Dashboard UI : http://localhost:5173" -ForegroundColor Green
Write-Host "  * FastAPI Backend    : http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "  * Swagger API Docs   : http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "  * WebSocket Feed     : ws://127.0.0.1:8000/ws/transactions" -ForegroundColor Green
Write-Host "  * Flink MiniCluster  : http://127.0.0.1:8081" -ForegroundColor Green
Write-Host "  * Neo4j Browser UI   : http://localhost:7474" -ForegroundColor Green
Write-Host "  * Kafka Broker       : localhost:9092" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "To stop background services: .\scripts\stop_all.ps1" -ForegroundColor Yellow

if ($KeepAlive) {
    Write-Host "`n[Supervisor] Services running in KeepAlive mode. Press Ctrl+C or kill task to stop." -ForegroundColor Cyan
    while ($true) {
        Start-Sleep -Seconds 30
    }
}
