from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer

from cloud_frontend.services.api_client import ApiClient
from cloud_frontend.ui.widgets.header import CloudHeader


class AdminSessionsScreen(Screen[None]):
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
        yield DataTable(id="sessions")
        yield Footer()

    def on_mount(self) -> None:
        self.set_focus(None)
        self.query_one(CloudHeader).set_user(self.username)
        table = self.query_one(DataTable)
        table.add_columns(
            "Session ID", "User ID", "Username", "Client IP", "Started", "Last Activity"
        )
        for item in self.client.get("/api/v1/admin/sessions").json():
            table.add_row(
                str(item["session_id"]),
                str(item["user_id"]),
                item["username"],
                item["client_ip"],
                item["started_at"],
                item["last_activity_at"],
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_quit(self) -> None:
        self.app.exit()
