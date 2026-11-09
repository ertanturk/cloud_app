"""
Service managing upload space reservation, streaming chunk ingestion,
SHA-256 integrity verification, and atomic file creation.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from cloud_backend.core.exceptions import (
    QuotaExceededError,
    ReservationExpiredError,
    ReservationNotFoundError,
    UploadSizeMismatchError,
    UserNotFoundError,
)
from cloud_backend.db.models.core import Files, UploadReservations
from cloud_backend.db.repositories.file_repo import FileRepository
from cloud_backend.db.repositories.reservation_repo import (
    UploadReservationRepository,
)
from cloud_backend.db.repositories.telemetry_repo import TelemetryRepository
from cloud_backend.db.repositories.user_repo import UserRepository
from cloud_backend.services.storage_service import StorageService


class UploadService:
    """Service orchestrating chunked file upload operations, quota enforcement, and verification."""

    def __init__(
        self,
        reservation_repo: UploadReservationRepository,
        file_repo: FileRepository,
        user_repo: UserRepository,
        storage_service: StorageService,
        telemetry_repo: TelemetryRepository,
    ) -> None:
        self.reservation_repo = reservation_repo
        self.file_repo = file_repo
        self.user_repo = user_repo
        self.storage_service = storage_service
        self.telemetry_repo = telemetry_repo

    def reserve_upload(
        self,
        user_id: int,
        session_id: int,
        file_name: str,
        file_size_bytes: int,
        client_ip: str,
    ) -> UploadReservations:
        """
        Pessimistically locks user row, verifies storage quota availability,
        reserves next sequence file_id, creates reservation record, and logs telemetry.
        """
        user = self.reservation_repo.get_user_for_quota_lock(user_id)
        if user is None:
            raise UserNotFoundError()

        used_bytes = self.file_repo.get_used_bytes_by_user(user_id)
        reserved_bytes = self.reservation_repo.get_reserved_bytes_by_user(user_id)

        if used_bytes + reserved_bytes + file_size_bytes > user.storage_quota_bytes:
            raise QuotaExceededError()

        file_id = self.file_repo.get_next_file_id()
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        reservation = self.reservation_repo.create_reservation(
            file_id=file_id,
            user_id=user_id,
            session_id=session_id,
            reserved_bytes=file_size_bytes,
            expires_at=expires_at,
        )
        # Ensure zero-byte uploads still have a concrete temporary artifact.
        if file_size_bytes == 0:
            self.storage_service.write_chunk(
                self.storage_service.get_temp_path(file_id), b"", append=False
            )

        self.telemetry_repo.log_event(
            event_type_name="upload.reserved",
            client_ip=client_ip,
            user_id=user_id,
            session_id=session_id,
            telemetry_data={
                "reservation_id": reservation.reservation_id,
                "file_id": file_id,
                "reserved_bytes": file_size_bytes,
                "file_name": file_name,
            },
        )

        return reservation

    def upload_chunk(
        self,
        reservation_id: int,
        user_id: int,
        chunk: bytes,
    ) -> None:
        """
        Validates reservation state, streams chunk bytes into temporary storage,
        and refreshes reservation activity timestamp.
        """
        reservation = self.reservation_repo.get_by_id(
            reservation_id=reservation_id, user_id=user_id
        )
        if reservation is None:
            raise ReservationNotFoundError()

        now = datetime.now(UTC)
        if reservation.expires_at < now or reservation.status not in [
            "reserved",
            "uploading",
        ]:
            raise ReservationExpiredError()

        current_size = (
            self.storage_service.file_size(
                self.storage_service.get_temp_path(reservation.file_id)
            )
            if self.storage_service.exists(
                self.storage_service.get_temp_path(reservation.file_id)
            )
            else 0
        )
        if current_size + len(chunk) > reservation.reserved_bytes:
            raise UploadSizeMismatchError()

        new_expires_at = now + timedelta(minutes=10)
        self.reservation_repo.update_status(
            reservation_id=reservation_id,
            user_id=user_id,
            status="uploading",
            new_expires_at=new_expires_at,
        )

        temp_path = self.storage_service.get_temp_path(reservation.file_id)
        self.storage_service.write_chunk(temp_path, chunk, append=True)

    def complete_upload(
        self,
        reservation_id: int,
        user_id: int,
        session_id: int,
        original_file_name: str,
        client_ip: str,
    ) -> Files:
        """
        Validates temporary file integrity (SHA-256 and size matching), moves file to final path,
        creates completed file record in DB, and marks reservation as completed.
        """
        reservation = self.reservation_repo.get_by_id(
            reservation_id=reservation_id, user_id=user_id
        )
        if reservation is None:
            raise ReservationNotFoundError()

        if reservation.status == "completed":
            existing = self.file_repo.get_active_file(reservation.file_id, user_id)
            if existing is None:
                raise ReservationNotFoundError()
            return existing

        if reservation.expires_at < datetime.now(UTC):
            raise ReservationExpiredError()

        temp_path = self.storage_service.get_temp_path(reservation.file_id)

        checksum_sha256, actual_size = self.storage_service.compute_checksum_and_size(
            temp_path
        )

        if actual_size != reservation.reserved_bytes:
            self.storage_service.delete_file(temp_path)
            raise UploadSizeMismatchError()

        extension = Path(original_file_name).suffix.lstrip(".").lower() or None

        final_path = self.storage_service.get_final_path(
            user_id=user_id,
            file_id=reservation.file_id,
            extension=extension,
        )

        self.storage_service.move_file(temp_path, final_path)

        file_record = self.file_repo.create_file(
            file_id=reservation.file_id,
            user_id=user_id,
            session_id=session_id,
            original_file_name=original_file_name,
            storage_path=final_path,
            checksum_sha256=checksum_sha256,
            file_size_bytes=actual_size,
            file_extension=extension,
        )

        self.reservation_repo.update_status(
            reservation_id=reservation_id,
            user_id=user_id,
            status="completed",
        )

        self.telemetry_repo.log_event(
            event_type_name="upload.completed",
            client_ip=client_ip,
            user_id=user_id,
            session_id=session_id,
            telemetry_data={
                "file_id": file_record.file_id,
                "file_size_bytes": actual_size,
            },
        )

        return file_record

    def cancel_upload(
        self,
        reservation_id: int,
        user_id: int,
        session_id: int,
        client_ip: str,
    ) -> None:
        """
        Cancels an ongoing upload reservation, purges temporary disk file,
        removes the reservation after its temporary file is cleaned up.
        """
        reservation = self.reservation_repo.get_by_id(
            reservation_id=reservation_id, user_id=user_id
        )
        if reservation is None:
            raise ReservationNotFoundError()

        temp_path = self.storage_service.get_temp_path(reservation.file_id)
        self.storage_service.delete_file(temp_path)

        if reservation.status == "completed":
            return
        self.reservation_repo.delete_reservation(
            reservation_id=reservation_id, user_id=user_id
        )

        self.telemetry_repo.log_event(
            event_type_name="upload.cancelled",
            client_ip=client_ip,
            user_id=user_id,
            session_id=session_id,
            telemetry_data={"reservation_id": reservation_id},
        )
