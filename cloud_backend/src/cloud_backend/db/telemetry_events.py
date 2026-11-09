"""Telemetry schema creation and event catalog initialization."""

from sqlalchemy import select

from cloud_backend.core.app_logging import ProjectLogger
from cloud_backend.db.connection import (
    TelemetrySessionLocal,
    core_engine,
    telemetry_engine,
)
from cloud_backend.db.models.core import Base as CoreBase
from cloud_backend.db.models.telemetry import Base as TelemetryBase
from cloud_backend.db.models.telemetry import TelemetryEvents

logger = ProjectLogger.get_logger(__name__)

TELEMETRY_EVENTS: dict[int, str] = {
    1: "auth.login.success",
    2: "auth.login.failed",
    3: "auth.totp.setup.started",
    4: "auth.totp.setup.completed",
    5: "auth.refresh.success",
    6: "auth.refresh.failed",
    7: "auth.refresh.reuse_detected",
    8: "auth.logout",
    9: "session.created",
    10: "session.ended",
    11: "session.expired",
    12: "upload.started",
    13: "upload.completed",
    14: "upload.failed",
    15: "upload.cancelled",
    16: "download.completed",
    17: "download.failed",
    18: "file.delete.started",
    19: "file.delete.completed",
    20: "file.delete.failed",
    21: "storage.error",
    22: "server.error",
    23: "user.created",
    24: "upload.reserved",
    25: "file.downloaded",
    26: "file.deleted",
    27: "auth.refresh.rotated",
    28: "auth.heartbeat",
}


def initialize_database() -> None:
    """Create both database schemas and insert missing telemetry catalog events."""
    CoreBase.metadata.create_all(bind=core_engine)
    TelemetryBase.metadata.create_all(bind=telemetry_engine)
    db = TelemetrySessionLocal()
    try:
        existing = {
            event.event_type_id: event.event_type
            for event in db.scalars(select(TelemetryEvents)).all()
        }
        conflicts = {
            event_id: (existing[event_id], event_name)
            for event_id, event_name in TELEMETRY_EVENTS.items()
            if event_id in existing and existing[event_id] != event_name
        }
        if conflicts:
            raise RuntimeError(f"Telemetry event ID conflicts: {conflicts}")

        known_names = set(existing.values())
        db.add_all(
            TelemetryEvents(event_type_id=event_id, event_type=event_name)
            for event_id, event_name in TELEMETRY_EVENTS.items()
            if event_id not in existing and event_name not in known_names
        )
        db.commit()
        logger.info("Telemetry schema and event catalog initialized.")
    except Exception:
        db.rollback()
        logger.exception("Failed to initialize telemetry schema and event catalog.")
        raise
    finally:
        db.close()


initialize_telemetry_database = initialize_database
