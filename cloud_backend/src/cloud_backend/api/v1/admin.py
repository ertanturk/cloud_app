"""
API router managing administrator operations: user creation, quota updates,
active session tracking, telemetry audit logs, and hardware/app performance metrics.
"""

import json

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from cloud_backend.api.v1.dependencies import (
    get_auth_service,
    get_client_ip,
    get_current_admin,
    get_current_session_id,
    get_metrics_service,
)
from cloud_backend.core.exceptions import UserNotFoundError
from cloud_backend.db.connection import get_core_db, get_telemetry_db
from cloud_backend.db.models import Users
from cloud_backend.db.repositories import (
    FileRepository,
    SessionRepository,
    TelemetryRepository,
    UploadReservationRepository,
    UserRepository,
)
from cloud_backend.schemas.admin import (
    ApplicationMetricsResponse,
    QuotaUpdateRequest,
    SessionResponse,
    SystemMetricsResponse,
    TelemetryResponse,
    UserCreateRequest,
    UserResponse,
)
from cloud_backend.services import AuthService, MetricsService

router = APIRouter(prefix="/api/v1/admin", tags=["Admin Management"])


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    payload: UserCreateRequest,
    current_admin: Users = Depends(get_current_admin),  # noqa
    session_id: int = Depends(get_current_session_id),
    client_ip: str = Depends(get_client_ip),
    auth_service: AuthService = Depends(get_auth_service),  # noqa
) -> UserResponse:
    """Creates a new standard user account. Requires admin privileges."""
    new_user = auth_service.create_user(
        admin=current_admin,
        admin_session_id=session_id,
        client_ip=client_ip,
        username=payload.username,
        initial_password=payload.initial_password,
    )
    return UserResponse.model_validate(new_user)


@router.get("/users", response_model=list[UserResponse])
def list_users(
    current_admin: Users = Depends(get_current_admin),  # noqa
    core_db: Session = Depends(get_core_db),  # noqa
) -> list[UserResponse]:
    """Retrieves all registered user accounts in the system."""
    user_repo = UserRepository(core_db)
    users = user_repo.list_users()
    return [UserResponse.model_validate(u) for u in users]


@router.put("/users/{user_id}/quota", response_model=UserResponse)
def update_user_quota(
    user_id: int,
    payload: QuotaUpdateRequest,
    current_admin: Users = Depends(get_current_admin),  # noqa
    core_db: Session = Depends(get_core_db),  # noqa
) -> UserResponse:
    """Updates the storage quota in bytes for a specific user."""
    user_repo = UserRepository(core_db)
    used = FileRepository(core_db).get_used_bytes_by_user(user_id)
    reserved = UploadReservationRepository(core_db).get_reserved_bytes_by_user(user_id)
    if payload.quota_bytes < used + reserved:
        from cloud_backend.core.exceptions import InvalidQuotaError

        raise InvalidQuotaError()
    updated_user = user_repo.update_quota(
        user_id=user_id,
        new_quota_bytes=payload.quota_bytes,
    )
    if updated_user is None:
        raise UserNotFoundError()

    return UserResponse.model_validate(updated_user)


@router.get("/sessions", response_model=list[SessionResponse])
def list_active_sessions(
    current_admin: Users = Depends(get_current_admin),  # noqa
    core_db: Session = Depends(get_core_db),  # noqa
) -> list[SessionResponse]:
    """Lists all currently active user sessions."""
    session_repo = SessionRepository(core_db)
    sessions = session_repo.list_active_sessions()
    users = {u.user_id: u.username for u in UserRepository(core_db).list_users()}
    return [
        SessionResponse(
            session_id=s.session_id,
            user_id=s.user_id,
            username=users.get(s.user_id, ""),
            client_ip=s.client_ip,
            started_at=s.started_at,
            last_activity_at=s.last_activity_at,
        )
        for s in sessions
    ]


@router.get("/telemetry", response_model=list[TelemetryResponse])
def get_telemetry_logs(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    event_type: str | None = Query(default=None, max_length=50),
    user_id: int | None = Query(default=None, ge=1),
    current_admin: Users = Depends(get_current_admin),  # noqa
    telemetry_db: Session = Depends(get_telemetry_db),  # noqa
) -> list[TelemetryResponse]:
    """Retrieves recent audit logging telemetry events."""
    telemetry_repo = TelemetryRepository(telemetry_db)
    events_with_types = telemetry_repo.list_events(
        limit=limit, offset=offset, event_type_name=event_type, user_id=user_id
    )

    response = []
    for event, event_type_name in events_with_types:
        # JSON string verisini dict'e geri ayrıştır
        parsed_data = None
        if event.telemetry_data:
            try:
                parsed_data = json.loads(event.telemetry_data)
            except json.JSONDecodeError:
                parsed_data = event.telemetry_data

        response.append(
            TelemetryResponse(
                event_id=event.event_id,
                event_type=event_type_name,
                user_id=event.user_id,
                session_id=event.session_id,
                client_ip=event.client_ip,
                telemetry_data=parsed_data,
                event_time=event.event_time,
            )
        )

    return response


@router.get("/metrics/system", response_model=SystemMetricsResponse)
def get_system_metrics(
    current_admin: Users = Depends(get_current_admin),  # noqa
    metrics_service: MetricsService = Depends(get_metrics_service),  # noqa
) -> SystemMetricsResponse:
    """Returns real-time host hardware usage metrics (CPU, RAM, Disk, Network speed)."""
    return metrics_service.get_system_metrics()


@router.get("/metrics/application", response_model=ApplicationMetricsResponse)
def get_application_metrics(
    current_admin: Users = Depends(get_current_admin),  # noqa
    metrics_service: MetricsService = Depends(get_metrics_service),  # noqa
) -> ApplicationMetricsResponse:
    """Returns application-level operational statistics (active uploads, users, storage usage)."""
    return metrics_service.get_application_metrics()
