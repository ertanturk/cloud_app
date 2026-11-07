"""
File metadata and user storage usage schemas.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FileItemResponse(BaseModel):
    file_id: int
    file_name: str = Field(..., validation_alias="original_file_name")
    file_size_bytes: int
    extension: str | None = Field(default=None, validation_alias="file_extension")
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class StorageResponse(BaseModel):
    quota_bytes: int = Field(..., ge=0)
    used_bytes: int = Field(..., ge=0)
    reserved_bytes: int = Field(..., ge=0)
    available_bytes: int = Field(..., ge=0)
