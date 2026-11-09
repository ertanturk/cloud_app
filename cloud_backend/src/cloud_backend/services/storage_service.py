"""
Service handling physical storage service handling disk I/O, temporary streaming writes,
SHA-256 checksum calculations, atomic file moves, and disk deletions.
"""

import hashlib
import os
import shutil
from pathlib import Path

from cloud_backend.core.exceptions import StorageError


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
            raise StorageError(
                message=f"Failed to initialize storage directories: {err}"
            )

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
        ext_suffix = f".{extension.lstrip('.')}" if extension else ""
        return str(user_dir / f"{file_id}{ext_suffix}")

    def write_chunk(self, file_path: str, chunk: bytes, append: bool = True) -> None:
        """Appends streaming bytes to the specified file path."""
        try:
            mode = "ab" if append else "wb"
            with open(file_path, mode) as f:
                f.write(chunk)
        except OSError as err:
            raise StorageError(message=f"Failed to write chunk to disk: {err}")

    def compute_checksum_and_size(self, file_path: str) -> tuple[bytes, int]:
        """
        Reads a file in 64KB blocks to compute its raw 32-byte SHA-256 digest
        and total size in bytes without loading the full file into memory.
        """
        if not os.path.exists(file_path):
            raise StorageError(
                message=f"File not found for checksum verification: {file_path}"
            )

        sha256_hash = hashlib.sha256()
        total_bytes = 0

        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(65536):  # 64 KB chunks
                    sha256_hash.update(chunk)
                    total_bytes += len(chunk)

            return sha256_hash.digest(), total_bytes
        except OSError as err:
            raise StorageError(message=f"Error computing file checksum: {err}")

    def move_file(self, source_path: str, destination_path: str) -> None:
        """Atomically moves a file from source to destination, creating target directories if needed."""
        try:
            dest_dir = os.path.dirname(destination_path)
            os.makedirs(dest_dir, exist_ok=True)
            shutil.move(source_path, destination_path)
        except OSError as err:
            raise StorageError(message=f"Failed to move file on disk: {err}")

    def delete_file(self, file_path: str) -> None:
        """Safely and idempotently removes a file from physical storage."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError as err:
            raise StorageError(message=f"Failed to delete file from disk: {err}")

    def exists(self, file_path: str) -> bool:
        """Checks if a file exists on physical storage."""
        return os.path.exists(file_path)
