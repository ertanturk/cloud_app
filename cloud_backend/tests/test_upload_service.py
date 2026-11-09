from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from cloud_backend.core.exceptions import QuotaExceededError, UploadSizeMismatchError
from cloud_backend.services.upload_service import UploadService


def _service() -> tuple[UploadService, Mock, Mock, Mock, Mock, Mock]:
    reservation_repo = Mock()
    file_repo = Mock()
    user_repo = Mock()
    storage = Mock()
    telemetry = Mock()
    return (
        UploadService(reservation_repo, file_repo, user_repo, storage, telemetry),
        reservation_repo,
        file_repo,
        user_repo,
        storage,
        telemetry,
    )


def test_reserve_upload_rejects_when_quota_is_exceeded() -> None:
    service, reservation_repo, file_repo, *_ = _service()
    reservation_repo.get_user_for_quota_lock.return_value = SimpleNamespace(
        storage_quota_bytes=100
    )
    file_repo.get_used_bytes_by_user.return_value = 80
    reservation_repo.get_reserved_bytes_by_user.return_value = 20

    with pytest.raises(QuotaExceededError):
        service.reserve_upload(1, 2, "file.txt", 1, "127.0.0.1")

    file_repo.get_next_file_id.assert_not_called()


def test_upload_chunk_rejects_bytes_above_reservation() -> None:
    service, reservation_repo, _, _, storage, _ = _service()
    reservation_repo.get_by_id.return_value = SimpleNamespace(
        file_id=4,
        reserved_bytes=10,
        status="reserved",
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    storage.get_temp_path.return_value = "temp"
    storage.exists.return_value = True
    storage.file_size.return_value = 9

    with pytest.raises(UploadSizeMismatchError):
        service.upload_chunk(3, 1, b"too long")

    storage.write_chunk.assert_not_called()


def test_complete_upload_returns_existing_file_for_completed_retry() -> None:
    service, reservation_repo, file_repo, _, _, _ = _service()
    existing = SimpleNamespace(file_id=4)
    reservation_repo.get_by_id.return_value = SimpleNamespace(
        file_id=4, status="completed"
    )
    file_repo.get_active_file.return_value = existing

    assert service.complete_upload(3, 1, 2, "report.PDF", "127.0.0.1") is existing
    file_repo.create_file.assert_not_called()
