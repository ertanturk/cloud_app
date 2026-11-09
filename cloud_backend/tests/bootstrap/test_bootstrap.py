import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from bootstrap.env_manager import update_database_urls
from bootstrap.instance_lock import InstanceLock
from bootstrap.passwords import prompt_password


def test_instance_lock_rejects_duplicate_and_releases(tmp_path: Path) -> None:
    lock_path = tmp_path / "instance.lock"
    lock_name = f"CloudStoreTest-{tmp_path.name}"

    with (
        InstanceLock(lock_path, lock_name),
        pytest.raises(RuntimeError, match="already held"),
        InstanceLock(lock_path, lock_name),
    ):
        pass

    with InstanceLock(lock_path, lock_name):
        pass


def test_password_prompt_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    values = iter(("short", "valid-password"))
    monkeypatch.setattr("getpass.getpass", lambda _: next(values))

    assert prompt_password("Password: ", minimum_length=12, attempts=2) == (
        "valid-password"
    )


def test_environment_update_does_not_create_backup(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("JWT_SECRET_KEY=existing-secret\n", encoding="utf-8")

    update_database_urls(
        env_path,
        "mssql+pymssql://app:secret@localhost:1433/CloudCore",
        "mssql+pymssql://app:secret@localhost:1433/CloudTelemetry",
    )

    assert not (tmp_path / ".env.bak").exists()
    content = env_path.read_text(encoding="utf-8")
    assert "JWT_SECRET_KEY=existing-secret" in content
    assert "CORE_DB_URL=" in content
    assert "TELEMETRY_DB_URL=" in content
