"""Preflight checks for the uv-managed Python runtime."""

import shutil
import subprocess  # nosec B404
from pathlib import Path


class BootstrapError(RuntimeError):
    """Raised when a bootstrap prerequisite is not satisfied."""


def project_root() -> Path:
    root = Path(__file__).resolve().parents[2]
    required = (root / ".python-version", root / "pyproject.toml", root / "uv.lock")
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise BootstrapError(f"Missing project files: {', '.join(missing)}")
    return root


def pinned_python_version(root: Path | None = None) -> str:
    value = (
        (root or project_root())
        .joinpath(".python-version")
        .read_text(encoding="utf-8")
        .strip()
    )
    if not value:
        raise BootstrapError(".python-version is empty.")
    return value


def verify_runtime(root: Path | None = None) -> str:
    root = root or project_root()
    uv = shutil.which("uv")
    if uv is None:
        raise BootstrapError("uv was not found on PATH.")
    version = pinned_python_version(root)
    result = subprocess.run(  # nosec B603
        [uv, "python", "find", version],
        cwd=root / "cloud_backend",
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise BootstrapError(result.stderr.strip() or "uv could not select Python.")
    return version


def sync_dependencies(root: Path | None = None) -> None:
    root = root or project_root()
    uv = shutil.which("uv")
    if uv is None:
        raise BootstrapError("uv was not found on PATH.")
    result = subprocess.run(  # nosec B603
        [uv, "sync", "--locked"],
        cwd=root / "cloud_backend",
        check=False,
    )
    if result.returncode:
        raise BootstrapError("uv sync --locked failed.")
