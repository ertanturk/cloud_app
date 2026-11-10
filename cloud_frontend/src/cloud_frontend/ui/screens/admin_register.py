from typing import ClassVar

import httpx
import qrcode
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Input, Label, Static

from cloud_frontend.services.api_client import ApiClient


class AdminRegisterScreen(Screen[None]):
    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("b", "back", "Back", priority=True),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, client: ApiClient, username: str) -> None:
        super().__init__()
        self.client = client
        self.username = username
        self.totp_setup_token: str | None = None

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Label("Register user", classes="screen-title"),
            Label("Username"),
            Input(placeholder="Username", id="username"),
            Label("Initial password"),
            Input(placeholder="Initial password", password=True, id="password"),
            Button("Create user", id="create"),
            Label("Authenticator QR code", classes="section-title"),
            Static("", id="qr", classes="qr"),
            Label("First authenticator code", classes="section-title"),
            Input(placeholder="First 6-digit TOTP code", id="totp"),
            Button("Confirm TOTP", id="confirm"),
            Label("", id="message"),
            Label("Press B to return to the admin dashboard.", classes="help-text"),
            classes="surface",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.set_focus(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        try:
            if event.button.id == "create":
                username = self.query_one("#username", Input).value.strip()
                password = self.query_one("#password", Input).value
                if not username:
                    raise ValueError("Username is required.")
                if not password:
                    raise ValueError("Initial password is required.")
                if len(password) < 8:
                    raise ValueError(
                        "Initial password must contain at least 8 characters."
                    )
                response = self.client.post(
                    "/api/v1/admin/users",
                    json={
                        "username": self.query_one("#username", Input).value,
                        "initial_password": password,
                    },
                ).json()
                setup = self.client.post(
                    "/api/v1/auth/totp/setup",
                    json={
                        "username": response["username"],
                        "password": password,
                        "client_ip": "127.0.0.1",
                    },
                ).json()
                self.totp_setup_token = setup["setup_token"]
                self.query_one("#qr", Static).update(
                    _render_qr(setup["provisioning_uri"])
                )
            elif event.button.id == "confirm":
                if self.totp_setup_token is None:
                    raise ValueError("Create the user before confirming TOTP.")
                totp_code = self.query_one("#totp", Input).value.strip()
                if len(totp_code) != 6 or not totp_code.isdecimal():
                    raise ValueError("Enter the current 6-digit TOTP code.")
                self.client.post(
                    "/api/v1/auth/totp/confirm",
                    json={
                        "setup_token": self.totp_setup_token,
                        "totp_code": totp_code,
                    },
                )
                self.query_one("#message", Label).update("User TOTP setup completed.")
        except httpx.HTTPStatusError as error:
            self.query_one("#message", Label).update(_response_message(error.response))
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            self.query_one("#message", Label).update(str(error))

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_quit(self) -> None:
        self.app.exit()


def _render_qr(value: str) -> str:
    code = qrcode.QRCode(border=1)
    code.add_data(value)
    code.make(fit=True)
    matrix = code.get_matrix()
    if len(matrix) % 2:
        matrix.append([False] * len(matrix[0]))
    rows = []
    for top, bottom in zip(matrix[::2], matrix[1::2]):
        rows.append(
            "".join(
                "█" if upper and lower else "▀" if upper else "▄" if lower else " "
                for upper, lower in zip(top, bottom)
            )
        )
    return "\n".join(rows)


def _response_message(response: httpx.Response) -> str:
    try:
        body = response.json()
        return str(body.get("error", {}).get("message", response.reason_phrase))
    except (ValueError, TypeError, AttributeError):
        return response.reason_phrase
