"""
Service managing active file retrieval, secure download verification,
storage quota calculations, and 2-phase file deletion.
"""

from cloud_backend.core.exceptions import (
    FileNotFoundError,
    StorageError,
    UserNotFoundError,
)
from cloud_backend.db.models.core import Files
from cloud_backend.db.repositories.file_repo import FileRepository
from cloud_backend.db.repositories.reservation_repo import (
    UploadReservationRepository,
)
from cloud_backend.db.repositories.telemetry_repo import TelemetryRepository
from cloud_backend.db.repositories.user_repo import UserRepository
from cloud_backend.schemas.file import StorageResponse
from cloud_backend.services.storage_service import StorageService


class FileService:
    """Service handling file management operations, storage quotas, and deletion flows."""

    def __init__(
        self,
        file_repo: FileRepository,
        reservation_repo: UploadReservationRepository,
        user_repo: UserRepository,
        storage_service: StorageService,
        telemetry_repo: TelemetryRepository,
    ) -> None:
        self.file_repo = file_repo
        self.reservation_repo = reservation_repo
        self.user_repo = user_repo
        self.storage_service = storage_service
        self.telemetry_repo = telemetry_repo

    def list_user_files(
        self, user_id: int, limit: int = 100, offset: int = 0
    ) -> list[Files]:
        """Retrieves all active file records for the specified user."""
        return self.file_repo.list_active_files_by_user(user_id, limit, offset)

    def get_file_for_download(
        self, file_id: int, user_id: int, session_id: int, client_ip: str
    ) -> tuple[Files, str]:
        """
        Validates file ownership, verifies active status and physical disk existence,
        logs download telemetry, and returns the file record along with its absolute path.
        """
        file_record = self.file_repo.get_active_file(file_id=file_id, user_id=user_id)
        if file_record is None:
            raise FileNotFoundError()

        if not self.storage_service.is_safe_path(file_record.storage_path):
            raise FileNotFoundError()
        if not self.storage_service.exists(file_record.storage_path):
            raise StorageError()

        self.telemetry_repo.log_event(
            event_type_name="file.downloaded",
            client_ip=client_ip,
            user_id=user_id,
            session_id=session_id,
            telemetry_data={
                "file_id": file_record.file_id,
                "file_size_bytes": file_record.file_size_bytes,
            },
        )

        return file_record, file_record.storage_path

    def delete_file(
        self, file_id: int, user_id: int, session_id: int, client_ip: str
    ) -> None:
        """Deletes a file record and its physical file from storage."""
        file_record = self.file_repo.mark_as_deleting(file_id=file_id, user_id=user_id)
        if file_record is None:
            raise FileNotFoundError()
        try:
            self.storage_service.delete_file(file_record.storage_path)
        except OSError as err:
            raise StorageError(message=f"Failed to remove physical file: {err}")

        self.file_repo.delete_file_record(file_id=file_id)

        self.telemetry_repo.log_event(
            event_type_name="file.deleted",
            client_ip=client_ip,
            user_id=user_id,
            session_id=session_id,
            telemetry_data={
                "file_id": file_id,
                "file_size_bytes": file_record.file_size_bytes,
            },
        )

    def get_storage_info(self, user_id: int) -> StorageResponse:
        """Calculates total quota, active used bytes, reserved bytes, and remaining available space."""
        user = self.user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError()

        quota_bytes = user.storage_quota_bytes
        used_bytes = self.file_repo.get_used_bytes_by_user(user_id)
        reserved_bytes = self.reservation_repo.get_reserved_bytes_by_user(user_id)
        available_bytes = max(0, quota_bytes - (used_bytes + reserved_bytes))

        return StorageResponse(
            quota_bytes=quota_bytes,
            used_bytes=used_bytes,
            reserved_bytes=reserved_bytes,
            available_bytes=available_bytes,
        )
