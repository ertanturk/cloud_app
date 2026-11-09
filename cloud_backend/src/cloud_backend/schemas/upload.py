"""
Upload reservation schemas.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class UploadReservationRequest(BaseModel):
    file_name: str = Field(
        ..., min_length=1, max_length=255, description="Original file name"
    )
    file_size_bytes: int = Field(
        ..., ge=0, description="Expected complete file size in bytes"
    )


class UploadCompleteRequest(BaseModel):
    original_file_name: str = Field(
        ..., min_length=1, max_length=255, description="Original file name"
    )


class UploadReservationResponse(BaseModel):
    reservation_id: int
    file_id: int
    expires_at: datetime
