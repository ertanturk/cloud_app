from fastapi import APIRouter, Depends

from cloud_backend.api.v1.dependencies import (
    get_current_user,
    get_file_service,
)
from cloud_backend.db.models import Users
from cloud_backend.schemas.file import StorageResponse
from cloud_backend.services import FileService

router = APIRouter(prefix="/api/v1/storage", tags=["Storage"])


@router.get("", response_model=StorageResponse)
def get_storage_info(
    current_user: Users = Depends(get_current_user),  # noqa
    file_service: FileService = Depends(get_file_service),  # noqa
) -> StorageResponse:
    """Returns storage quota utilization, reserved space, and remaining capacity."""
    return file_service.get_storage_info(current_user.user_id)
