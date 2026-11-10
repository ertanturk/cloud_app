$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

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

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator))
{
    throw "Run install.ps1 as Administrator first."
}
if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue))
{
    if (-not (Get-Command winget -ErrorAction SilentlyContinue))
    {
        throw "cloudflared is not installed and winget is unavailable. Install winget, then rerun install.ps1."
    }
    Write-Host "Installing cloudflared..."
    winget install --id Cloudflare.cloudflared --exact `
        --accept-source-agreements --accept-package-agreements
    if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue))
    {
        throw "cloudflared installation completed, but cloudflared is not available in PATH. Restart PowerShell and rerun install.ps1."
    }
} else
{
    Write-Host "cloudflared is already installed."
}
$tunnelToken = Get-DotEnvValue (Join-Path $PWD ".env") "CLOUDFLARE_TUNNEL_TOKEN"
$tunnelService = Get-Service -Name "cloudflared" -ErrorAction SilentlyContinue
if ($tunnelService)
{
    Write-Host "cloudflared Windows service is already installed."
} elseif (-not [string]::IsNullOrWhiteSpace($tunnelToken))
{
    Write-Host "Installing cloudflared Windows service..."
    cloudflared.exe service install $tunnelToken
    if (-not (Get-Service -Name "cloudflared" -ErrorAction SilentlyContinue))
    {
        throw "cloudflared service installation did not create the cloudflared Windows service."
    }
} else
{
    Write-Host "CLOUDFLARE_TUNNEL_TOKEN is not set in cloud_backend\.env; skipping tunnel service installation."
}
if (-not (Get-Command uv -ErrorAction SilentlyContinue))
{
    Write-Host "Installing uv..."
    irm https://astral.sh/uv/install.ps1 | iex
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}
uv run python -m bootstrap.orchestrator
