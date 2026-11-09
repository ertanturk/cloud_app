$ErrorActionPreference = "Stop"
$pidFile = Join-Path $PSScriptRoot\.. ".cloudstore-backend.pid"
if (-not (Test-Path $pidFile)) {
    Write-Host "Cloud Store backend is not running."
    exit 0
}
$pid = [int](Get-Content $pidFile)
if (Get-Process -Id $pid -ErrorAction SilentlyContinue) {
    Stop-Process -Id $pid
    Write-Host "Stopped Cloud Store backend PID $pid."
    for ($i = 0; $i -lt 20; $i++) {
        if (-not (Get-Process -Id $pid -ErrorAction SilentlyContinue)) { break }
        Start-Sleep -Milliseconds 250
    }
}
Remove-Item $pidFile -Force
