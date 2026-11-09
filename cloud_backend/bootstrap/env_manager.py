"""Safe application environment file updates."""

import os
import secrets
import tempfile
from pathlib import Path


def update_database_urls(env_path: Path, core_url: str, telemetry_url: str) -> None:
    existing: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                existing[key] = value
    existing["CORE_DB_URL"] = core_url
    existing["TELEMETRY_DB_URL"] = telemetry_url
    existing.setdefault("JWT_SECRET_KEY", secrets.token_urlsafe(48))
    existing.setdefault("STORAGE_BASE_PATH", r"D:\CloudStore\Storage")
    existing.setdefault("LOG_FILE_PATH", r"D:\CloudStore\Logs\cloud_backend.log")
    env_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=env_path.parent, prefix=".env.", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write("".join(f"{key}={value}\n" for key, value in existing.items()))
        os.replace(temporary, env_path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
