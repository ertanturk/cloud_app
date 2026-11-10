from textual.widgets import Header


class CloudHeader(Header):
    """Shared product header."""

    def set_user(self, username: str) -> None:
        self.sub_title = username
