"""
Service monitoring system hardware metrics (CPU, RAM, Disk, Network)
and application-level statistics.
"""

import time
from datetime import UTC, datetime

import psutil
from sqlalchemy import func, select

from cloud_backend.db.models.core import Files, UploadReservations, Users
from cloud_backend.db.repositories.file_repo import FileRepository
from cloud_backend.db.repositories.reservation_repo import (
    UploadReservationRepository,
)
from cloud_backend.db.repositories.session_repo import SessionRepository
from cloud_backend.db.repositories.user_repo import UserRepository
from cloud_backend.schemas.admin import (
    ApplicationMetricsResponse,
    SystemMetricsResponse,
)


class MetricsService:
    """Service monitoring system resources and computing backend operational metrics."""

    def __init__(
        self,
        user_repo: UserRepository,
        session_repo: SessionRepository,
        file_repo: FileRepository,
        reservation_repo: UploadReservationRepository,
        storage_root: str | None = None,
    ) -> None:
        self.user_repo = user_repo
        self.session_repo = session_repo
        self.file_repo = file_repo
        self.reservation_repo = reservation_repo
        if storage_root is None:
            from cloud_backend.core.config import get_config

            storage_root = get_config().STORAGE_BASE_PATH
        self.storage_root = storage_root

        # Internal state for delta-based network speed calculation
        self._last_net_time: float | None = None
        self._last_net_bytes_recv: int | None = None
        self._last_net_bytes_sent: int | None = None

    def get_system_metrics(self) -> SystemMetricsResponse:
        """Collects real-time hardware performance metrics via psutil."""
        cpu_percent = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(self.storage_root)

        # Network transfer speed computation (bytes/sec delta)
        now = time.time()
        net_io = psutil.net_io_counters()

        bytes_recv_rate = 0.0
        bytes_sent_rate = 0.0

        if (
            self._last_net_time is not None
            and self._last_net_bytes_recv is not None
            and self._last_net_bytes_sent is not None
        ):
            time_delta = now - self._last_net_time
            if time_delta > 0:
                bytes_recv_rate = max(
                    0.0, (net_io.bytes_recv - self._last_net_bytes_recv) / time_delta
                )
                bytes_sent_rate = max(
                    0.0, (net_io.bytes_sent - self._last_net_bytes_sent) / time_delta
                )

        self._last_net_time = now
        self._last_net_bytes_recv = net_io.bytes_recv
        self._last_net_bytes_sent = net_io.bytes_sent

        return SystemMetricsResponse(
            cpu_usage_percent=float(cpu_percent),
            ram_used_bytes=mem.used,
            ram_total_bytes=mem.total,
            ram_usage_percent=float(mem.percent),
            disk_used_bytes=disk.used,
            disk_total_bytes=disk.total,
            disk_usage_percent=float(disk.percent),
            network_bytes_recv_per_sec=bytes_recv_rate,
            network_bytes_sent_per_sec=bytes_sent_rate,
        )

    def get_application_metrics(self) -> ApplicationMetricsResponse:
        """Aggregates system-wide application database statistics."""
        active_sessions_count = len(self.session_repo.list_active_sessions())

        total_users_stmt = select(func.count(Users.user_id))
        total_users = self.user_repo.db.scalar(total_users_stmt) or 0

        active_files_stmt = select(
            func.count(Files.file_id),
            func.coalesce(func.sum(Files.file_size_bytes), 0),
        ).where(Files.status == "active")

        result = self.file_repo.db.execute(active_files_stmt).first()
        total_files = result[0] if result else 0
        total_storage_used = result[1] if result else 0

        now = datetime.now(UTC)
        active_uploads_stmt = select(
            func.count(UploadReservations.reservation_id)
        ).where(
            UploadReservations.status.in_(["reserved", "uploading"]),
            UploadReservations.expires_at >= now,
        )
        active_uploads = self.reservation_repo.db.scalar(active_uploads_stmt) or 0

        return ApplicationMetricsResponse(
            active_sessions=active_sessions_count,
            active_uploads=active_uploads,
            total_users=total_users,
            total_files=total_files,
            total_storage_used_bytes=total_storage_used,
        )
