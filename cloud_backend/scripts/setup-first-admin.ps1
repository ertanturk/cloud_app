if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator))
{
    throw "Run .\setup-first-admin.ps1 as Administrator first."
}

$ErrorActionPreference = "Stop"

$baseUrl = "http://127.0.0.1:8000"
try
{
    $health = Invoke-RestMethod "$baseUrl/health" -Method Get
    if ($health.status -ne "healthy")
    {
        throw "Backend health status is not healthy."
    }
} catch
{
    throw "Backend is not running. Start it with .\start.ps1, then retry."
}

$username = Read-Host "Cloud Store administrator username"
$password = Read-Host "Cloud Store administrator password" -AsSecureString
$passwordText = [System.Net.NetworkCredential]::new("", $password).Password

$setupBody = @{
    username = $username
    password = $passwordText
    client_ip = "127.0.0.1"
} | ConvertTo-Json

try
{
    $setup = Invoke-RestMethod `
        -Uri "$baseUrl/api/v1/auth/totp/setup" `
        -Method Post `
        -ContentType "application/json" `
        -Body $setupBody
} finally
{
    $passwordText = $null
}

Write-Host ""
Write-Host "Scan this provisioning URI with a QR-capable authenticator:"
Write-Host $setup.provisioning_uri
if ($setup.provisioning_uri -match "[?&]secret=([^&]+)")
{
    $manualKey = [System.Uri]::UnescapeDataString($matches[1])
    Write-Host ""
    Write-Host "For manual Google Authenticator setup, enter only this key:"
    Write-Host $manualKey
    Write-Host "Choose time-based one-time password (TOTP), not the full otpauth URI."
}
$totpCode = Read-Host "Current 6-digit TOTP code"

$confirmBody = @{
    setup_token = $setup.setup_token
    totp_code = $totpCode
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "$baseUrl/api/v1/auth/totp/confirm" `
    -Method Post `
    -ContentType "application/json" `
    -Body $confirmBody | Out-Null

Write-Host "TOTP setup completed. You can now log in with the administrator account."
