from typing import ClassVar

import httpx
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Input, Label

from cloud_frontend.services.api_client import ApiClient
from cloud_frontend.ui.widgets.header import CloudHeader


class AdminUsersScreen(Screen[None]):
    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("b", "back", "Back"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, client: ApiClient, username: str) -> None:
        super().__init__()
        self.client = client
        self.username = username
        self._users: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        yield CloudHeader()
        yield DataTable(id="users", cursor_type="row")
        yield Vertical(
            Label("Select a user row to edit account actions.", id="selected-user"),
            Horizontal(
                Input(placeholder="Selected user ID", id="user-id", disabled=True),
                Input(
                    placeholder="Enter new quota in bytes",
                    id="quota",
                    disabled=True,
                ),
            ),
            Horizontal(
                Button("Update quota", id="quota-update", disabled=True),
                Button(
                    "Delete user", id="user-delete", classes="remove", disabled=True
                ),
                Button(
                    "Force delete user and files",
                    id="user-force-delete",
                    classes="remove",
                    disabled=True,
                ),
            ),
            id="user-actions",
        )
        yield Label("", id="message")
        yield Footer()

    def on_mount(self) -> None:
        self.set_focus(None)
        self.call_after_refresh(self.set_focus, None)
        self.query_one(CloudHeader).set_user(self.username)
        self._load()

    def _load(self) -> None:
        table = self.query_one(DataTable)
        table.clear(columns=True)
        table.add_columns("User ID", "Username", "Role", "Quota", "Created At")
        self._users = {}
        for item in self.client.get("/api/v1/admin/users").json():
            user_id = str(item["user_id"])
            self._users[user_id] = str(item["username"])
            table.add_row(
                user_id,
                item["username"],
                item["role"],
                str(item["storage_quota_bytes"]),
                item["created_at"],
                key=user_id,
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self._select_user(event.row_key.value)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key is not None:
            self._select_user(event.row_key.value)

    def _select_user(self, user_id: object) -> None:
        user_id_value = str(user_id)
        self.query_one("#user-id", Input).value = user_id_value
        self.query_one("#quota", Input).disabled = False
        username = self._users.get(user_id_value, user_id_value)
        self.query_one("#selected-user", Label).update(
            f"Selected user: {username} (ID {user_id_value})"
        )
        for button_id in ("quota-update", "user-delete", "user-force-delete"):
            self.query_one(f"#{button_id}", Button).disabled = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "main-menu":
            self.app.pop_screen()
            return
        if event.button.id not in {
            "quota-update",
            "user-delete",
            "user-force-delete",
        }:
            return
        try:
            user_id = self.query_one("#user-id", Input).value.strip()
            if not user_id:
                raise ValueError("User ID is required.")
            if event.button.id == "quota-update":
                quota = self.query_one("#quota", Input).value.strip()
                if not quota:
                    raise ValueError("New quota is required.")
                self.client.put(
                    f"/api/v1/admin/users/{user_id}/quota",
                    json={"quota_bytes": int(quota)},
                )
                self.query_one("#message", Label).update("Quota updated.")
            elif event.button.id == "user-delete":
                self.client.delete(f"/api/v1/admin/users/{user_id}")
                self.query_one("#message", Label).update("User deleted.")
            else:
                self.client.delete(f"/api/v1/admin/users/{user_id}/force")
                self.query_one("#message", Label).update(
                    "User and stored files deleted."
                )
            self._load()
        except httpx.HTTPStatusError as error:
            self.query_one("#message", Label).update(_response_message(error.response))
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            self.query_one("#message", Label).update(str(error))

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_quit(self) -> None:
        self.app.exit()


def _response_message(response: httpx.Response) -> str:
    try:
        body = response.json()
        return str(body.get("error", {}).get("message", response.reason_phrase))
    except (ValueError, TypeError, AttributeError):
        return response.reason_phrase
