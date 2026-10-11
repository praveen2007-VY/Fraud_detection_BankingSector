# check_environment.ps1
# Diagnostics and prerequisite verification script for Windows PowerShell

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Fraud Detection System - Environment and Prerequisites" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$allPass = $true

# 1. Python Check
Write-Host "`n[1] Checking Python Installation..." -NoNewline
try {
    $pyVer = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
    Write-Host " [PASS] Python $pyVer" -ForegroundColor Green
} catch {
    Write-Host " [FAIL] Python not found in PATH" -ForegroundColor Red
    $allPass = $false
}

# 2. Node / npm Check
Write-Host "[2] Checking Node.js and npm..." -NoNewline
try {
    $nodeVer = node -v
    $npmVer = npm -v
    Write-Host " [PASS] Node $nodeVer, npm $npmVer" -ForegroundColor Green
} catch {
    Write-Host " [FAIL] Node.js or npm not found in PATH" -ForegroundColor Red
    $allPass = $false
}

# 3. Java / JDK 17 Check
Write-Host "[3] Checking Java 17 for Kafka / Neo4j / Flink..." -NoNewline
$javaHome = "C:\Program Files\Eclipse Adoptium\jdk-17.0.20.101-hotspot"
if (Test-Path "$javaHome\bin\java.exe") {
    Write-Host " [PASS] JDK 17 located at $javaHome" -ForegroundColor Green
} else {
    try {
        $jVer = java -version 2>&1 | Select-Object -First 1
        Write-Host " [PASS] Java in PATH: $jVer" -ForegroundColor Green
    } catch {
        Write-Host " [WARN] Java not found at expected path" -ForegroundColor Yellow
    }
}

# 4. Native Service Directories
Write-Host "[4] Checking Native Service Binaries..."
if (Test-Path "C:\kfk") {
    Write-Host "  - Apache Kafka Home (C:\kfk): [PASS]" -ForegroundColor Green
} else {
    Write-Host "  - Apache Kafka Home (C:\kfk): [FAIL]" -ForegroundColor Red
    $allPass = $false
}

if (Test-Path "C:\neo4j") {
    Write-Host "  - Neo4j Home (C:\neo4j): [PASS]" -ForegroundColor Green
} else {
    Write-Host "  - Neo4j Home (C:\neo4j): [FAIL]" -ForegroundColor Red
    $allPass = $false
}

# 5. Dataset and ML Artifacts
Write-Host "[5] Checking Repository Artifacts..."
$cleanCsv = "data\transactions_clean.csv"
$scoredCsv = "neo4j\scored_transactions.csv"
$c2gatModel = "ml\c2gat_model.pt"
$c2gatScores = "ml\c2gat_scores.csv"

if (Test-Path $cleanCsv) {
    Write-Host "  - Clean Dataset ($cleanCsv): [PASS]" -ForegroundColor Green
} else {
    Write-Host "  - Clean Dataset ($cleanCsv): [FAIL]" -ForegroundColor Red
    $allPass = $false
}

if (Test-Path $scoredCsv) {
    Write-Host "  - Phase 5 Scores ($scoredCsv): [PASS]" -ForegroundColor Green
} else {
    Write-Host "  - Phase 5 Scores ($scoredCsv): [FAIL]" -ForegroundColor Red
    $allPass = $false
}

if (Test-Path $c2gatModel) {
    Write-Host "  - Phase 6 Model ($c2gatModel): [PASS]" -ForegroundColor Green
} else {
    Write-Host "  - Phase 6 Model ($c2gatModel): [FAIL]" -ForegroundColor Red
    $allPass = $false
}

if (Test-Path $c2gatScores) {
    Write-Host "  - Phase 6 Scores ($c2gatScores): [PASS]" -ForegroundColor Green
} else {
    Write-Host "  - Phase 6 Scores ($c2gatScores): [FAIL]" -ForegroundColor Red
    $allPass = $false
}

# 6. Active Port Probes
Write-Host "`n[6] Checking Active Port Bindings..."
function Test-PortBinding($port, $name) {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $iar = $tcp.BeginConnect("127.0.0.1", $port, $null, $null)
        $wait = $iar.AsyncWaitHandle.WaitOne(800)
        if ($wait -and $tcp.Connected) {
            $tcp.EndConnect($iar)
            $tcp.Close()
            Write-Host "  - Port $port ($name): [LISTENING]" -ForegroundColor Green
            return $true
        } else {
            $tcp.Close()
            Write-Host "  - Port $port ($name): [CLOSED / NOT RUNNING]" -ForegroundColor Yellow
            return $false
        }
    } catch {
        Write-Host "  - Port $port ($name): [CLOSED / NOT RUNNING]" -ForegroundColor Yellow
        return $false
    }
}

Test-PortBinding 9092 "Kafka KRaft Broker"
Test-PortBinding 7687 "Neo4j Bolt Protocol"
Test-PortBinding 7474 "Neo4j HTTP Browser"
Test-PortBinding 8000 "FastAPI Backend API"
Test-PortBinding 5173 "React Dashboard (Vite)"

Write-Host "`n==========================================================" -ForegroundColor Cyan
if ($allPass) {
    Write-Host " All required dependencies and artifacts are verified!" -ForegroundColor Green
} else {
    Write-Host " One or more required components need attention." -ForegroundColor Yellow
}
Write-Host "==========================================================" -ForegroundColor Cyan
