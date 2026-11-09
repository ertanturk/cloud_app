"""
Service handling physical storage service handling disk I/O, temporary streaming writes,
SHA-256 checksum calculations, atomic file moves, and disk deletions.
"""

import hashlib
import os
import shutil
from pathlib import Path

from cloud_backend.core.app_logging import ProjectLogger
from cloud_backend.core.exceptions import StorageError

logger = ProjectLogger.get_logger(__name__)


class StorageService:
    """Manages physical disk storage operations and path resolutions."""

    def __init__(self, storage_root: str = r"D:\Storage") -> None:
        self.storage_root = Path(storage_root).resolve()
        self.temp_dir = self.storage_root / ".tmp"
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensures storage root and temporary upload directories exist on disk."""
        try:
            os.makedirs(self.storage_root, exist_ok=True)
            os.makedirs(self.temp_dir, exist_ok=True)
        except OSError as err:
            logger.exception("Failed to initialize storage directories")
            raise StorageError() from err

    def is_safe_path(self, file_path: str) -> bool:
        """Return whether a path resolves beneath the configured storage root."""
        try:
            Path(file_path).resolve().relative_to(self.storage_root)
            return True
        except ValueError:
            return False

    def get_temp_path(self, file_id: int) -> str:
        """Returns the absolute path for an ongoing temporary file upload."""
        return str(self.temp_dir / f"upload_{file_id}.tmp")

    def get_final_path(
        self, user_id: int, file_id: int, extension: str | None = None
    ) -> str:
        """
        Formats and returns the deterministic target path for a completed file:
        e.g., storage_root/user_{user_id}/{file_id}.{extension}
        """
        user_dir = self.storage_root / f"user_{user_id}"
        safe_extension = "".join(
            char
            for char in (extension or "").lstrip(".")
            if char.isalnum() or char in {"-", "_"}
        )[:20]
        ext_suffix = f".{safe_extension}" if safe_extension else ""
        return str(user_dir / f"{file_id}{ext_suffix}")

    def file_size(self, file_path: str) -> int:
        try:
            return Path(file_path).stat().st_size
        except OSError as err:
            logger.exception("Failed to write storage chunk")
            raise StorageError() from err

    def write_chunk(self, file_path: str, chunk: bytes, append: bool = True) -> None:
        """Appends streaming bytes to the specified file path."""
        if not self.is_safe_path(file_path):
            raise StorageError()
        try:
            mode = "ab" if append else "wb"
            with open(file_path, mode) as f:
                f.write(chunk)
        except OSError as err:
            logger.exception("Failed to compute storage checksum")
            raise StorageError() from err

    def compute_checksum_and_size(self, file_path: str) -> tuple[bytes, int]:
        """
        Reads a file in 64KB blocks to compute its raw 32-byte SHA-256 digest
        and total size in bytes without loading the full file into memory.
        """
        if not os.path.exists(file_path):
            raise StorageError()

        sha256_hash = hashlib.sha256()
        total_bytes = 0

        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(65536):  # 64 KB chunks
                    sha256_hash.update(chunk)
                    total_bytes += len(chunk)

            return sha256_hash.digest(), total_bytes
        except OSError as err:
            logger.exception("Failed to move storage file")
            raise StorageError() from err

    def move_file(self, source_path: str, destination_path: str) -> None:
        """Atomically moves a file from source to destination, creating target directories if needed."""
        if not self.is_safe_path(source_path) or not self.is_safe_path(
            destination_path
        ):
            raise StorageError()
        try:
            dest_dir = os.path.dirname(destination_path)
            os.makedirs(dest_dir, exist_ok=True)
            shutil.move(source_path, destination_path)
        except OSError as err:
            logger.exception("Failed to delete storage file")
            raise StorageError() from err

    def delete_file(self, file_path: str) -> None:
        """Safely and idempotently removes a file from physical storage."""
        if not self.is_safe_path(file_path):
            raise StorageError()
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError as err:
            raise StorageError() from err

    def exists(self, file_path: str) -> bool:
        """Checks if a file exists on physical storage."""
        return self.is_safe_path(file_path) and os.path.exists(file_path)
