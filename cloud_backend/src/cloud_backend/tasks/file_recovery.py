"""Recovery task for file records stuck in the deleting state."""

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

FILE_RECOVERY_INTERVAL_SECONDS = 60


def recover_deleting_files(storage: StorageService, db: Session) -> tuple[int, int]:
    """Retry physical and metadata deletion for files marked as deleting."""
    records = db.scalars(
        select(Files).where(Files.status == "deleting").with_for_update()
    ).all()
    recovered_physical = 0
    recovered_records = 0

    for file_record in records:
        if not storage.is_safe_path(file_record.storage_path):
            logger.error(
                "Refusing recovery for unsafe file path file_id=%s path=%s",
                file_record.file_id,
                file_record.storage_path,
            )
            continue

        try:
            if storage.exists(file_record.storage_path):
                storage.delete_file(file_record.storage_path)
                recovered_physical += 1
        except Exception:
            db.rollback()
            logger.exception(
                "Failed to recover physical file deletion file_id=%s path=%s",
                file_record.file_id,
                file_record.storage_path,
            )
            continue

        try:
            db.delete(file_record)
            db.commit()
            recovered_records += 1
        except Exception:
            db.rollback()
            logger.exception(
                "Failed to delete recovered file record file_id=%s",
                file_record.file_id,
            )

    return recovered_physical, recovered_records


def _recover_once(
    storage_root: str, session_factory: Callable[[], Session]
) -> tuple[int, int]:
    db = session_factory()
    try:
        return recover_deleting_files(StorageService(storage_root), db)
    finally:
        db.close()


async def file_recovery_task(
    storage_root: str = get_config().STORAGE_BASE_PATH,
    session_factory: Callable[[], Session] = CoreSessionLocal,
) -> None:
    """Run deleting-file recovery periodically."""
    while True:
        try:
            physical_count, record_count = await asyncio.to_thread(
                _recover_once, storage_root, session_factory
            )
            logger.info(
                "File recovery completed; removed %d physical files and %d records.",
                physical_count,
                record_count,
            )
        except asyncio.CancelledError:
            logger.info("File recovery task stopped.")
            raise
        except Exception:
            logger.exception("Error during file recovery.")
        await asyncio.sleep(FILE_RECOVERY_INTERVAL_SECONDS)
