#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v uv >/dev/null 2>&1; then
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

uv python install 3.12
uv sync
uv run python -m cloud_backend.bootstrap

echo "Cloud Store backend is ready."
echo "Start it with: uv run uvicorn cloud_backend.main:app --host 0.0.0.0 --port 8000"
