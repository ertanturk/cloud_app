import httpx
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Label

from cloud_frontend.services.api_client import ApiClient
from cloud_frontend.services.auth_manager import AuthManager
from cloud_frontend.services.keyring_store import KeyringStore


class LoginScreen(Screen[dict[str, object]]):
    def __init__(
        self,
        client: ApiClient,
        auth_manager: AuthManager,
        keyring_store: KeyringStore,
        admin_mode: bool,
    ) -> None:
        super().__init__()
        self.client = client
        self.auth_manager = auth_manager
        self.keyring_store = keyring_store
        self.admin_mode = admin_mode

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("CloudVault", classes="screen-title"),
            Label("Sign in to your secure storage", classes="screen-subtitle"),
            Label("Username"),
            Input(placeholder="Enter your username", id="username"),
            Label("Password"),
            Input(placeholder="Enter your password", password=True, id="password"),
            Label("Authenticator code"),
            Input(placeholder="6-digit TOTP code", id="totp"),
            Label("", id="login-message"),
            Button("Sign in", id="login", classes="primary"),
            classes="surface",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "login":
            return
        try:
            username = self.query_one("#username", Input).value.strip()
            password = self.query_one("#password", Input).value
            totp_code = self.query_one("#totp", Input).value.strip()
            if not username:
                raise ValueError("Username is required.")
            if not password:
                raise ValueError("Password is required.")
            if len(totp_code) != 6 or not totp_code.isdecimal():
                raise ValueError(
                    "Authenticator code is required: enter the current 6-digit code."
                )
            response = self.client.post(
                "/api/v1/auth/login",
                json={
                    "username": username,
                    "password": password,
                    "totp_code": totp_code,
                },
            ).json()
            user = response["user"]
            if self.admin_mode and user["role"] != "admin":
                raise ValueError("The signed-in user is not an administrator.")
            self.auth_manager.set_auth_token(response["access_token"])
            self.keyring_store.store(
                "default",
                response["refresh_token"],
                user=user,
            )
            self.dismiss(user)
        except httpx.HTTPStatusError as error:
            self._show_error(_response_message(error.response))
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            self._show_error(str(error))

    def _show_error(self, message: str) -> None:
        label = self.query_one("#login-message", Label)
        label.remove_class("success")
        label.add_class("error")
        label.update(message)


def _response_message(response: httpx.Response) -> str:
    try:
        body = response.json()
        return str(body.get("error", {}).get("message", response.reason_phrase))
    except (ValueError, TypeError, AttributeError):
        return response.reason_phrase
