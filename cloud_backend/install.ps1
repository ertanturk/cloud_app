$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv..."
    irm https://astral.sh/uv/install.ps1 | iex
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

uv python install 3.12
uv sync
uv run python -m cloud_backend.bootstrap

Write-Host "Cloud Store backend is ready."
Write-Host "Start it with: uv run uvicorn cloud_backend.main:app --host 0.0.0.0 --port 8000"
