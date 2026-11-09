"""Background cleanup for inactive sessions and their refresh tokens."""

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import update
from sqlalchemy.orm import Session

from cloud_backend.core.app_logging import ProjectLogger
from cloud_backend.db.connection import CoreSessionLocal
from cloud_backend.db.models.core import RefreshTokens, Sessions

logger = ProjectLogger.get_logger(__name__)

SESSION_TIMEOUT = timedelta(minutes=20)
CLEANUP_INTERVAL_SECONDS = 60


def cleanup_inactive_sessions(db: Session, now: datetime | None = None) -> int:
    """End inactive sessions and revoke their active refresh tokens."""
    cleanup_time = now or datetime.now(UTC)
    cutoff_datetime = cleanup_time - SESSION_TIMEOUT

    result = db.execute(
        update(Sessions)
        .where(
            Sessions.last_activity_at < cutoff_datetime,
            Sessions.ended_at.is_(None),
        )
        .values(ended_at=cleanup_time)
        .returning(Sessions.session_id)
    )
    session_ids = list(result.scalars().all())
    if session_ids:
        db.execute(
            update(RefreshTokens)
            .where(
                RefreshTokens.session_id.in_(session_ids),
                RefreshTokens.revoked_at.is_(None),
            )
            .values(revoked_at=cleanup_time)
        )
    db.commit()
    return len(session_ids)


def _cleanup_once(session_factory: Callable[[], Session]) -> int:
    db = session_factory()
    try:
        return cleanup_inactive_sessions(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def session_cleanup_task(
    session_factory: Callable[[], Session] = CoreSessionLocal,
) -> None:
    """Run session cleanup every minute using the synchronous DB in a worker thread."""
    while True:
        try:
            ended_count = await asyncio.to_thread(_cleanup_once, session_factory)
            logger.info("Session cleanup completed; ended %d sessions.", ended_count)
        except asyncio.CancelledError:
            logger.info("Session cleanup task stopped.")
            raise
        except Exception:
            logger.exception("Error during session cleanup.")
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
