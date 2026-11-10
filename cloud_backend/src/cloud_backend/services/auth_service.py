"""Service handling user authentication and session management."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import pyotp

from cloud_backend.core.exceptions import (
    ExistingTotpError,
    ForbiddenError,
    InvalidTokenError,
    SessionExpiredError,
    TokenReuseDetectedError,
    TotpNotEnabledError,
    TotpSetupExpiredError,
    TotpVerificationError,
    UserAlreadyExistsError,
    UserCredentialsError,
)
from cloud_backend.core.security import (
    create_access_token,
    decrypt_totp_secret,
    encrypt_totp_secret,
    hash_password,
    verify_password,
)
from cloud_backend.db.models.core import Users
from cloud_backend.db.repositories import (
    RefreshTokenRepository,
    SessionRepository,
    TelemetryRepository,
    UserRepository,
)


def _as_utc(value: datetime) -> datetime:
    """Treat SQL Server's timezone-naive UTC timestamps as UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        session_repo: SessionRepository,
        refresh_token_repo: RefreshTokenRepository,
        telemetry_repo: TelemetryRepository,
    ):
        self.user_repo = user_repo
        self.session_repo = session_repo
        self.refresh_token_repo = refresh_token_repo
        self.telemetry_repo = telemetry_repo

    def create_user(
        self,
        admin: Users,
        admin_session_id: int,
        client_ip: str,
        username: str,
        initial_password: str,
    ) -> Users:
        """Creates a new user record with default 'user' role. Requires admin privileges."""
        if admin.role != "admin":
            raise ForbiddenError()

        if self.user_repo.get_by_username(username) is not None:
            raise UserAlreadyExistsError()

        password_hash, password_salt = hash_password(initial_password)
        password_hash_version = 1

        new_user = self.user_repo.create_user_with_secrets(
            username=username,
            password_hash=password_hash,
            password_hash_version=password_hash_version,
            password_salt=password_salt,
            role="user",
        )
        self.telemetry_repo.log_event(
            event_type_name="user.created",
            client_ip=client_ip,
            user_id=admin.user_id,
            session_id=admin_session_id,
            telemetry_data={
                "created_user_id": new_user.user_id,
                "created_username": new_user.username,
            },
        )
        return new_user

    def start_totp_setup(
        self, username: str, password: str, client_ip: str
    ) -> tuple[str, str]:
        """
        Starts TOTP 2FA setup for a user.
        Generates a Base32 secret and setup token, encrypts/hashes them,
        persists pending state via user_repo, and logs telemetry.

        Returns:
            tuple[str, str]: (provisioning_uri, setup_token)
        """
        user = self.user_repo.get_by_username(username)
        if user is None:
            raise UserCredentialsError()

        user_secret = self.user_repo.get_user_secrets(user.user_id)
        if user_secret is None:
            raise UserCredentialsError()

        if not verify_password(password, user_secret.password_salt, user.password_hash):
            raise UserCredentialsError()

        if user_secret.totp_enabled:
            raise ExistingTotpError()

        pending_secret = user_secret.pending_totp_secret
        pending_expires_at = user_secret.totp_setup_expires_at
        if (
            pending_secret is not None
            and pending_expires_at is not None
            and _as_utc(pending_expires_at) >= datetime.now(UTC)
        ):
            totp_secret = decrypt_totp_secret(pending_secret.decode("utf-8"))
        else:
            totp_secret = pyotp.random_base32()
        raw_setup_token = secrets.token_urlsafe(32)

        encrypted_secret_str = encrypt_totp_secret(totp_secret)
        encrypted_secret_bytes = encrypted_secret_str.encode("utf-8")
        setup_token_hash = hashlib.sha256(raw_setup_token.encode("utf-8")).digest()

        expires_at = datetime.now(UTC) + timedelta(minutes=20)

        self.user_repo.save_pending_totp(
            user_id=user.user_id,
            pending_totp_secret=encrypted_secret_bytes,
            totp_setup_token_hash=setup_token_hash,
            totp_setup_expires_at=expires_at,
        )

        totp = pyotp.TOTP(totp_secret)
        provisioning_uri = totp.provisioning_uri(
            name=username, issuer_name="CloudBackend"
        )

        self.telemetry_repo.log_event(
            event_type_name="auth.totp.setup.started",
            client_ip=client_ip,
            user_id=user.user_id,
        )

        return provisioning_uri, raw_setup_token

    def confirm_totp_setup(
        self, setup_token: str, totp_code: str, client_ip: str
    ) -> None:
        """
        Confirms TOTP setup using the setup token and the first valid 6-digit TOTP code.
        Decrypts pending secret, verifies with pyotp, completes setup in DB, and logs telemetry.
        """
        setup_token_hash = hashlib.sha256(setup_token.encode("utf-8")).digest()
        user_secret = self.user_repo.get_by_setup_token(setup_token_hash)
        if user_secret is None or user_secret.pending_totp_secret is None:
            raise InvalidTokenError()

        expires_at = user_secret.totp_setup_expires_at
        if expires_at is None or _as_utc(expires_at) < datetime.now(UTC):
            raise TotpSetupExpiredError()

        encrypted_secret_str = user_secret.pending_totp_secret.decode("utf-8")
        decrypted_totp_secret = decrypt_totp_secret(encrypted_secret_str)

        totp = pyotp.TOTP(decrypted_totp_secret)
        if not totp.verify(totp_code):
            raise TotpVerificationError()

        self.user_repo.confirm_totp(user_id=user_secret.user_id)

        self.telemetry_repo.log_event(
            event_type_name="auth.totp.setup.completed",
            client_ip=client_ip,
            user_id=user_secret.user_id,
        )

    def login(
        self, username: str, password: str, totp_code: str, client_ip: str
    ) -> tuple[str, str, Users]:
        """
        Authenticates user credentials, validates 2FA TOTP code, creates an active session,
        issues JWT Access Token and persistent Refresh Token, and logs telemetry.
        """
        user = self.user_repo.get_by_username(username)
        if user is None:
            self.telemetry_repo.log_event(
                event_type_name="auth.login.failed",
                client_ip=client_ip,
                user_id=None,
            )
            raise UserCredentialsError()

        user_secret = self.user_repo.get_user_secrets(user.user_id)
        if user_secret is None:
            self.telemetry_repo.log_event(
                event_type_name="auth.login.failed",
                client_ip=client_ip,
                user_id=user.user_id,
            )
            raise UserCredentialsError()

        if not verify_password(password, user_secret.password_salt, user.password_hash):
            self.telemetry_repo.log_event(
                event_type_name="auth.login.failed",
                client_ip=client_ip,
                user_id=user.user_id,
            )
            raise UserCredentialsError()

        if not user_secret.totp_enabled or user_secret.encrypted_totp_secret is None:
            self.telemetry_repo.log_event(
                event_type_name="auth.login.failed",
                client_ip=client_ip,
                user_id=user.user_id,
            )
            raise TotpNotEnabledError()

        encrypted_secret_str = user_secret.encrypted_totp_secret.decode("utf-8")
        decrypted_totp_secret = decrypt_totp_secret(encrypted_secret_str)
        totp = pyotp.TOTP(decrypted_totp_secret)

        if not totp.verify(totp_code):
            self.telemetry_repo.log_event(
                event_type_name="auth.login.failed",
                client_ip=client_ip,
                user_id=user.user_id,
            )
            raise TotpVerificationError()

        session = self.session_repo.create_session(
            user_id=user.user_id, client_ip=client_ip
        )

        access_token = create_access_token(
            data={
                "sub": str(user.user_id),
                "session_id": session.session_id,
                "role": user.role,
            }
        )

        raw_refresh_token = secrets.token_urlsafe(32)
        refresh_token_hash = hashlib.sha256(raw_refresh_token.encode("utf-8")).digest()
        refresh_token_expires_at = datetime.now(UTC) + timedelta(days=30)

        self.refresh_token_repo.create_token(
            session_id=session.session_id,
            token_hash=refresh_token_hash,
            expires_at=refresh_token_expires_at,
        )

        self.telemetry_repo.log_event(
            event_type_name="auth.login.success",
            client_ip=client_ip,
            user_id=user.user_id,
            session_id=session.session_id,
        )

        return access_token, raw_refresh_token, user

    def refresh_tokens(self, raw_refresh_token: str, client_ip: str) -> tuple[str, str]:
        """
        Rotates an existing refresh token, validates session activity and token expiration,
        issues a new JWT access token and rotated refresh token, and logs telemetry.
        """
        hashed_refresh_token = hashlib.sha256(
            raw_refresh_token.encode("utf-8")
        ).digest()
        token = self.refresh_token_repo.get_by_hash(
            token_hash=hashed_refresh_token, lock=True
        )
        if not token:
            raise InvalidTokenError()

        if token.used_at is not None or token.replaced_by_token_id is not None:
            self.refresh_token_repo.revoke_all_for_session(session_id=token.session_id)
            session = self.session_repo.get_active_session(session_id=token.session_id)
            user_id = session.user_id if session else None

            self.session_repo.end_session(session_id=token.session_id)

            self.telemetry_repo.log_event(
                event_type_name="auth.refresh.reuse_detected",
                client_ip=client_ip,
                user_id=user_id,
                session_id=token.session_id,
            )
            raise TokenReuseDetectedError()

        now = datetime.now(UTC)
        if token.revoked_at is not None:
            raise InvalidTokenError()

        if _as_utc(token.expires_at) < now:
            raise InvalidTokenError()

        session = self.session_repo.get_active_session(session_id=token.session_id)
        if session is None:
            raise SessionExpiredError()

        user = self.user_repo.get_by_id(session.user_id)
        if user is None:
            raise InvalidTokenError()

        self.session_repo.update_last_activity(session_id=session.session_id)

        new_raw_refresh_token = secrets.token_urlsafe(32)
        new_refresh_token_hash = hashlib.sha256(
            new_raw_refresh_token.encode("utf-8")
        ).digest()
        new_expires_at = now + timedelta(days=30)

        self.refresh_token_repo.rotate_token(
            old_token=token,
            new_token_hash=new_refresh_token_hash,
            new_expires_at=new_expires_at,
        )

        access_token = create_access_token(
            data={
                "sub": str(user.user_id),
                "session_id": session.session_id,
                "role": user.role,
            }
        )

        self.telemetry_repo.log_event(
            event_type_name="auth.refresh.rotated",
            client_ip=client_ip,
            user_id=user.user_id,
            session_id=session.session_id,
        )

        return access_token, new_raw_refresh_token

    def logout(self, raw_refresh_token: str, client_ip: str) -> None:
        """
        Logs out the user by terminating their active session and revoking all
        associated refresh tokens. Operates idempotently to ensure clean logout state.
        """
        if not raw_refresh_token:
            return

        hashed_token = hashlib.sha256(raw_refresh_token.encode("utf-8")).digest()
        token = self.refresh_token_repo.get_by_hash(token_hash=hashed_token)

        if token is None:
            return

        session = self.session_repo.get_active_session(session_id=token.session_id)
        user_id = session.user_id if session else None

        self.session_repo.end_session(session_id=token.session_id)
        self.refresh_token_repo.revoke_all_for_session(session_id=token.session_id)

        self.telemetry_repo.log_event(
            event_type_name="auth.logout",
            client_ip=client_ip,
            user_id=user_id,
            session_id=token.session_id,
        )

    def heartbeat(self, raw_refresh_token: str, client_ip: str) -> None:
        """
        Verifies the validity of the refresh token and extends the session if valid.
        """
        if not raw_refresh_token:
            return

        hashed_token = hashlib.sha256(raw_refresh_token.encode("utf-8")).digest()
        token = self.refresh_token_repo.get_by_hash(token_hash=hashed_token)

        if token is None:
            return

        session = self.session_repo.get_active_session(session_id=token.session_id)

        if session is None:
            return

        self.session_repo.update_last_activity(session_id=token.session_id)

        self.telemetry_repo.log_event(
            event_type_name="auth.heartbeat",
            client_ip=client_ip,
            user_id=session.user_id,
            session_id=token.session_id,
        )
