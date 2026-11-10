from collections.abc import Iterator
from pathlib import Path
from typing import Any, Self

import httpx

from .auth_manager import AuthManager


class ApiClient:
    def __init__(
        self,
        base_url: str,
        auth_manager: AuthManager,
    ) -> None:
        self._auth_manager = auth_manager
        self._client = httpx.Client(
            base_url=base_url,
            timeout=httpx.Timeout(30.0),
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        token = self._auth_manager.get_auth_token()

        if token:
            headers["Authorization"] = f"Bearer {token}"

        return headers

    def get(self, path: str, **params: Any) -> httpx.Response:
        response = self._client.get(
            path,
            params=params,
            headers=self._headers(),
        )
        response.raise_for_status()
        return response

    def post(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        response = self._client.post(
            path,
            json=json,
            headers=self._headers(),
        )
        response.raise_for_status()
        return response

    def put(
        self,
        path: str,
        *,
        content: Any = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        request_headers = {**self._headers(), **(headers or {})}
        response = self._client.put(
            path,
            content=content,
            json=json,
            headers=request_headers,
        )
        response.raise_for_status()
        return response

    def delete(self, path: str) -> httpx.Response:
        response = self._client.delete(path, headers=self._headers())
        response.raise_for_status()
        return response

    def upload_file(
        self,
        path: Path,
        reservation_id: int,
        chunk_size: int = 1024 * 1024,
    ) -> None:
        def chunks() -> Iterator[bytes]:
            with path.open("rb") as file:
                while chunk := file.read(chunk_size):
                    yield chunk

        self.put(
            f"/api/v1/uploads/{reservation_id}/content",
            content=chunks(),
            headers={"Content-Type": "application/octet-stream"},
        )

    def download_file(
        self,
        file_id: int,
        destination: Path,
        chunk_size: int = 1024 * 1024,
    ) -> None:
        with self._client.stream(
            "GET",
            f"/api/v1/files/{file_id}/download",
            headers=self._headers(),
        ) as response:
            response.raise_for_status()

            with destination.open("wb") as file:
                for chunk in response.iter_bytes(chunk_size):
                    file.write(chunk)

    def upload(self, path: Path, original_name: str) -> dict[str, Any]:
        reservation_response = self.post(
            "/api/v1/uploads",
            json={
                "file_name": original_name,
                "file_size_bytes": path.stat().st_size,
            },
        )
        reservation = reservation_response.json()

        try:
            self.upload_file(
                path=path,
                reservation_id=reservation["reservation_id"],
            )
            complete_response = self.post(
                f"/api/v1/uploads/{reservation['reservation_id']}/complete",
                json={"original_file_name": original_name},
            )
            return complete_response.json()
        except Exception:
            self.delete(f"/api/v1/uploads/{reservation['reservation_id']}")
            raise
