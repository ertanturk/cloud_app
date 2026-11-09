$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..
$port = 8000
$pidFile = Join-Path $PWD ".cloudstore-backend.pid"
if (Test-Path $pidFile) {
    $oldPid = [int](Get-Content $pidFile)
    if (Get-Process -Id $oldPid -ErrorAction SilentlyContinue) {
        throw "Cloud Store backend is already running with PID $oldPid."
    }
    Remove-Item $pidFile -Force
}
$existing = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    throw "Port $port is already in use by PID $($existing.OwningProcess)."
}
$process = Start-Process uv -ArgumentList "run uvicorn cloud_backend.main:app --host 127.0.0.1 --port $port --workers 1" -PassThru
try {
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        try {
            $health = Invoke-RestMethod "http://127.0.0.1:$port/health"
            if ($health.status -eq "healthy") {
                $owner = Get-NetTCPConnection -LocalPort $port -State Listen
                Set-Content -Path $pidFile -Value $owner.OwningProcess
                Write-Host "Cloud Store backend is ready (PID $($owner.OwningProcess))."
                exit 0
            }
        } catch {}
    }
    throw "Backend health check failed."
} catch {
    if (-not $process.HasExited) { Stop-Process -Id $process.Id }
    throw
}
