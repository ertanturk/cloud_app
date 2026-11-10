if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator))
{
    throw "Run .\stop.ps1 as Administrator first."
}


$ErrorActionPreference = "Stop"
$pidFile = Join-Path $PSScriptRoot\.. ".cloudstore-backend.pid"
$tunnelPidFile = Join-Path $PSScriptRoot\.. ".cloudstore-cloudflared.pid"
$hadTunnelPidFile = Test-Path $tunnelPidFile
$tunnelService = Get-Service -Name "cloudflared" -ErrorAction SilentlyContinue

if ($tunnelService -and $tunnelService.Status -eq "Running")
{
    try
    {
        Stop-Service -Name "cloudflared"
        Write-Host "Stopped Cloudflare Tunnel Windows service."
    } catch
    {
        Write-Warning "Could not stop the cloudflared service (Administrator rights are required). Continuing with the backend."
    }
}

if (Test-Path $tunnelPidFile)
{
    $tunnelPid = [int](Get-Content $tunnelPidFile)
    if (Get-Process -Id $tunnelPid -ErrorAction SilentlyContinue)
    {
        Stop-Process -Id $tunnelPid
        Write-Host "Stopped Cloudflare Tunnel PID $tunnelPid."
        for ($i = 0; $i -lt 20; $i++)
        {
            if (-not (Get-Process -Id $tunnelPid -ErrorAction SilentlyContinue))
            { break
            }
            Start-Sleep -Milliseconds 250
        }
    }
    Remove-Item $tunnelPidFile -Force
}

if (Test-Path $pidFile)
{
    $backendPid = [int](Get-Content $pidFile)
    if (Get-Process -Id $backendPid -ErrorAction SilentlyContinue)
    {
        Stop-Process -Id $backendPid
        Write-Host "Stopped Cloud Store backend PID $backendPid."
        for ($i = 0; $i -lt 20; $i++)
        {
            if (-not (Get-Process -Id $backendPid -ErrorAction SilentlyContinue))
            { break
            }
            Start-Sleep -Milliseconds 250
        }
    }
    Remove-Item $pidFile -Force
} elseif (-not $hadTunnelPidFile)
{
    Write-Host "Cloud Store backend and tunnel are not running."
}
