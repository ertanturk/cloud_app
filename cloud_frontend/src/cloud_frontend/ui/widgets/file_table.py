from collections.abc import Iterable
from typing import Any

from textual.widgets import DataTable


class FileTable(DataTable[str]):
    def __init__(self) -> None:
        super().__init__(cursor_type="row")
        self._file_ids: list[int] = []
        self._file_names: list[str] = []

    def load_files(self, files: Iterable[dict[str, Any]]) -> None:
        self.clear(columns=True)
        self._file_ids = []
        self._file_names = []
        self.add_columns(
            "File ID", "File Name", "File Size", "Extension", "Uploaded At"
        )
        rows = list(files)
        for item in rows:
            self._file_ids.append(int(item["file_id"]))
            self._file_names.append(str(item["file_name"]))
            self.add_row(
                str(item["file_id"]),
                str(item["file_name"]),
                _format_bytes(int(item["file_size_bytes"])),
                str(item.get("extension") or ""),
                str(item["uploaded_at"]),
                key=str(item["file_id"]),
            )
        if not rows:
            self.add_row("—", "No files uploaded yet", "—", "—", "—")

    @property
    def selected_file_id(self) -> int | None:
        if not self._file_ids or self.cursor_row < 0:
            return None
        if self.cursor_row >= len(self._file_ids):
            return None
        return self._file_ids[self.cursor_row]

    @property
    def selected_file_name(self) -> str | None:
        if not self._file_names or self.cursor_row < 0:
            return None
        if self.cursor_row >= len(self._file_names):
            return None
        return self._file_names[self.cursor_row]


def _format_bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{value} B"
