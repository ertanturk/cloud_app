import os
import secrets
import tempfile
from pathlib import Path

import pytest

_TEST_ROOT = Path(tempfile.mkdtemp(prefix="cloud-backend-tests-"))
os.environ.update(
    {
        "CORE_DB_URL": f"sqlite:///{_TEST_ROOT / 'core.db'}",
        "TELEMETRY_DB_URL": f"sqlite:///{_TEST_ROOT / 'telemetry.db'}",
        "JWT_SECRET_KEY": secrets.token_urlsafe(32),
        "STORAGE_BASE_PATH": str(_TEST_ROOT / "storage"),
        "LOG_FILE_PATH": str(_TEST_ROOT / "cloud_backend.log"),
    }
)


@pytest.fixture(scope="session")
def test_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _TEST_ROOT


@pytest.fixture
def storage_root(test_root: Path) -> Path:
    path = test_root / "storage"
    path.mkdir(exist_ok=True)
    return path
