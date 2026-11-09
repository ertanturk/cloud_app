"""Weekly integrity checks for stored files."""

import asyncio
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from cloud_backend.core.app_logging import ProjectLogger
from cloud_backend.core.config import get_config
from cloud_backend.db.connection import CoreSessionLocal
from cloud_backend.db.models.core import Files
from cloud_backend.services.storage_service import StorageService

logger = ProjectLogger.get_logger(__name__)

CHECKSUM_CHECK_INTERVAL_SECONDS = 7 * 24 * 60 * 60


def check_file_checksums(storage: StorageService, db: Session) -> tuple[int, int]:
    """Check stored file size and SHA-256 values without modifying records."""
    records = db.scalars(select(Files)).all()
    checked_count = 0
    mismatch_count = 0

    for file_record in records:
        checked_count += 1
        if not storage.is_safe_path(file_record.storage_path):
            logger.error(
                "Checksum check refused unsafe file path file_id=%s path=%s",
                file_record.file_id,
                file_record.storage_path,
            )
            mismatch_count += 1
            continue
        if not storage.exists(file_record.storage_path):
            logger.error(
                "Stored file is missing file_id=%s path=%s",
                file_record.file_id,
                file_record.storage_path,
            )
            mismatch_count += 1
            continue

        try:
            checksum, size = storage.compute_checksum_and_size(file_record.storage_path)
        except Exception:
            logger.exception(
                "Failed to calculate checksum file_id=%s path=%s",
                file_record.file_id,
                file_record.storage_path,
            )
            mismatch_count += 1
            continue

        if (
            checksum != file_record.checksum_sha256
            or size != file_record.file_size_bytes
        ):
            logger.error(
                "Stored file integrity mismatch file_id=%s expected_size=%s actual_size=%s",
                file_record.file_id,
                file_record.file_size_bytes,
                size,
            )
            mismatch_count += 1

    return checked_count, mismatch_count


def _check_once(
    storage_root: str, session_factory: Callable[[], Session]
) -> tuple[int, int]:
    db = session_factory()
    try:
        return check_file_checksums(StorageService(storage_root), db)
    finally:
        db.close()


async def checksum_checker_task(
    storage_root: str = get_config().STORAGE_BASE_PATH,
    session_factory: Callable[[], Session] = CoreSessionLocal,
) -> None:
    """Run stored-file integrity checks weekly."""
    while True:
        try:
            checked_count, mismatch_count = await asyncio.to_thread(
                _check_once, storage_root, session_factory
            )
            logger.info(
                "Checksum check completed; checked %d files and found %d issues.",
                checked_count,
                mismatch_count,
            )
        except asyncio.CancelledError:
            logger.info("Checksum checker task stopped.")
            raise
        except Exception:
            logger.exception("Error during checksum checking.")
        await asyncio.sleep(CHECKSUM_CHECK_INTERVAL_SECONDS)
