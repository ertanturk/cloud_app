"""Session repository for managing session records in the database."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from cloud_backend.db.models.core import Sessions


class SessionRepository:
    """Manages session records in the database."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_session(self, user_id: int, client_ip: str) -> Sessions:
        """Create a new session for the given user and client IP."""
        try:
            now = datetime.now(UTC)
            new_session = Sessions(
                user_id=user_id,
                client_ip=client_ip,
                started_at=now,
                last_activity_at=now,
            )
            self.db.add(new_session)
            self.db.commit()
            self.db.refresh(new_session)
            return new_session
        except Exception:
            self.db.rollback()
            raise

    def get_active_session(self, session_id: int) -> Sessions | None:
        """Get the active session with the given ID, if it exists."""

        cutoff = datetime.now(UTC) - timedelta(minutes=20)
        stmt = select(Sessions).where(
            Sessions.session_id == session_id,
            Sessions.ended_at.is_(None),
            Sessions.last_activity_at >= cutoff,
        )
        return self.db.scalar(stmt)

    def update_last_activity(self, session_id: int) -> Sessions | None:
        """Update the last activity timestamp for the given session."""

        try:
            stmt = (
                select(Sessions)
                .where(Sessions.session_id == session_id)
                .with_for_update()
            )
            session = self.db.scalar(stmt)
            if session is None:
                return None

            session.last_activity_at = datetime.now(UTC)
            self.db.commit()
            self.db.refresh(session)
            return session
        except Exception:
            self.db.rollback()
            raise

    def end_session(self, session_id: int) -> Sessions | None:
        """End the session with the given ID, if it exists."""

        try:
            stmt = (
                select(Sessions)
                .where(Sessions.session_id == session_id)
                .with_for_update()
            )
            session = self.db.scalar(stmt)
            if session is None:
                return None

            session.ended_at = datetime.now(UTC)
            self.db.commit()
            self.db.refresh(session)
            return session
        except Exception:
            self.db.rollback()
            raise

    def list_active_sessions(self) -> list[Sessions]:
        """List all active sessions."""
        cutoff = datetime.now(UTC) - timedelta(minutes=20)
        stmt = select(Sessions).where(
            Sessions.ended_at.is_(None),
            Sessions.last_activity_at >= cutoff,
        )
        return list(self.db.scalars(stmt).all())
