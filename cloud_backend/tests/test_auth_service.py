from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pyotp
import pytest
from cloud_backend.core.exceptions import (
    ForbiddenError,
    TokenReuseDetectedError,
    TotpNotEnabledError,
    UserCredentialsError,
)
from cloud_backend.core.security import encrypt_totp_secret, hash_password
from cloud_backend.services.auth_service import AuthService


def _service() -> tuple[AuthService, Mock, Mock, Mock, Mock]:
    user_repo = Mock()
    session_repo = Mock()
    refresh_repo = Mock()
    telemetry_repo = Mock()
    return (
        AuthService(user_repo, session_repo, refresh_repo, telemetry_repo),
        user_repo,
        session_repo,
        refresh_repo,
        telemetry_repo,
    )


def test_create_user_requires_admin() -> None:
    service, *_ = _service()
    admin = SimpleNamespace(role="user", user_id=1)

    with pytest.raises(ForbiddenError):
        service.create_user(admin, 3, "127.0.0.1", "new-user", "password123")


def test_create_user_hashes_password_and_logs_event() -> None:
    service, user_repo, _, _, telemetry_repo = _service()
    admin = SimpleNamespace(role="admin", user_id=9)
    created = SimpleNamespace(user_id=4, username="new-user")
    user_repo.get_by_username.return_value = None
    user_repo.create_user_with_secrets.return_value = created

    result = service.create_user(admin, 3, "127.0.0.1", "new-user", "password123")

    assert result is created
    args = user_repo.create_user_with_secrets.call_args.kwargs
    assert args["role"] == "user"
    assert len(args["password_hash"]) == 32
    assert len(args["password_salt"]) == 16
    telemetry_repo.log_event.assert_called_once()


def test_login_rejects_unknown_user_and_logs_failure() -> None:
    service, user_repo, _, _, telemetry_repo = _service()
    user_repo.get_by_username.return_value = None

    with pytest.raises(UserCredentialsError):
        service.login("missing", "password", "123456", "127.0.0.1")

    telemetry_repo.log_event.assert_called_once_with(
        event_type_name="auth.login.failed",
        client_ip="127.0.0.1",
        user_id=None,
    )


def test_login_rejects_user_without_totp() -> None:
    service, user_repo, _, _, telemetry_repo = _service()
    password_hash, salt = hash_password("password123")
    user_repo.get_by_username.return_value = SimpleNamespace(
        user_id=2, username="user", password_hash=password_hash, role="user"
    )
    user_repo.get_user_secrets.return_value = SimpleNamespace(
        password_salt=salt, totp_enabled=False, encrypted_totp_secret=None
    )

    with pytest.raises(TotpNotEnabledError):
        service.login("user", "password123", "123456", "127.0.0.1")

    assert telemetry_repo.log_event.call_args.kwargs["user_id"] == 2


def test_login_issues_access_and_refresh_tokens() -> None:
    service, user_repo, session_repo, refresh_repo, telemetry_repo = _service()
    secret = pyotp.random_base32()
    password_hash, salt = hash_password("password123")
    user = SimpleNamespace(
        user_id=2, username="user", password_hash=password_hash, role="user"
    )
    user_repo.get_by_username.return_value = user
    user_repo.get_user_secrets.return_value = SimpleNamespace(
        password_salt=salt,
        totp_enabled=True,
        encrypted_totp_secret=encrypt_totp_secret(secret).encode(),
    )
    session_repo.create_session.return_value = SimpleNamespace(session_id=8)

    access, refresh, result = service.login(
        "user", "password123", pyotp.TOTP(secret).now(), "127.0.0.1"
    )

    assert access
    assert refresh
    assert result is user
    refresh_repo.create_token.assert_called_once()
    assert (
        telemetry_repo.log_event.call_args.kwargs["event_type_name"]
        == "auth.login.success"
    )


def test_confirm_totp_accepts_sql_server_naive_utc_expiry() -> None:
    service, user_repo, _, _, telemetry_repo = _service()
    secret = pyotp.random_base32()
    user_repo.get_by_setup_token.return_value = SimpleNamespace(
        user_id=2,
        pending_totp_secret=encrypt_totp_secret(secret).encode(),
        totp_setup_expires_at=datetime.now(UTC).replace(tzinfo=None)
        + timedelta(minutes=5),
    )

    service.confirm_totp_setup("setup-token", pyotp.TOTP(secret).now(), "127.0.0.1")

    user_repo.confirm_totp.assert_called_once_with(user_id=2)
    assert telemetry_repo.log_event.call_args.kwargs["event_type_name"] == (
        "auth.totp.setup.completed"
    )


def test_refresh_reuse_ends_session_and_revokes_tokens() -> None:
    service, _, session_repo, refresh_repo, telemetry_repo = _service()
    token = SimpleNamespace(
        session_id=8,
        used_at=datetime.now(UTC),
        replaced_by_token_id=None,
    )
    refresh_repo.get_by_hash.return_value = token
    session_repo.get_active_session.return_value = SimpleNamespace(user_id=2)

    with pytest.raises(TokenReuseDetectedError):
        service.refresh_tokens("refresh", "127.0.0.1")

    refresh_repo.revoke_all_for_session.assert_called_once_with(session_id=8)
    session_repo.end_session.assert_called_once_with(session_id=8)
    assert telemetry_repo.log_event.call_args.kwargs["event_type_name"] == (
        "auth.refresh.reuse_detected"
    )


def test_expired_refresh_token_is_rejected() -> None:
    service, _, _, refresh_repo, _ = _service()
    refresh_repo.get_by_hash.return_value = SimpleNamespace(
        session_id=8,
        used_at=None,
        replaced_by_token_id=None,
        revoked_at=None,
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )

    with pytest.raises(Exception) as error:
        service.refresh_tokens("refresh", "127.0.0.1")

    assert error.value.code == "INVALID_TOKEN"
