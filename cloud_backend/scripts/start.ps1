param(
    [string]$TunnelName = $env:CLOUDFLARE_TUNNEL_NAME,
    [string]$PublicBaseUrl = "https://api-cloudvault.tech",
    [int]$Port = 8000
)

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator))
{
    throw "Run start.ps1 as Administrator first."
}

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..
$localBaseUrl = "http://127.0.0.1:$Port"
$pidFile = Join-Path $PWD ".cloudstore-backend.pid"
$tunnelPidFile = Join-Path $PWD ".cloudstore-cloudflared.pid"
$tunnelService = Get-Service -Name "cloudflared" -ErrorAction SilentlyContinue

function Get-DotEnvValue([string]$Path, [string]$Key)
{
    if (-not (Test-Path $Path))
    {
        return $null
    }
    foreach ($line in Get-Content -Path $Path)
    {
        if ($line -match "^\s*$([regex]::Escape($Key))\s*=\s*(.*)\s*$")
        {
            $value = $Matches[1].Trim()
            if (($value.StartsWith('"') -and $value.EndsWith('"')) -or
                ($value.StartsWith("'") -and $value.EndsWith("'")))
            {
                $value = $value.Substring(1, $value.Length - 2)
            }
            return $value
        }
    }
    return $null
}

if ([string]::IsNullOrWhiteSpace($TunnelName))
{
    $TunnelName = Get-DotEnvValue (Join-Path $PWD ".env") "CLOUDFLARE_TUNNEL_NAME"
}
if (-not $tunnelService -and [string]::IsNullOrWhiteSpace($TunnelName))
{
    throw "Named Tunnel is required. Install the cloudflared service with CLOUDFLARE_TUNNEL_TOKEN or set CLOUDFLARE_TUNNEL_NAME in cloud_backend\.env."
}
if (-not $tunnelService -and -not (Get-Command cloudflared -ErrorAction SilentlyContinue))
{
    throw "cloudflared is not installed. Run .\install.ps1 as Administrator first."
}

function Wait-ForHealthy([string]$Url, [string]$ServiceName)
{
    $lastError = "No response received."
    for ($i = 0; $i -lt 60; $i++)
    {
        try
        {
            $health = Invoke-RestMethod "$Url/health" -Method Get -TimeoutSec 5
            if ($health.status -eq "healthy")
            {
                return
            }
            $lastError = "Unexpected status '$($health.status)'."
        } catch
        {
            $lastError = $_.Exception.Message
        }
        Start-Sleep -Seconds 1
    }
    throw "$ServiceName health check failed: $lastError"
}

if (Test-Path $pidFile)
{
    $oldPid = [int](Get-Content $pidFile)
    if (Get-Process -Id $oldPid -ErrorAction SilentlyContinue)
    {
        throw "Cloud Store backend is already running with PID $oldPid."
    }
    Remove-Item $pidFile -Force
}
$existingTunnelPid = $null
if (Test-Path $tunnelPidFile)
{
    $existingTunnelPid = [int](Get-Content $tunnelPidFile)
    if (Get-Process -Id $existingTunnelPid -ErrorAction SilentlyContinue)
    {
        throw "Cloudflare Tunnel is already running with PID $existingTunnelPid."
    }
    Remove-Item $tunnelPidFile -Force
}
$existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($existing)
{
    throw "Port $Port is already in use by PID $($existing.OwningProcess)."
}
$backendProcess = Start-Process uv -ArgumentList "run uvicorn cloud_backend.main:app --host 127.0.0.1 --port $Port --workers 1" -PassThru
$tunnelProcess = $null
try
{
    Wait-ForHealthy $localBaseUrl "Local backend"
    $owner = Get-NetTCPConnection -LocalPort $Port -State Listen
    Set-Content -Path $pidFile -Value $owner.OwningProcess
    Write-Host "Cloud Store backend is ready at $localBaseUrl (PID $($owner.OwningProcess))."

    if ($tunnelService)
    {
        if ($tunnelService.Status -ne "Running")
        {
            Start-Service -Name "cloudflared"
        }
        Write-Host "Cloudflare Tunnel Windows service started."
    } else
    {
        $tunnelProcess = Start-Process cloudflared `
            -ArgumentList "tunnel run $TunnelName" -PassThru
        Set-Content -Path $tunnelPidFile -Value $tunnelProcess.Id
        Write-Host "Cloudflare Tunnel '$TunnelName' started (PID $($tunnelProcess.Id))."
        Start-Sleep -Seconds 2
        if ($tunnelProcess.HasExited)
        {
            throw "Cloudflare Tunnel exited before the public health check. Verify the Named Tunnel name, credentials, and route."
        }
    }

    Wait-ForHealthy $PublicBaseUrl "Public backend"
    Write-Host "Cloud Store is publicly available at $PublicBaseUrl."
} catch
{
    if ($tunnelProcess -and -not $tunnelProcess.HasExited)
    {
        Stop-Process -Id $tunnelProcess.Id
    }
    if (Test-Path $tunnelPidFile)
    { Remove-Item $tunnelPidFile -Force
    }
    if (Test-Path $pidFile)
    {
        $failedBackendPid = [int](Get-Content $pidFile)
        if (Get-Process -Id $failedBackendPid -ErrorAction SilentlyContinue)
        {
            Stop-Process -Id $failedBackendPid
        }
    } elseif (-not $backendProcess.HasExited)
    {
        Stop-Process -Id $backendProcess.Id
    }
    if (Test-Path $pidFile)
    { Remove-Item $pidFile -Force
    }
    throw
}
