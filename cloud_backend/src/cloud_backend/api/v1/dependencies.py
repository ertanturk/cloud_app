"""
FastAPI Dependency Injection providers for database sessions, repositories,
business services, request context, and JWT authentication flows.
"""

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from cloud_backend.core.exceptions import (
    ForbiddenError,
    InvalidTokenError,
    SessionExpiredError,
)
from cloud_backend.core.security import verify_access_token
from cloud_backend.db.connection import get_core_db, get_telemetry_db
from cloud_backend.db.models import Users
from cloud_backend.db.repositories import (
    FileRepository,
    RefreshTokenRepository,
    SessionRepository,
    TelemetryRepository,
    UploadReservationRepository,
    UserRepository,
)
from cloud_backend.services import (
    AuthService,
    FileService,
    MetricsService,
    StorageService,
    UploadService,
)

oauth2_scheme = HTTPBearer()


def get_auth_service(
    core_db: Session = Depends(get_core_db),  # noqa
    telemetry_db: Session = Depends(get_telemetry_db),  # noqa
) -> AuthService:
    """Provides an initialized AuthService instance with its required repositories."""
    return AuthService(
        user_repo=UserRepository(core_db),
        session_repo=SessionRepository(core_db),
        refresh_token_repo=RefreshTokenRepository(core_db),
        telemetry_repo=TelemetryRepository(telemetry_db),
    )


def get_storage_service() -> StorageService:
    """Provides a StorageService instance for disk I/O operations."""
    from cloud_backend.core.config import get_config

    return StorageService(get_config().STORAGE_BASE_PATH)


def get_file_service(
    core_db: Session = Depends(get_core_db),  # noqa
    telemetry_db: Session = Depends(get_telemetry_db),  # noqa
) -> FileService:
    """Provides an initialized FileService instance."""
    return FileService(
        file_repo=FileRepository(core_db),
        reservation_repo=UploadReservationRepository(core_db),
        user_repo=UserRepository(core_db),
        storage_service=get_storage_service(),
        telemetry_repo=TelemetryRepository(telemetry_db),
    )


def get_upload_service(
    core_db: Session = Depends(get_core_db),  # noqa
    telemetry_db: Session = Depends(get_telemetry_db),  # noqa
) -> UploadService:
    """Provides an initialized UploadService instance."""
    return UploadService(
        reservation_repo=UploadReservationRepository(core_db),
        file_repo=FileRepository(core_db),
        user_repo=UserRepository(core_db),
        storage_service=get_storage_service(),
        telemetry_repo=TelemetryRepository(telemetry_db),
    )


def get_metrics_service(
    core_db: Session = Depends(get_core_db),  # noqa
) -> MetricsService:
    """Provides an initialized MetricsService instance."""
    return MetricsService(
        user_repo=UserRepository(core_db),
        session_repo=SessionRepository(core_db),
        file_repo=FileRepository(core_db),
        reservation_repo=UploadReservationRepository(core_db),
    )


def get_client_ip(request: Request) -> str:
    """Extracts client IP address from request headers or connection fallback."""
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


def get_current_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),  # noqa
) -> dict:
    """Decodes and validates the Bearer JWT token structure."""
    token = credentials.credentials
    payload = verify_access_token(token)

    if not payload or "sub" not in payload or "session_id" not in payload:
        raise InvalidTokenError()

    return payload


def get_current_user(
    payload: dict = Depends(get_current_token_payload),  # noqa
    core_db: Session = Depends(get_core_db),  # noqa
) -> Users:
    """
    Authenticates the current user via JWT access token and active session check.
    Returns the Users ORM model instance if valid.
    """
    try:
        user_id = int(payload["sub"])
        session_id = int(payload["session_id"])
    except (ValueError, TypeError):
        raise InvalidTokenError()

    session_repo = SessionRepository(core_db)
    session = session_repo.get_active_session(session_id)
    if not session or session.user_id != user_id:
        raise SessionExpiredError()

    user_repo = UserRepository(core_db)
    user = user_repo.get_by_id(user_id)
    if not user:
        raise InvalidTokenError()

    return user


def get_current_session_id(
    payload: dict = Depends(get_current_token_payload),  # noqa
) -> int:
    """Extracts the verified active session_id from the JWT payload."""
    return int(payload["session_id"])


def get_current_admin(
    current_user: Users = Depends(get_current_user),  # noqa
) -> Users:
    """Enforces admin role verification on top of standard authentication."""
    if current_user.role != "admin":
        raise ForbiddenError()
    return current_user
