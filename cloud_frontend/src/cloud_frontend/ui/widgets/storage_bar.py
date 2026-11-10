from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, ProgressBar


class StorageBar(Vertical):
    def __init__(
        self,
        quota_bytes: int = 0,
        used_bytes: int = 0,
        reserved_bytes: int = 0,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.quota_bytes = quota_bytes
        self.used_bytes = used_bytes
        self.reserved_bytes = reserved_bytes

    def compose(self) -> ComposeResult:
        yield Label("Storage", id="storage-title")
        yield ProgressBar(
            total=max(self.quota_bytes, 1), show_eta=False, id="storage-progress"
        )
        yield Label(self._summary(), id="storage-summary")

    def update_storage(self, data: dict[str, int]) -> None:
        self.quota_bytes = data["quota_bytes"]
        self.used_bytes = data["used_bytes"]
        self.reserved_bytes = data["reserved_bytes"]
        self.query_one("#storage-progress", ProgressBar).update(
            total=max(self.quota_bytes, 1),
            progress=min(self.used_bytes + self.reserved_bytes, self.quota_bytes),
        )
        self.query_one("#storage-summary", Label).update(self._summary())

    def _summary(self) -> str:
        available = max(
            self.quota_bytes - self.used_bytes - self.reserved_bytes,
            0,
        )
        return (
            f"Used: {_format_bytes(self.used_bytes)} | "
            f"Quota: {_format_bytes(self.quota_bytes)} | "
            f"Available: {_format_bytes(available)}"
        )


def _format_bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{value} B"
