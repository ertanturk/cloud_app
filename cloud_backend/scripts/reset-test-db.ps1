$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator))
{
    throw "Run reset-test-db.ps1 as Administrator first."
}

if (-not $args.Contains("--yes"))
{
    throw "This deletes CloudCore and CloudTelemetry. Re-run with --yes."
}

$stopScript = Join-Path $PSScriptRoot "stop.ps1"
& $stopScript
uv run python -m bootstrap.reset_test_databases --yes
if ($LASTEXITCODE -ne 0)
{
    throw "Test database reset failed. Install was not started."
}
& (Join-Path $PSScriptRoot "install.ps1")
