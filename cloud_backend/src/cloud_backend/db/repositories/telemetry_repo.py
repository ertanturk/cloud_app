"""Telemetry repository for managing telemetry events in the database."""

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from cloud_backend.core.app_logging import ProjectLogger
from cloud_backend.db.models.telemetry import Telemetry, TelemetryEvents

logger = ProjectLogger.get_logger(__name__)


class TelemetryRepository:
    """Manages logging and querying application event telemetry in TelemetryDB."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def log_event(
        self,
        event_type_name: str,
        client_ip: str,
        user_id: int | None = None,
        session_id: int | None = None,
        telemetry_data: dict | None = None,
    ) -> Telemetry | None:
        """
        Logs a telemetry event to TelemetryDB.
        Resolves event_type_id from event_type_name and converts telemetry_data dict to JSON string.
        """
        try:
            event_type_stmt = select(TelemetryEvents.event_type_id).where(
                TelemetryEvents.event_type == event_type_name
            )
            event_type_id = self.db.scalar(event_type_stmt)
            if event_type_id is None:
                return None

            json_payload = json.dumps(telemetry_data) if telemetry_data else None

            event = Telemetry(
                user_id=user_id,
                session_id=session_id,
                client_ip=client_ip,
                event_type_id=event_type_id,
                telemetry_data=json_payload,
                event_time=datetime.now(UTC),
            )
            self.db.add(event)
            self.db.commit()
            self.db.refresh(event)
            return event
        except Exception:
            logger.exception("Failed to write telemetry event type=%s", event_type_name)
            self.db.rollback()
            raise

    def list_events(
        self,
        limit: int = 50,
        offset: int = 0,
        event_type_name: str | None = None,
        user_id: int | None = None,
    ) -> list[tuple[Telemetry, str]]:
        """
        Retrieves paginated telemetry events joined with TelemetryEvents.event_type name.
        Returns a list of tuples: (Telemetry instance, event_type string).
        """
        stmt = (
            select(Telemetry, TelemetryEvents.event_type)
            .join(
                TelemetryEvents,
                Telemetry.event_type_id == TelemetryEvents.event_type_id,
            )
            .order_by(Telemetry.event_time.desc())
        )

        if event_type_name:
            stmt = stmt.where(TelemetryEvents.event_type == event_type_name)

        if user_id is not None:
            stmt = stmt.where(Telemetry.user_id == user_id)

        stmt = stmt.limit(limit).offset(offset)
        return list(self.db.execute(stmt).all())

    def get_recent_events(self, limit: int = 100) -> list[tuple[Telemetry, str]]:
        """Alias method for retrieving recent telemetry logs with event_type names."""
        return self.list_events(limit=limit, offset=0)
