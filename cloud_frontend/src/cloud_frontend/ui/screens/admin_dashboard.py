from typing import TYPE_CHECKING, ClassVar, cast

import httpx
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Label

from cloud_frontend.services.api_client import ApiClient
from cloud_frontend.services.sse_client import SseClient
from cloud_frontend.ui.widgets.header import CloudHeader
from cloud_frontend.ui.widgets.metrics_card import MetricsCard

if TYPE_CHECKING:
    from cloud_frontend.main import CloudStoreApp


class AdminDashboard(Screen[None]):
    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("l", "logout", "Logout"),
        ("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        client: ApiClient,
        sse_client: SseClient,
        username: str,
    ) -> None:
        super().__init__()
        self.client = client
        self.sse_client = sse_client
        self.username = username

    def compose(self) -> ComposeResult:
        yield CloudHeader()
        yield Vertical(
            Label("Administration overview", classes="screen-title"),
            Horizontal(
                MetricsCard(id="system", classes="metric"),
                MetricsCard(id="application", classes="metric"),
            ),
            Horizontal(
                Button("Active sessions", id="sessions"),
                Button("Telemetry log", id="telemetry"),
                Button("Register user", id="register"),
                Button("Manage users", id="users"),
                classes="admin-menu",
            ),
            Label("", id="admin-message"),
            classes="surface",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(CloudHeader).set_user(self.username)
        self.run_worker(self._stream_metrics(), exclusive=True, group="metrics")

    async def _stream_metrics(self) -> None:
        try:
            async for payload in self.sse_client.metrics():
                self.query_one("#system", MetricsCard).update_metric(
                    "System metrics", payload.get("system", {})
                )
                self.query_one("#application", MetricsCard).update_metric(
                    "Application metrics", payload.get("application", {})
                )
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            self.query_one("#admin-message", Label).update(str(error))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "logout":
            cast("CloudStoreApp", self.app).logout()
            return
        screens = {
            "sessions": "sessions",
            "telemetry": "telemetry",
            "register": "register",
            "users": "users",
        }
        target = screens.get(event.button.id or "")
        if target:
            cast("CloudStoreApp", self.app).push_admin_page(target)

    def action_quit(self) -> None:
        self.app.exit()

    def action_logout(self) -> None:
        cast("CloudStoreApp", self.app).logout()
