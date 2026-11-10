from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Input, Label

from cloud_frontend.services.api_client import ApiClient
from cloud_frontend.ui.widgets.header import CloudHeader


class AdminTelemetryScreen(Screen[None]):
    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("b", "back", "Back"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, client: ApiClient, username: str) -> None:
        super().__init__()
        self.client = client
        self.username = username

    def compose(self) -> ComposeResult:
        yield CloudHeader()
        yield Label("Enter filters and press Enter to refresh the telemetry log.")
        yield Vertical(
            Horizontal(
                Input(placeholder="Event type", id="event-type"),
                Input(placeholder="User ID", id="user-id"),
            ),
            DataTable(id="telemetry"),
            id="telemetry-content",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.set_focus(None)
        self.call_after_refresh(self.set_focus, None)
        self.query_one(CloudHeader).set_user(self.username)
        self._load()

    def _load(self) -> None:
        params: dict[str, str] = {"limit": "100", "offset": "0"}
        event_type = self.query_one("#event-type", Input).value
        user_id = self.query_one("#user-id", Input).value
        if event_type:
            params["event_type"] = event_type
        if user_id:
            params["user_id"] = user_id
        table = self.query_one(DataTable)
        table.clear(columns=True)
        table.add_columns(
            "Event ID", "Type", "User ID", "Session ID", "Client IP", "Event Time"
        )
        for item in self.client.get("/api/v1/admin/telemetry", **params).json():
            table.add_row(
                str(item["event_id"]),
                item["event_type"],
                str(item.get("user_id") or ""),
                str(item.get("session_id") or ""),
                item["client_ip"],
                item["event_time"],
            )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._load()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_quit(self) -> None:
        self.app.exit()
