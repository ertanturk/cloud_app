"""File repository for managing file records in the database."""

from datetime import UTC, datetime

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from cloud_backend.db.models.core import Files


class FileRepository:
    """Manages file records in the database, including creation, deletion, and status updates."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_next_file_id(self) -> int:
        """Fetches the next unique file_id from MSSQL sequence."""
        stmt = text("SELECT NEXT VALUE FOR dbo.FileIdSequence")
        return self.db.scalar(stmt)

    def get_used_bytes_by_user(self, user_id: int) -> int:
        """Calculates total used storage bytes for active and deleting files."""
        stmt = select(func.coalesce(func.sum(Files.file_size_bytes), 0)).where(
            Files.user_id == user_id,
            Files.status.in_(["active", "deleting"]),
        )
        return self.db.scalar(stmt) or 0

    def create_file(
        self,
        file_id: int,
        user_id: int,
        session_id: int,
        original_file_name: str,
        storage_path: str,
        checksum_sha256: bytes,
        file_size_bytes: int,
        file_extension: str | None,
        uploaded_at: datetime | None = None,
    ) -> Files:
        """Inserts a completed file record into the database."""
        try:
            now = uploaded_at or datetime.now(UTC)
            file = Files(
                file_id=file_id,
                user_id=user_id,
                session_id=session_id,
                original_file_name=original_file_name,
                storage_path=storage_path,
                checksum_sha256=checksum_sha256,
                file_size_bytes=file_size_bytes,
                file_extension=file_extension,
                status="active",
                uploaded_at=now,
            )
            self.db.add(file)
            self.db.commit()
            self.db.refresh(file)
            return file
        except Exception:
            self.db.rollback()
            raise

    def list_active_files_by_user(self, user_id: int) -> list[Files]:
        """Retrieves all active files belonging to a user ordered by uploaded_at descending."""
        stmt = (
            select(Files)
            .where(Files.user_id == user_id, Files.status == "active")
            .order_by(Files.uploaded_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_active_file(self, file_id: int, user_id: int) -> Files | None:
        """Retrieves an active file belonging to the specified user."""
        stmt = select(Files).where(
            Files.file_id == file_id,
            Files.user_id == user_id,
            Files.status == "active",
        )
        return self.db.scalar(stmt)

    def mark_as_deleting(self, file_id: int, user_id: int) -> Files | None:
        """Changes file status from 'active' to 'deleting' to block downloads."""
        try:
            stmt = (
                select(Files)
                .where(Files.file_id == file_id, Files.user_id == user_id)
                .with_for_update()
            )
            file = self.db.scalar(stmt)
            if file is None:
                return None

            file.status = "deleting"
            self.db.commit()
            self.db.refresh(file)
            return file
        except Exception:
            self.db.rollback()
            raise

    def delete_file_record(self, file_id: int) -> bool:
        """Permanently deletes the file record from SQL Server after physical deletion."""
        try:
            stmt = select(Files).where(Files.file_id == file_id).with_for_update()
            file = self.db.scalar(stmt)
            if file is None:
                return False

            self.db.delete(file)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise
