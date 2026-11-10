"""
Custom domain exception hierarchy for application services.
Exceptions are caught by FastAPI global exception handlers and translated into ErrorResponse payloads.
"""


class ServiceException(Exception):
    """Base exception class for all business logic errors."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class InvalidCredentialsError(ServiceException):
    def __init__(self) -> None:
        super().__init__(
            code="INVALID_CREDENTIALS",
            message="Invalid username or password.",
            status_code=401,
        )


# Alias for backward compatibility
UserCredentialsError = InvalidCredentialsError


class ForbiddenError(ServiceException):
    def __init__(self) -> None:
        super().__init__(
            code="FORBIDDEN",
            message="Admin privileges required for this action.",
            status_code=403,
        )


class TotpNotEnabledError(ServiceException):
    def __init__(self) -> None:
        super().__init__(
            code="TOTP_NOT_ENABLED",
            message="TOTP setup is incomplete for this account.",
            status_code=401,
        )


class TotpAlreadyEnabledError(ServiceException):
    def __init__(self) -> None:
        super().__init__(
            code="TOTP_ALREADY_ENABLED",
            message="TOTP 2FA is already enabled for this account.",
            status_code=400,
        )


# Alias for backward compatibility
ExistingTotpError = TotpAlreadyEnabledError


class TotpSetupExpiredError(ServiceException):
    def __init__(self) -> None:
        super().__init__(
            code="TOTP_SETUP_EXPIRED",
            message="TOTP setup token has expired.",
            status_code=400,
        )


class TotpInvalidError(ServiceException):
    def __init__(self) -> None:
        super().__init__(
            code="TOTP_INVALID",
            message="Invalid 6-digit TOTP code.",
            status_code=401,
        )


# Alias for backward compatibility
TotpVerificationError = TotpInvalidError


class InvalidTokenError(ServiceException):
    def __init__(self) -> None:
        super().__init__(
            code="INVALID_TOKEN",
            message="Invalid access or refresh token.",
            status_code=401,
        )


class TokenExpiredError(ServiceException):
    def __init__(self) -> None:
        super().__init__(
            code="TOKEN_EXPIRED",
            message="Token has expired.",
            status_code=401,
        )


class TokenReuseDetectedError(ServiceException):
    def __init__(self) -> None:
        super().__init__(
            code="TOKEN_REUSE_DETECTED",
            message="Security alert: Refresh token reuse detected. Session terminated.",
            status_code=401,
        )


class SessionExpiredError(ServiceException):
    def __init__(self) -> None:
        super().__init__(
            code="SESSION_EXPIRED",
            message="Session has ended or timed out due to inactivity.",
            status_code=401,
        )


class UserAlreadyExistsError(ServiceException):
    def __init__(self) -> None:
        super().__init__(
            code="USER_ALREADY_EXISTS",
            message="Username is already taken.",
            status_code=409,
        )


class UserNotFoundError(ServiceException):
    def __init__(self) -> None:
        super().__init__(
            code="USER_NOT_FOUND",
            message="User not found.",
            status_code=404,
        )


class UserDeletionBlockedError(ServiceException):
    def __init__(self) -> None:
        super().__init__(
            code="USER_DELETION_BLOCKED",
            message="User cannot be deleted while files or session history exists.",
            status_code=409,
        )


class InvalidQuotaError(ServiceException):
    def __init__(self) -> None:
        super().__init__(
            code="INVALID_QUOTA",
            message="New quota cannot be lower than current used + reserved storage bytes.",
            status_code=400,
        )


class QuotaExceededError(ServiceException):
    def __init__(self) -> None:
        super().__init__(
            code="QUOTA_EXCEEDED",
            message="Storage quota exceeded. Cannot reserve upload space.",
            status_code=400,
        )


class ReservationNotFoundError(ServiceException):
    def __init__(self) -> None:
        super().__init__(
            code="RESERVATION_NOT_FOUND",
            message="Upload reservation not found.",
            status_code=404,
        )


class ReservationExpiredError(ServiceException):
    def __init__(self) -> None:
        super().__init__(
            code="RESERVATION_EXPIRED",
            message="Upload reservation has expired.",
            status_code=400,
        )


class FileNotFoundError(ServiceException):
    def __init__(self) -> None:
        super().__init__(
            code="FILE_NOT_FOUND",
            message="File not found.",
            status_code=404,
        )


class FileDeletingError(ServiceException):
    def __init__(self) -> None:
        super().__init__(
            code="FILE_DELETING",
            message="File is pending deletion and cannot be processed.",
            status_code=400,
        )


class UploadSizeMismatchError(ServiceException):
    def __init__(self) -> None:
        super().__init__(
            code="UPLOAD_SIZE_MISMATCH",
            message="Actual uploaded bytes do not match the reserved size.",
            status_code=400,
        )


class StorageError(ServiceException):
    def __init__(self, message: str = "Physical storage read/write error.") -> None:
        super().__init__(
            code="STORAGE_ERROR",
            message=message,
            status_code=500,
        )
