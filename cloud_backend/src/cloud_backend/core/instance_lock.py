"""Process locks for the backend and bootstrap lifecycle."""

import ctypes
import os
from pathlib import Path
from typing import Self

_ERROR_ALREADY_EXISTS = 183


class InstanceLock:
    """Own a named Windows mutex, with an exclusive-file fallback elsewhere."""

    def __init__(self, path: Path, name: str) -> None:
        self.path = path
        self.name = name
        self._file = None
        self._handle: int | None = None

    def __enter__(self) -> Self:
        if os.name == "nt":
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            handle = kernel32.CreateMutexW(None, True, self.name)
            if not handle:
                raise OSError("Could not create the Windows instance mutex.")
            if ctypes.get_last_error() == _ERROR_ALREADY_EXISTS:
                kernel32.CloseHandle(handle)
                raise RuntimeError(f"Instance lock is already held: {self.name}")
            self._handle = handle
            return self

        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._file = self.path.open("x", encoding="utf-8")
        except FileExistsError as error:
            raise RuntimeError(f"Instance lock is already held: {self.path}") from error
        self._file.write(str(os.getpid()))
        self._file.flush()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self._handle is not None:
            ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle(self._handle)
            self._handle = None
        if self._file is not None:
            self._file.close()
            self.path.unlink(missing_ok=True)
            self._file = None
