"""Idempotent bootstrap seeds for telemetry and the first administrator."""

import re

from sqlalchemy import create_engine, text

from .passwords import prompt_password

TELEMETRY_EVENT_TYPES = (
    "user.created",
    "auth.totp.setup.started",
    "auth.totp.setup.completed",
    "auth.login.failed",
    "auth.login.success",
    "auth.refresh.reuse_detected",
    "auth.refresh.rotated",
    "auth.logout",
    "auth.heartbeat",
    "upload.reserved",
    "upload.completed",
    "upload.cancelled",
    "file.downloaded",
    "file.deleted",
)


def seed_telemetry(telemetry_url: str) -> None:
    engine = create_engine(telemetry_url, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            for event_type_id, event_type in enumerate(TELEMETRY_EVENT_TYPES, 1):
                existing_id = connection.scalar(
                    text(
                        "SELECT event_type_id FROM dbo.TelemetryEvents "
                        "WHERE event_type = :event_type"
                    ),
                    {"event_type": event_type},
                )
                if existing_id is not None:
                    if existing_id != event_type_id:
                        raise RuntimeError(
                            f"Telemetry event ID changed for {event_type}."
                        )
                    continue
                connection.execute(
                    text(
                        "INSERT INTO dbo.TelemetryEvents (event_type_id, event_type) "
                        "VALUES (:event_type_id, :event_type)"
                    ),
                    {"event_type_id": event_type_id, "event_type": event_type},
                )
    finally:
        engine.dispose()


def ensure_first_admin(core_url: str) -> None:
    engine = create_engine(core_url, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            if connection.scalar(
                text("SELECT TOP 1 user_id FROM dbo.Users WHERE role = 'admin'")
            ):
                print("An administrator already exists; keeping existing users.")
                return

            username = input("Cloud Store administrator username: ").strip()
            if not re.fullmatch(r"[A-Za-z0-9_.-]{3,100}", username):
                raise ValueError("Administrator username is invalid.")
            password = prompt_password("Cloud Store administrator password: ")
            from cloud_backend.core.security import hash_password

            password_hash, password_salt = hash_password(password)
            user_id = connection.execute(
                text(
                    "INSERT INTO dbo.Users "
                    "(username, password_hash, password_hash_version, role) "
                    "OUTPUT INSERTED.user_id "
                    "VALUES (:username, :password_hash, 1, 'admin')"
                ),
                {
                    "username": username,
                    "password_hash": password_hash,
                },
            ).scalar_one()
            connection.execute(
                text(
                    "INSERT INTO dbo.UserSecrets "
                    "(user_id, password_salt, totp_enabled) "
                    "VALUES (:user_id, :password_salt, 0)"
                ),
                {"user_id": user_id, "password_salt": password_salt},
            )
            print(
                "Administrator created. Complete TOTP setup at "
                "/api/v1/auth/totp/setup before logging in."
            )
    finally:
        engine.dispose()
