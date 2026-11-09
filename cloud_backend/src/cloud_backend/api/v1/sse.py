# ruff: noqa: B008

"""
Server-Sent Events (SSE) router pushing real-time system and application metrics
to admin clients every 2 seconds.
"""

import asyncio
import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from cloud_backend.api.v1.dependencies import (
    get_current_admin,
    get_metrics_service,
)
from cloud_backend.db.models import Users
from cloud_backend.services import MetricsService

router = APIRouter(prefix="/api/v1/admin", tags=["SSE & Live Metrics"])


@router.get("/events")
async def stream_live_metrics(
    request: Request,
    current_admin: Users = Depends(get_current_admin),
    metrics_service: MetricsService = Depends(get_metrics_service),
) -> StreamingResponse:
    """
    Establishes a persistent SSE stream pushing host performance and app database metrics
    every 2 seconds. Requires admin privileges.
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            while True:
                if await request.is_disconnected():
                    break
                payload = {
                    "system": metrics_service.get_system_metrics().model_dump(),
                    "application": metrics_service.get_application_metrics().model_dump(),
                }
                yield f"event: metrics\ndata: {json.dumps(payload, default=str)}\n\n"
                await asyncio.sleep(2)
        except asyncio.CancelledError:
            return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
