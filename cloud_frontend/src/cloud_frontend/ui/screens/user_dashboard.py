from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, cast

import httpx
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Input, Label

from cloud_frontend.services.api_client import ApiClient
from cloud_frontend.ui.widgets.file_table import FileTable
from cloud_frontend.ui.widgets.header import CloudHeader
from cloud_frontend.ui.widgets.storage_bar import StorageBar

if TYPE_CHECKING:
    from cloud_frontend.main import CloudStoreApp


class UserDashboard(Screen[None]):
    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("u", "upload", "Upload"),
        ("d", "focus_download", "Download"),
        ("r", "remove", "Remove"),
        ("l", "logout", "Logout"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, client: ApiClient, user: dict[str, object]) -> None:
        super().__init__()
        self.client = client
        self.user = user

    def compose(self) -> ComposeResult:
        yield CloudHeader()
        yield Vertical(
            StorageBar(id="storage"),
            Label(
                "Your files",
                classes="section-title",
            ),
            FileTable(),
            Vertical(
                Label(
                    "• Select a file row before downloading or removing.",
                    classes="help-text",
                ),
                Label(
                    "• Upload: enter a local path, then press Enter, click Upload file, or press U.",
                    classes="help-text",
                ),
                Label(
                    "• Download: enter a folder or target file path, then click Download selected or press D.",
                    classes="help-text",
                ),
                classes="instructions",
            ),
            Horizontal(
                Input(
                    placeholder="Local file path, e.g. C:\\Files\\report.pdf",
                    id="upload-path",
                ),
                Button("Upload file", id="upload", classes="upload"),
            ),
            Horizontal(
                Input(
                    placeholder="Download folder, e.g. C:\\Files",
                    id="download-path",
                ),
                Button("Download selected", id="download", classes="download"),
                Button("Remove selected", id="remove", classes="remove"),
            ),
            Label("", id="message"),
            classes="surface",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(CloudHeader).set_user(str(self.user["username"]))
        self.refresh_data()

    def refresh_data(self) -> None:
        files = self.client.get("/api/v1/files", limit=100, offset=0).json()
        storage = self.client.get("/api/v1/storage").json()
        self.query_one(FileTable).load_files(files)
        self.query_one(StorageBar).update_storage(storage)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        try:
            if event.button.id == "logout":
                self._app().logout()
                return
            if event.button.id == "upload":
                raw_path = self.query_one("#upload-path", Input).value.strip()
                if not raw_path:
                    raise ValueError("Choose a local file path before uploading.")
                path = Path(raw_path).expanduser()
                if not path.is_file():
                    raise ValueError(f"Local file was not found: {path}")
                self.client.upload(path, path.name)
                self.refresh_data()
                self._message("Upload completed.", "success")
            elif event.button.id == "download":
                file_id = self.query_one(FileTable).selected_file_id
                if file_id is None:
                    raise ValueError("Select a file from the table first.")
                raw_destination = self.query_one("#download-path", Input).value.strip()
                if not raw_destination:
                    raise ValueError("Choose a destination folder before downloading.")
                file_name = self.query_one(FileTable).selected_file_name
                if not file_name:
                    raise ValueError("The selected file name is unavailable.")
                destination_input = Path(raw_destination).expanduser()
                if destination_input.exists() and destination_input.is_dir():
                    destination = destination_input / Path(file_name).name
                elif destination_input.exists():
                    if not destination_input.is_file():
                        raise ValueError("Download target is not a regular file.")
                    destination = destination_input
                else:
                    if not destination_input.parent.is_dir():
                        raise ValueError(
                            f"Download folder was not found: {destination_input.parent}"
                        )
                    destination = destination_input
                if not destination.parent.is_dir():
                    raise ValueError(
                        f"Download folder was not found: {destination.parent}"
                    )
                self.client.download_file(file_id, destination)
                if not destination.is_file():
                    raise OSError(f"Download target was not created: {destination}")
                self._message(f"Download completed: {destination}", "success")
            elif event.button.id == "remove":
                file_id = self.query_one(FileTable).selected_file_id
                if file_id is None:
                    raise ValueError("Select a file from the table first.")
                self.client.delete(f"/api/v1/files/{file_id}")
                self.refresh_data()
                self._message("File removed.", "success")
        except httpx.HTTPStatusError as error:
            self._message(_response_message(error.response), "error")
        except (httpx.HTTPError, OSError, ValueError, KeyError, TypeError) as error:
            self._message(str(error), "error")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "upload-path":
            self.query_one("#upload", Button).press()
        elif event.input.id == "download-path":
            self.query_one("#download", Button).press()

    def _message(self, value: str, class_name: str) -> None:
        label = self.query_one("#message", Label)
        label.remove_class("error", "success")
        label.add_class(class_name)
        label.update(value)
        self.set_timer(5, self._clear_message)

    def _clear_message(self) -> None:
        self.query_one("#message", Label).update("")

    def action_focus_upload(self) -> None:
        self.query_one("#upload-path", Input).focus()

    def action_upload(self) -> None:
        self.query_one("#upload", Button).press()

    def action_focus_download(self) -> None:
        self.query_one("#download-path", Input).focus()

    def action_remove(self) -> None:
        self.query_one("#remove", Button).press()

    def action_quit(self) -> None:
        self.app.exit()

    def action_logout(self) -> None:
        self._app().logout()

    def _app(self) -> "CloudStoreApp":
        return cast("CloudStoreApp", self.app)


def _response_message(response: httpx.Response) -> str:
    try:
        body = response.json()
        return str(body.get("error", {}).get("message", response.reason_phrase))
    except (ValueError, TypeError, AttributeError):
        return response.reason_phrase
