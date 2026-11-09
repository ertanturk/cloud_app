from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import FileResponse

from cloud_backend.api.v1.dependencies import (
    get_client_ip,
    get_current_session_id,
    get_current_user,
    get_file_service,
)
from cloud_backend.db.models import Users
from cloud_backend.schemas.file import FileItemResponse
from cloud_backend.services import FileService

router = APIRouter(prefix="/api/v1/files", tags=["Files"])


@router.get("", response_model=list[FileItemResponse])
def get_files(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    current_user: Users = Depends(get_current_user),  # noqa
    file_service: FileService = Depends(get_file_service),  # noqa
) -> list[FileItemResponse]:
    """Retrieves all active file records owned by the authenticated user."""
    return file_service.list_user_files(
        current_user.user_id, limit=limit, offset=offset
    )


@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    current_user: Users = Depends(get_current_user),  # noqa
    session_id: int = Depends(get_current_session_id),
    client_ip: str = Depends(get_client_ip),
    file_service: FileService = Depends(get_file_service),  # noqa
) -> FileResponse:
    """Streams physical file download for the specified file_id."""
    file_record, physical_path = file_service.get_file_for_download(
        file_id=file_id,
        user_id=current_user.user_id,
        session_id=session_id,
        client_ip=client_ip,
    )
    return FileResponse(
        path=physical_path,
        filename=file_record.original_file_name,
        media_type="application/octet-stream",
        headers={
            "Content-Length": str(file_record.file_size_bytes),
            "X-Content-SHA256": file_record.checksum_sha256.hex(),
        },
    )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    file_id: int,
    current_user: Users = Depends(get_current_user),  # noqa
    client_ip: str = Depends(get_client_ip),
    session_id: int = Depends(get_current_session_id),
    file_service: FileService = Depends(get_file_service),  # noqa
) -> None:
    """Executes secure deletion for the specified file_id."""
    file_service.delete_file(
        file_id=file_id,
        user_id=current_user.user_id,
        session_id=session_id,
        client_ip=client_ip,
    )
