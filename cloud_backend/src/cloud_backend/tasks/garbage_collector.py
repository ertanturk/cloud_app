"""Background cleanup for temporary upload files and stale reservations."""

import asyncio
import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from cloud_backend.core.app_logging import ProjectLogger
from cloud_backend.db.connection import CoreSessionLocal
from cloud_backend.db.models.core import UploadReservations

logger = ProjectLogger.get_logger(__name__)

ORPHAN_GRACE_PERIOD = timedelta(hours=1)
COMPLETED_RESERVATION_RETENTION = timedelta(hours=24)
GARBAGE_COLLECTION_INTERVAL_SECONDS = 300
TEMP_FILE_PATTERN = re.compile(r"^upload_(?P<file_id>[1-9]\d*)\.tmp$")


def _parse_file_id(file_path: Path) -> int | None:
    match = TEMP_FILE_PATTERN.fullmatch(file_path.name)
    if match is None:
        return None
    return int(match.group("file_id"))


def _delete_file(file_path: Path) -> bool:
    try:
        file_path.unlink(missing_ok=True)
        return True
    except OSError:
        logger.exception("Failed to delete temporary upload file: %s", file_path)
        return False


def _delete_reservation(db: Session, reservation: UploadReservations) -> bool:
    try:
        db.delete(reservation)
        db.commit()
        return True
    except Exception:
        db.rollback()
        logger.exception(
            "Failed to delete upload reservation_id=%s file_id=%s",
            reservation.reservation_id,
            reservation.file_id,
        )
        return False


def cleanup_orphaned_files(
    tmp_dir: str, db: Session, now: datetime | None = None
) -> int:
    """Clean stale temporary files while preserving active uploads."""
    tmp_path = Path(tmp_dir)
    cleanup_time = now or datetime.now(UTC)
    scanned_file_ids: set[int] = set()
    protected_file_ids: set[int] = set()
    deleted_file_ids: set[int] = set()
    deleted_count = 0

    for file_path in tmp_path.glob("*.tmp") if tmp_path.exists() else []:
        file_id = _parse_file_id(file_path)
        if file_id is None:
            logger.warning("Ignoring invalid temporary upload filename: %s", file_path)
            continue
        scanned_file_ids.add(file_id)

        reservation = db.scalar(
            select(UploadReservations).where(UploadReservations.file_id == file_id)
        )
        if reservation is None:
            file_age = cleanup_time - datetime.fromtimestamp(
                file_path.stat().st_mtime, tz=UTC
            )
            if file_age > ORPHAN_GRACE_PERIOD and _delete_file(file_path):
                deleted_count += 1
            continue

        if reservation.status == "completed":
            if _delete_file(file_path):
                deleted_count += 1
            else:
                protected_file_ids.add(file_id)
            continue

        if reservation.expires_at > cleanup_time:
            protected_file_ids.add(file_id)
            continue

        if not _delete_file(file_path):
            protected_file_ids.add(file_id)
            continue
        deleted_count += 1
        deleted_file_ids.add(file_id)
        _delete_reservation(db, reservation)

    expired_pending = db.scalars(
        select(UploadReservations).where(
            UploadReservations.status.in_(["reserved", "uploading"]),
            UploadReservations.expires_at <= cleanup_time,
        )
    ).all()
    for reservation in expired_pending:
        if reservation.file_id in protected_file_ids:
            continue
        if (
            reservation.file_id not in scanned_file_ids
            or reservation.file_id in deleted_file_ids
        ):
            _delete_reservation(db, reservation)

    return deleted_count


def cleanup_completed_reservations(db: Session, now: datetime | None = None) -> int:
    """Delete completed reservations after their retry-retention window."""
    cleanup_time = now or datetime.now(UTC)
    cutoff = cleanup_time - COMPLETED_RESERVATION_RETENTION
    reservations = db.scalars(
        select(UploadReservations).where(
            UploadReservations.status == "completed",
            UploadReservations.completed_at.is_not(None),
            UploadReservations.completed_at <= cutoff,
        )
    ).all()
    deleted_count = 0
    for reservation in reservations:
        if _delete_reservation(db, reservation):
            deleted_count += 1
    return deleted_count


def _garbage_collect_once(
    tmp_dir: str, session_factory: Callable[[], Session]
) -> tuple[int, int]:
    db = session_factory()
    try:
        temp_deleted = cleanup_orphaned_files(tmp_dir, db)
        reservations_deleted = cleanup_completed_reservations(db)
        return temp_deleted, reservations_deleted
    finally:
        db.close()


async def garbage_collector_task(
    tmp_dir: str,
    session_factory: Callable[[], Session] = CoreSessionLocal,
) -> None:
    """Run temporary-file and reservation cleanup periodically."""
    while True:
        try:
            temp_deleted, reservations_deleted = await asyncio.to_thread(
                _garbage_collect_once, tmp_dir, session_factory
            )
            logger.info(
                "Garbage collection completed; deleted %d temp files and %d reservations.",
                temp_deleted,
                reservations_deleted,
            )
        except asyncio.CancelledError:
            logger.info("Garbage collector task stopped.")
            raise
        except Exception:
            logger.exception("Error during garbage collection.")
        await asyncio.sleep(GARBAGE_COLLECTION_INTERVAL_SECONDS)
