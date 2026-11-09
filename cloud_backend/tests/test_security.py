from datetime import UTC, datetime, timedelta

import jwt
from cloud_backend.core.security import (
    create_access_token,
    hash_password,
    verify_access_token,
    verify_password,
)


def test_password_hash_round_trip() -> None:
    password_hash, salt = hash_password("correct horse battery staple")

    assert verify_password("correct horse battery staple", salt, password_hash)
    assert not verify_password("wrong password", salt, password_hash)


def test_access_token_contains_claims_and_rejects_expired_token() -> None:
    token = create_access_token({"sub": "7", "session_id": 11, "role": "user"})
    payload = verify_access_token(token)

    assert payload is not None
    assert payload["sub"] == "7"
    assert payload["session_id"] == 11
    assert payload["role"] == "user"

    expired = jwt.encode(
        {
            "sub": "7",
            "session_id": 11,
            "exp": datetime.now(UTC) - timedelta(minutes=1),
        },
        "test-only-secret-key-change-before-production-123",
        algorithm="HS256",
    )
    assert verify_access_token(expired) is None
