# ruff: noqa: B008

from fastapi import APIRouter, Depends, status

from cloud_backend.api.v1.dependencies import get_auth_service, get_client_ip
from cloud_backend.schemas.admin import UserResponse
from cloud_backend.schemas.auth import (
    HeartbeatRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    RefreshRequest,
    RefreshResponse,
    TotpConfirmRequest,
    TotpSetupRequest,
    TotpSetupResponse,
)
from cloud_backend.services import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
    client_ip: str = Depends(get_client_ip),
) -> LoginResponse:
    access_token, refresh_token, user = auth_service.login(
        username=payload.username,
        password=payload.password,
        totp_code=payload.totp_code,
        client_ip=client_ip,
    )
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",  # nosec B106
        expires_in=600,
        user=UserResponse(
            user_id=user.user_id,
            username=user.username,
            role=user.role,
            storage_quota_bytes=user.storage_quota_bytes,
            created_at=user.created_at,
        ),
    )


@router.post("/totp/setup", response_model=TotpSetupResponse)
def setup_totp(
    payload: TotpSetupRequest,
    auth_service: AuthService = Depends(get_auth_service),
    client_ip: str = Depends(get_client_ip),
) -> TotpSetupResponse:
    provisioning_uri, setup_token = auth_service.start_totp_setup(
        username=payload.username, password=payload.password, client_ip=client_ip
    )
    return TotpSetupResponse(provisioning_uri=provisioning_uri, setup_token=setup_token)


@router.post("/totp/confirm", status_code=status.HTTP_204_NO_CONTENT)
def confirm_totp(
    payload: TotpConfirmRequest,
    auth_service: AuthService = Depends(get_auth_service),
    client_ip: str = Depends(get_client_ip),
) -> None:
    auth_service.confirm_totp_setup(
        setup_token=payload.setup_token,
        totp_code=payload.totp_code,
        client_ip=client_ip,
    )


@router.post("/refresh", response_model=RefreshResponse)
def refresh(
    payload: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
    client_ip: str = Depends(get_client_ip),
) -> RefreshResponse:
    access_token, new_refresh_token = auth_service.refresh_tokens(
        raw_refresh_token=payload.raw_refresh_token, client_ip=client_ip
    )
    return RefreshResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="Bearer",  # nosec B106
        expires_in=600,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: LogoutRequest,
    auth_service: AuthService = Depends(get_auth_service),
    client_ip: str = Depends(get_client_ip),
) -> None:
    auth_service.logout(
        raw_refresh_token=payload.raw_refresh_token, client_ip=client_ip
    )


@router.post("/heartbeat", status_code=status.HTTP_204_NO_CONTENT)
def heartbeat(
    payload: HeartbeatRequest,
    auth_service: AuthService = Depends(get_auth_service),
    client_ip: str = Depends(get_client_ip),
) -> None:
    auth_service.heartbeat(
        raw_refresh_token=payload.raw_refresh_token, client_ip=client_ip
    )
