$pidFile = Join-Path $PSScriptRoot\.. ".cloudstore-backend.pid"
$connection = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($connection) {
    Write-Host "Backend: running (PID $($connection.OwningProcess))"
    try { Invoke-RestMethod "http://127.0.0.1:8000/health" | Format-List } catch { Write-Host "Backend health: failed" }
} else {
    Write-Host "Backend: stopped"
}
if (Test-Path $pidFile) {
    Write-Host "Project PID file: $pidFile"
}
Get-Service -Name "MSSQL*" -ErrorAction SilentlyContinue |
    Select-Object Name,Status | Format-Table -AutoSize
$sqlPort = Get-NetTCPConnection -LocalPort 1433 -State Listen -ErrorAction SilentlyContinue
if ($sqlPort) {
    Write-Host "SQL Server TCP: listening on 127.0.0.1:1433"
} else {
    Write-Host "SQL Server TCP: not listening on 127.0.0.1:1433"
}
