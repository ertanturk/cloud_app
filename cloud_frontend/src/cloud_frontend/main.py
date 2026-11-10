import httpx
from textual.app import App

from cloud_frontend.cli.args import parse_args
from cloud_frontend.services.api_client import ApiClient
from cloud_frontend.services.auth_manager import AuthManager
from cloud_frontend.services.keyring_store import KeyringStore
from cloud_frontend.services.sse_client import SseClient
from cloud_frontend.ui.screens.admin_dashboard import AdminDashboard
from cloud_frontend.ui.screens.admin_register import AdminRegisterScreen
from cloud_frontend.ui.screens.admin_sessions import AdminSessionsScreen
from cloud_frontend.ui.screens.admin_telemetry import AdminTelemetryScreen
from cloud_frontend.ui.screens.admin_users import AdminUsersScreen
from cloud_frontend.ui.screens.login import LoginScreen
from cloud_frontend.ui.screens.user_dashboard import UserDashboard
from cloud_frontend.ui.styles.theme import APP_CSS


class CloudStoreApp(App[None]):
    CSS = APP_CSS
    TITLE = "CloudVault"
    SUB_TITLE = "Secure file storage"
    ENABLE_COMMAND_PALETTE = False

    def __init__(self, base_url: str, admin_mode: bool) -> None:
        super().__init__()
        self.auth_manager = AuthManager()
        self.keyring_store = KeyringStore()
        self.client = ApiClient(base_url, self.auth_manager)
        self.sse_client = SseClient(base_url, self.auth_manager)
        self.admin_mode = admin_mode
        self.username = ""

    def on_mount(self) -> None:
        if self._restore_session():
            return
        self.push_screen(
            LoginScreen(
                self.client,
                self.auth_manager,
                self.keyring_store,
                self.admin_mode,
            ),
            self.open_dashboard,
        )

    def _restore_session(self) -> bool:
        record = self.keyring_store.retrieve("default")
        if not record or not record.get("username") or not record.get("role"):
            return False
        try:
            response = self.client.post(
                "/api/v1/auth/refresh",
                json={"raw_refresh_token": record["refresh_token"]},
            ).json()
            self.auth_manager.set_auth_token(response["access_token"])
            user: dict[str, object] = {
                "username": record["username"],
                "role": record["role"],
            }
            if self.admin_mode and user["role"] != "admin":
                raise ValueError("Stored account role does not match this mode.")
            self.keyring_store.store(
                "default",
                response["refresh_token"],
                user=user,
            )
            self.open_dashboard(user)
            return True
        except httpx.HTTPStatusError as error:
            if error.response.status_code in {401, 403}:
                self._clear_session()
            return False
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            self.auth_manager.clear_auth_token()
            return False

    def _clear_session(self) -> None:
        self.keyring_store.clear("default")
        self.auth_manager.clear_auth_token()

    def open_dashboard(self, user: dict[str, object] | None) -> None:
        if user is None:
            return
        self.username = str(user["username"])
        if self.admin_mode:
            self.push_screen(
                AdminDashboard(self.client, self.sse_client, self.username)
            )
        else:
            self.push_screen(UserDashboard(self.client, user))

    def push_admin_page(self, page: str) -> None:
        pages = {
            "sessions": AdminSessionsScreen,
            "telemetry": AdminTelemetryScreen,
            "register": AdminRegisterScreen,
            "users": AdminUsersScreen,
        }
        screen_type = pages.get(page)
        if screen_type is None:
            return
        self.push_screen(screen_type(self.client, self.username))

    def on_unmount(self) -> None:
        self.client.close()
        self.run_worker(self.sse_client.close())

    def logout(self) -> None:
        record = self.keyring_store.retrieve("default")
        if record:
            try:
                self.client.post(
                    "/api/v1/auth/logout",
                    json={"raw_refresh_token": record["refresh_token"]},
                )
            except httpx.HTTPError:
                pass
        self.keyring_store.clear("default")
        self.auth_manager.clear_auth_token()
        self.exit()


def main() -> None:
    args = parse_args()
    CloudStoreApp(args.base_url, args.admin).run()
