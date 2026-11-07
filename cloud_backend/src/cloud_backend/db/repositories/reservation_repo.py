"""
Upload reservation repository for managing reservation records in the database.
"""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cloud_backend.db.models.core import UploadReservations, Users


class UploadReservationRepository:
    """Manages upload reservation records and quota locks in the database."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user_for_quota_lock(self, user_id: int) -> Users | None:
        """
        Locks the User row in the database (UPDLOCK / HOLDLOCK) during quota calculation
        to prevent race conditions with concurrent upload reservations.
        """
        try:
            stmt = select(Users).where(Users.user_id == user_id).with_for_update()
            return self.db.scalar(stmt)
        except Exception:
            self.db.rollback()
            raise

    def get_reserved_bytes_by_user(self, user_id: int) -> int:
        """
        Calculates total reserved bytes for pending uploads (status: 'reserved' or 'uploading').
        Completed reservations are excluded as their size is already counted in Files.
        """
        stmt = select(
            func.coalesce(func.sum(UploadReservations.reserved_bytes), 0)
        ).where(
            UploadReservations.user_id == user_id,
            UploadReservations.status.in_(["reserved", "uploading"]),
        )
        return self.db.scalar(stmt) or 0

    def create_reservation(
        self,
        file_id: int,
        user_id: int,
        session_id: int,
        reserved_bytes: int,
        expires_at: datetime,
    ) -> UploadReservations:
        """Creates a new upload reservation record with status 'reserved'."""
        try:
            now = datetime.now(UTC)
            reservation = UploadReservations(
                file_id=file_id,
                user_id=user_id,
                session_id=session_id,
                reserved_bytes=reserved_bytes,
                status="reserved",
                created_at=now,
                expires_at=expires_at,
            )
            self.db.add(reservation)
            self.db.commit()
            self.db.refresh(reservation)
            return reservation
        except Exception:
            self.db.rollback()
            raise

    def get_by_id(self, reservation_id: int, user_id: int) -> UploadReservations | None:
        """Retrieves a reservation by reservation_id and user_id."""
        stmt = select(UploadReservations).where(
            UploadReservations.reservation_id == reservation_id,
            UploadReservations.user_id == user_id,
        )
        return self.db.scalar(stmt)

    def get_by_file_id(self, file_id: int) -> UploadReservations | None:
        """Retrieves a reservation by file_id to check for existing completed uploads."""
        stmt = select(UploadReservations).where(UploadReservations.file_id == file_id)
        return self.db.scalar(stmt)

    def update_status(
        self,
        reservation_id: int,
        user_id: int,
        status: str,
        new_expires_at: datetime | None = None,
    ) -> UploadReservations | None:
        """
        Updates reservation state ('reserved', 'uploading', 'completed') and handles
        associated timestamps (upload_started_at, completed_at, last_activity_at).
        """
        try:
            stmt = (
                select(UploadReservations)
                .where(
                    UploadReservations.reservation_id == reservation_id,
                    UploadReservations.user_id == user_id,
                )
                .with_for_update()
            )
            reservation = self.db.scalar(stmt)
            if reservation is None:
                return None

            now = datetime.now(UTC)
            reservation.status = status
            reservation.last_activity_at = now

            if status == "uploading":
                if reservation.upload_started_at is None:
                    reservation.upload_started_at = now
                if new_expires_at:
                    reservation.expires_at = new_expires_at
            elif status == "completed":
                reservation.completed_at = now

            self.db.commit()
            self.db.refresh(reservation)
            return reservation
        except Exception:
            self.db.rollback()
            raise
