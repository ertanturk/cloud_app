if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator))
{
    throw "Run .\status.ps1 as Administrator first."
}


$pidFile = Join-Path $PSScriptRoot\.. ".cloudstore-backend.pid"
$tunnelPidFile = Join-Path $PSScriptRoot\.. ".cloudstore-cloudflared.pid"
$tunnelService = Get-Service -Name "cloudflared" -ErrorAction SilentlyContinue
$connection = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($connection)
{
    Write-Host "Backend: running (PID $($connection.OwningProcess))"
    try
    { Invoke-RestMethod "http://127.0.0.1:8000/health" | Format-List
    } catch
    { Write-Host "Backend health: failed"
    }
} else
{
    Write-Host "Backend: stopped"
}
if ($tunnelService)
{
    Write-Host "Cloudflare Tunnel service: $($tunnelService.Status)"
    if ($tunnelService.Status -eq "Running")
    {
        try
        {
            Invoke-RestMethod "https://api-cloudvault.tech/health" -TimeoutSec 5 | Format-List
        } catch
        {
            Write-Host "Public health: failed"
        }
    }
} elseif (Test-Path $tunnelPidFile)
{
    $tunnelPid = [int](Get-Content $tunnelPidFile)
    if (Get-Process -Id $tunnelPid -ErrorAction SilentlyContinue)
    {
        Write-Host "Cloudflare Tunnel: running (PID $tunnelPid)"
        try
        {
            Invoke-RestMethod "https://api-cloudvault.tech/health" -TimeoutSec 5 | Format-List
        } catch
        {
            Write-Host "Public health: failed"
        }
    } else
    {
        Write-Host "Cloudflare Tunnel: stopped"
    }
} else
{
    Write-Host "Cloudflare Tunnel: stopped"
}
if (Test-Path $pidFile)
{
    Write-Host "Project PID file: $pidFile"
}
Get-Service -Name "MSSQL*" -ErrorAction SilentlyContinue |
    Select-Object Name,Status | Format-Table -AutoSize
$sqlPort = Get-NetTCPConnection -LocalPort 1433 -State Listen -ErrorAction SilentlyContinue
if ($sqlPort)
{
    Write-Host "SQL Server TCP: listening on 127.0.0.1:1433"
} else
{
    Write-Host "SQL Server TCP: not listening on 127.0.0.1:1433"
}
