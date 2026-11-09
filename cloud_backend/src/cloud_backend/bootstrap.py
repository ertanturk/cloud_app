"""Interactive first-run setup for Cloud Store."""

import getpass
import os
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"


def _ask(label: str, default: str | None = None, secret: bool = False) -> str:
    prompt = f"{label}"
    if default:
        prompt += f" [{default}]"
    prompt += ": "
    value = getpass.getpass(prompt) if secret else input(prompt)
    return value.strip() or (default or "")


def _write_environment() -> None:
    existing: dict[str, str] = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                existing[key.strip()] = value.strip()

    storage_default = (
        "D:\\CloudStore\\Storage" if os.name == "nt" else "/var/lib/cloudstore"
    )
    values = {
        "STORAGE_BASE_PATH": existing.get(
            "STORAGE_BASE_PATH",
            _ask("Storage path", storage_default),
        ),
        "JWT_SECRET_KEY": existing.get(
            "JWT_SECRET_KEY",
            secrets.token_urlsafe(32),
        ),
        "CORE_DB_URL": existing.get(
            "CORE_DB_URL",
            _ask("Core database SQLAlchemy URL"),
        ),
        "TELEMETRY_DB_URL": existing.get(
            "TELEMETRY_DB_URL",
            _ask("Telemetry database SQLAlchemy URL"),
        ),
        "LOG_FILE_PATH": existing.get(
            "LOG_FILE_PATH",
            _ask(
                "Log file path",
                str(Path(storage_default) / "Logs" / "cloud_backend.log"),
            ),
        ),
    }
    ENV_PATH.write_text(
        "".join(f"{key}={value}\n" for key, value in values.items()),
        encoding="utf-8",
    )
    Path(values["STORAGE_BASE_PATH"]).mkdir(parents=True, exist_ok=True)
    Path(values["LOG_FILE_PATH"]).parent.mkdir(parents=True, exist_ok=True)


def _create_admin() -> None:
    from sqlalchemy import select

    from cloud_backend.core.security import hash_password
    from cloud_backend.db.connection import CoreSessionLocal
    from cloud_backend.db.models.core import Users, UserSecrets

    db = CoreSessionLocal()
    try:
        username = _ask("Admin username", "admin")
        existing = db.scalar(select(Users).where(Users.username == username))
        if existing is not None:
            if existing.role != "admin":
                raise RuntimeError(
                    f"Username '{username}' already belongs to a non-admin user."
                )
            print(f"Admin '{username}' already exists; keeping existing account.")
            return

        while True:
            password = _ask("Admin password", secret=True)
            confirmation = _ask("Confirm admin password", secret=True)
            if len(password) >= 8 and password == confirmation:
                break
            print("Passwords must match and contain at least 8 characters.")

        password_hash, password_salt = hash_password(password)
        admin = Users(
            username=username,
            password_hash=password_hash,
            password_hash_version=1,
            role="admin",
        )
        db.add(admin)
        db.flush()
        db.add(
            UserSecrets(
                user_id=admin.user_id,
                password_salt=password_salt,
                totp_enabled=False,
            )
        )
        db.commit()
        print(
            "Admin account created. Complete TOTP setup through "
            "/api/v1/auth/totp/setup before login."
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> int:
    print("Cloud Store first-run setup")
    _write_environment()
    os.environ.update(
        line.split("=", 1)
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines()
        if "=" in line
    )

    from cloud_backend.db.telemetry_events import initialize_database

    initialize_database()
    _create_admin()
    print("Setup complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
