"""
Admin management, telemetry, and system metric schemas.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UserCreateRequest(BaseModel):
    username: str = Field(
        ..., min_length=3, max_length=100, description="New user's username"
    )
    initial_password: str = Field(
        ..., min_length=8, description="Initial password set by admin"
    )


class UserResponse(BaseModel):
    user_id: int
    username: str
    role: str
    storage_quota_bytes: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuotaUpdateRequest(BaseModel):
    quota_bytes: int = Field(..., gt=0, description="New storage quota in bytes")


class SessionResponse(BaseModel):
    session_id: int
    user_id: int
    username: str
    client_ip: str
    started_at: datetime
    last_activity_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TelemetryResponse(BaseModel):
    event_id: int
    event_type: str
    user_id: int | None = None
    session_id: int | None = None
    client_ip: str
    telemetry_data: dict[str, Any] | str | None = None
    event_time: datetime

    model_config = ConfigDict(from_attributes=True)


class SystemMetricsResponse(BaseModel):
    cpu_usage_percent: float = Field(..., ge=0.0, le=100.0)
    ram_used_bytes: int = Field(..., ge=0)
    ram_total_bytes: int = Field(..., ge=0)
    ram_usage_percent: float = Field(..., ge=0.0, le=100.0)
    disk_used_bytes: int = Field(..., ge=0)
    disk_total_bytes: int = Field(..., ge=0)
    disk_usage_percent: float = Field(..., ge=0.0, le=100.0)
    network_bytes_recv_per_sec: float = Field(..., ge=0.0)
    network_bytes_sent_per_sec: float = Field(..., ge=0.0)


class ApplicationMetricsResponse(BaseModel):
    active_sessions: int = Field(..., ge=0)
    active_uploads: int = Field(..., ge=0)
    total_users: int = Field(..., ge=0)
    total_files: int = Field(..., ge=0)
    total_storage_used_bytes: int = Field(..., ge=0)
