import json
from datetime import UTC, datetime

import keyring

SERVICE_NAME = "cloud_store"
STORING_DURATION = 30 * 24 * 60 * 60  # 30 days in seconds


class KeyringStore:
    def __init__(self) -> None:
        self._keyring = keyring.get_keyring()

    def store(self, key: str, refresh_token: str) -> None:
        if not key:
            raise ValueError("Keyring key cannot be empty.")
        if not refresh_token:
            raise ValueError("Refresh token cannot be empty.")

        now = datetime.now(UTC)

        data_to_store = {
            "created_at": now.isoformat(),
            "refresh_token": refresh_token,
        }

        json_string = json.dumps(data_to_store)
        self._keyring.set_password(SERVICE_NAME, key, json_string)

    def retrieve(self, key: str) -> dict[str, str] | None:
        json_string = self._keyring.get_password(SERVICE_NAME, key)
        if not json_string:
            return None

        try:
            stored_data = json.loads(json_string)
            if not isinstance(stored_data, dict):
                raise TypeError("Stored keyring data must be an object.")
            created_at_value = stored_data["created_at"]
            refresh_token = stored_data["refresh_token"]
            if not isinstance(created_at_value, str) or not isinstance(
                refresh_token, str
            ):
                raise TypeError("Stored keyring data has invalid fields.")
            created_at = datetime.fromisoformat(created_at_value)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            self._keyring.delete_password(SERVICE_NAME, key)
            return None

        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        age_seconds = (datetime.now(UTC) - created_at).total_seconds()
        if age_seconds >= STORING_DURATION or age_seconds < 0:
            self._keyring.delete_password(SERVICE_NAME, key)
            return None

        return {
            "created_at": created_at.isoformat(),
            "refresh_token": refresh_token,
        }

    def clear(self, key: str) -> None:
        if not self._keyring.get_password(SERVICE_NAME, key):
            return
        self._keyring.delete_password(SERVICE_NAME, key)
