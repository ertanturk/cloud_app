import json
from datetime import UTC, datetime, timedelta

import keyring
import pytest
from cloud_frontend.services.auth_manager import AuthManager
from cloud_frontend.services.keyring_store import SERVICE_NAME, KeyringStore


class FakeKeyring:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}

    def set_password(self, service: str, key: str, value: str) -> None:
        self.values[(service, key)] = value

    def get_password(self, service: str, key: str) -> str | None:
        return self.values.get((service, key))

    def delete_password(self, service: str, key: str) -> None:
        self.values.pop((service, key), None)


def make_store(monkeypatch: pytest.MonkeyPatch) -> tuple[KeyringStore, FakeKeyring]:
    backend = FakeKeyring()
    monkeypatch.setattr(keyring, "get_keyring", lambda: backend)
    return KeyringStore(), backend


def test_auth_manager_keeps_access_token_in_memory() -> None:
    manager = AuthManager()
    manager.set_auth_token("access-token")

    assert manager.get_auth_token() == "access-token"
    manager.clear_auth_token()
    assert manager.get_auth_token() is None


def test_auth_manager_rejects_empty_token() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        AuthManager().set_auth_token("")


def test_keyring_store_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    store, _ = make_store(monkeypatch)
    store.store("user", "refresh-token")

    record = store.retrieve("user")

    assert record is not None
    assert record["refresh_token"] == "refresh-token"


def test_expired_keyring_record_is_deleted(monkeypatch: pytest.MonkeyPatch) -> None:
    store, backend = make_store(monkeypatch)
    backend.set_password(
        SERVICE_NAME,
        "user",
        json.dumps(
            {
                "created_at": (datetime.now(UTC) - timedelta(days=31)).isoformat(),
                "refresh_token": "expired-token",
            }
        ),
    )

    assert store.retrieve("user") is None
    assert store.retrieve("user") is None


def test_malformed_keyring_record_is_deleted(monkeypatch: pytest.MonkeyPatch) -> None:
    store, backend = make_store(monkeypatch)
    backend.set_password(SERVICE_NAME, "user", "{not-json")

    assert store.retrieve("user") is None
    assert backend.get_password(SERVICE_NAME, "user") is None
