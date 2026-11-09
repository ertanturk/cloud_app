from fastapi import APIRouter, Depends, Request, status

from cloud_backend.api.v1.dependencies import (
    get_client_ip,
    get_current_session_id,
    get_current_user,
    get_upload_service,
)
from cloud_backend.db.models import Users
from cloud_backend.schemas.file import FileItemResponse
from cloud_backend.schemas.upload import (
    UploadCompleteRequest,
    UploadReservationRequest,
    UploadReservationResponse,
)
from cloud_backend.services import UploadService

router = APIRouter(prefix="/api/v1/uploads", tags=["Uploads"])


@router.post(
    "", response_model=UploadReservationResponse, status_code=status.HTTP_201_CREATED
)
def reserve_upload(
    payload: UploadReservationRequest,
    current_user: Users = Depends(get_current_user),  # noqa
    session_id: int = Depends(get_current_session_id),
    client_ip: str = Depends(get_client_ip),
    upload_service: UploadService = Depends(get_upload_service),  # noqa
) -> UploadReservationResponse:
    """
    Reserves storage quota space and initiates a new file upload transaction.
    Endpoint: POST /api/v1/uploads
    """
    reservation = upload_service.reserve_upload(
        user_id=current_user.user_id,
        session_id=session_id,
        file_name=payload.file_name,
        file_size_bytes=payload.file_size_bytes,
        client_ip=client_ip,
    )
    return UploadReservationResponse(
        reservation_id=reservation.reservation_id,
        file_id=reservation.file_id,
        expires_at=reservation.expires_at,
    )


@router.put("/{reservation_id}/content", status_code=status.HTTP_204_NO_CONTENT)
async def upload_chunk(
    reservation_id: int,
    request: Request,
    current_user: Users = Depends(get_current_user),  # noqa
    upload_service: UploadService = Depends(get_upload_service),  # noqa
) -> None:
    """
    Streams raw binary chunk data into temporary storage for the active reservation.
    Endpoint: PUT /api/v1/uploads/{id}/content
    """
    async for chunk in request.stream():
        if chunk:
            upload_service.upload_chunk(
                reservation_id=reservation_id,
                user_id=current_user.user_id,
                chunk=chunk,
            )


@router.post("/{reservation_id}/complete", response_model=FileItemResponse)
def complete_upload(
    reservation_id: int,
    payload: UploadCompleteRequest,
    current_user: Users = Depends(get_current_user),  # noqa
    session_id: int = Depends(get_current_session_id),
    client_ip: str = Depends(get_client_ip),
    upload_service: UploadService = Depends(get_upload_service),  # noqa
) -> FileItemResponse:
    """
    Verifies SHA-256 and byte-length integrity, moves file to final path, and creates active file.
    Endpoint: POST /api/v1/uploads/{id}/complete
    """
    file_record = upload_service.complete_upload(
        reservation_id=reservation_id,
        user_id=current_user.user_id,
        session_id=session_id,
        original_file_name=payload.original_file_name,
        client_ip=client_ip,
    )
    return FileItemResponse(
        file_id=file_record.file_id,
        original_file_name=file_record.original_file_name,
        file_size_bytes=file_record.file_size_bytes,
        file_extension=file_record.file_extension,
        checksum_sha256=file_record.checksum_sha256.hex()
        if isinstance(file_record.checksum_sha256, bytes)
        else file_record.checksum_sha256,
        uploaded_at=file_record.uploaded_at,
    )


@router.delete("/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_upload(
    reservation_id: int,
    current_user: Users = Depends(get_current_user),  # noqa
    client_ip: str = Depends(get_client_ip),
    session_id: int = Depends(get_current_session_id),
    upload_service: UploadService = Depends(get_upload_service),  # noqa
) -> None:
    """
    Cancels an ongoing upload reservation and purges temporary disk artifacts.
    Endpoint: DELETE /api/v1/uploads/{id}
    """
    upload_service.cancel_upload(
        reservation_id=reservation_id,
        user_id=current_user.user_id,
        session_id=session_id,
        client_ip=client_ip,
    )
