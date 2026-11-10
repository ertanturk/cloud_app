"""Async Server-Sent Events client for administrator metrics."""

import json
from collections.abc import AsyncIterator
from typing import Any, Self

import httpx
from httpx_sse import aconnect_sse

from .auth_manager import AuthManager


class SseClient:
    def __init__(
        self,
        base_url: str,
        auth_manager: AuthManager,
    ) -> None:
        self._auth_manager = auth_manager
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(30.0, read=None),
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        traceback: object,
    ) -> None:
        await self.close()

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "text/event-stream"}
        token = self._auth_manager.get_auth_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def metrics(self) -> AsyncIterator[dict[str, Any]]:
        async with aconnect_sse(
            self._client,
            "GET",
            "/api/v1/admin/events",
            headers=self._headers(),
        ) as event_source:
            event_source.response.raise_for_status()
            async for event in event_source.aiter_sse():
                if event.event != "metrics":
                    continue
                payload = json.loads(event.data)
                if not isinstance(payload, dict):
                    raise TypeError("Metrics SSE payload must be a JSON object.")
                yield payload
