from types import SimpleNamespace

import pytest
from cloud_backend.api.v1.dependencies import (
    get_current_admin,
    get_current_session_id,
    get_current_token_payload,
)
from cloud_backend.core.exceptions import ForbiddenError, InvalidTokenError
from cloud_backend.core.security import create_access_token


def test_token_payload_requires_subject_and_session() -> None:
    credentials = SimpleNamespace(credentials=create_access_token({"sub": "1"}))

    with pytest.raises(InvalidTokenError):
        get_current_token_payload(credentials)


def test_session_id_is_read_from_validated_payload() -> None:
    assert get_current_session_id({"session_id": 42}) == 42


def test_current_admin_rejects_normal_user() -> None:
    with pytest.raises(ForbiddenError):
        get_current_admin(SimpleNamespace(role="user"))
