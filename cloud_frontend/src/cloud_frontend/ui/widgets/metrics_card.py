from typing import Any

from textual.widgets import Static


class MetricsCard(Static):
    def update_metric(self, title: str, values: dict[str, Any]) -> None:
        lines = [f"[bold #F2C14E]{title}[/bold #F2C14E]"]
        for key, value in values.items():
            label = key.replace("_", " ").title()
            lines.append(f"[#C1A78E]{label}:[/] {self._format_value(key, value)}")
        self.update("\n".join(lines))

    @staticmethod
    def _format_value(key: str, value: Any) -> str:
        if key.endswith("_bytes") and isinstance(value, (int, float)):
            return _format_bytes(value)
        if key.endswith("_bytes_per_sec") and isinstance(value, (int, float)):
            return f"{_format_bytes(value)}/s"
        if key.endswith("_percent") and isinstance(value, (int, float)):
            return f"{value:.1f}%"
        return str(value)


def _format_bytes(value: float) -> str:
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{value:.1f} B"
