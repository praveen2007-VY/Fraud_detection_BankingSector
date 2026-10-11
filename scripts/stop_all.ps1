# stop_all.ps1
# Gracefully terminates Fraud Detection System background services

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Stopping Fraud Detection System Services" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

function Stop-PortProcess($port, $name) {
    $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($connections) {
        foreach ($conn in $connections) {
            $pidToKill = $conn.OwningProcess
            try {
                Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
                Write-Host "  [STOPPED] $name (PID: $pidToKill on port $port)" -ForegroundColor Yellow
            } catch {
                Write-Host "  [WARN] Could not stop PID $pidToKill ($name): $_" -ForegroundColor Red
            }
        }
    } else {
        Write-Host "  [INACTIVE] $name on port $port is not running." -ForegroundColor DarkGray
    }
}

Stop-PortProcess 5173 "React Dashboard (Vite)"
Stop-PortProcess 8000 "FastAPI Backend Server"
Stop-PortProcess 9092 "Apache Kafka Broker"
Stop-PortProcess 7687 "Neo4j Graph Database"

Write-Host "`nAll specified services have been stopped." -ForegroundColor Green
