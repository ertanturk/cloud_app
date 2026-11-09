class ServiceException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ForbiddenError(ServiceException):
    def __init__(self):
        super().__init__(
            code="FORBIDDEN",
            message="Forbidden.",
            status_code=403,
        )


class UserAlreadyExistsError(ServiceException):
    def __init__(self):
        super().__init__(
            code="EXISTING_USER",
            message="User already exists.",
            status_code=401,
        )


class UserCredentialsError(ServiceException):
    def __init__(self):
        super().__init__(
            code="INVALID_CREDENTIALS",
            message="Invalid credentials.",
            status_code=401,
        )


class ExistingTotpError(ServiceException):
    def __init__(self):
        super().__init__(
            code="EXISTING_TOTP",
            message="TOTP already exists.",
            status_code=401,
        )


class TotpNotEnabledError(ServiceException):
    def __init__(self):
        super().__init__(
            code="TOTP_NOT_ENABLED",
            message="TOTP is not enabled.",
            status_code=401,
        )


class TotpSetupExpiredError(ServiceException):
    def __init__(self):
        super().__init__(
            code="TOTP_SETUP_EXPIRED",
            message="TOTP setup has expired.",
            status_code=401,
        )


class InvalidTokenError(ServiceException):
    def __init__(self):
        super().__init__(
            code="INVALID_TOKEN",
            message="Invalid token.",
            status_code=401,
        )


class TotpVerificationError(ServiceException):
    def __init__(self):
        super().__init__(
            code="TOTP_VERIFICATION_FAILED",
            message="TOTP verification failed.",
            status_code=401,
        )


class RefreshTokenNotFoundError(ServiceException):
    def __init__(self):
        super().__init__(
            code="REFRESH_TOKEN_NOT_FOUND",
            message="Refresh token not found.",
            status_code=401,
        )


class TokenReuseDetectedError(ServiceException):
    def __init__(self):
        super().__init__(
            code="TOKEN_REUSE_DETECTED",
            message="Token reuse detected.",
            status_code=401,
        )


class SessionExpiredError(ServiceException):
    def __init__(self):
        super().__init__(
            code="SESSION_EXPIRED",
            message="Session expired.",
            status_code=401,
        )
