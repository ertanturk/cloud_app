"""
Authentication and 2FA TOTP schemas.
"""

from pydantic import BaseModel, Field

from cloud_backend.schemas.admin import UserResponse


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)
    totp_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit TOTP code",
    )


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 600
    user: UserResponse


class TotpSetupResponse(BaseModel):
    provisioning_uri: str
    setup_token: str


class TotpConfirmRequest(BaseModel):
    setup_token: str
    totp_code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class RefreshRequest(BaseModel):
    refresh_token: str
