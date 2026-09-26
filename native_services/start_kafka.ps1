# Kafka KRaft Startup Script - Runs as independent persistent process
$env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-17.0.20.101-hotspot"
$env:PATH = "$env:JAVA_HOME\bin;" + $env:PATH

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Kafka 3.6.1 KRaft - Native Windows" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Data : C:\kfk-data"
Write-Host "Logs : C:\kfk-logs"
Write-Host "Port : localhost:9092"
Write-Host ""

$javaArgs = @(
    "-Xmx1G", "-Xms1G",
    "-Dlog4j.configuration=file:C:\kfk\config\log4j.properties",
    "-Dkafka.logs.dir=C:\kfk-logs",
    "-cp", "C:\kfk\libs\*",
    "kafka.Kafka",
    "C:\kfk\config\kraft\server.properties"
)

Write-Host "Starting Kafka broker..." -ForegroundColor Yellow
& "$env:JAVA_HOME\bin\java.exe" $javaArgs

Write-Host ""
Write-Host "Kafka broker stopped." -ForegroundColor Red
Write-Host "Press any key to close this window..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
