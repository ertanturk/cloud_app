class AuthManager:
    def __init__(self) -> None:
        self._jwt_access_token: str | None = None

    def set_auth_token(self, token: str) -> None:
        if not token:
            raise ValueError("Access token cannot be empty.")
        self._jwt_access_token = token

    def get_auth_token(self) -> str | None:
        return self._jwt_access_token

    def clear_auth_token(self) -> None:
        self._jwt_access_token = None
