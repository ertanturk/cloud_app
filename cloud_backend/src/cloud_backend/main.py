"""
Main entry point for the Cloud Storage Backend FastAPI application.
Configures application lifecycle, CORS middleware, global exception handlers, and routing.
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from cloud_backend.api.v1 import admin, auth, files, sse, storage, uploads
from cloud_backend.core.app_logging import ProjectLogger
from cloud_backend.core.config import get_config
from cloud_backend.core.exceptions import ServiceException
from cloud_backend.core.instance_lock import InstanceLock
from cloud_backend.db.connection import core_engine, telemetry_engine
from cloud_backend.tasks.checksum_checker import checksum_checker_task
from cloud_backend.tasks.cleanup import session_cleanup_task
from cloud_backend.tasks.file_recovery import file_recovery_task
from cloud_backend.tasks.garbage_collector import garbage_collector_task

logger = ProjectLogger.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handles startup and shutdown events for application background tasks and resources."""
    lock_path = Path(get_config().STORAGE_BASE_PATH) / ".cloudstore-backend.lock"
    with InstanceLock(lock_path, "Local\\CloudStoreBackend"):
        cleanup_task = asyncio.create_task(
            session_cleanup_task(), name="session-cleanup-task"
        )
        garbage_task = asyncio.create_task(
            garbage_collector_task(str(Path(get_config().STORAGE_BASE_PATH) / ".tmp")),
            name="garbage-collector-task",
        )
        file_recovery_background_task = asyncio.create_task(
            file_recovery_task(get_config().STORAGE_BASE_PATH),
            name="file-recovery-task",
        )
        checksum_background_task = asyncio.create_task(
            checksum_checker_task(get_config().STORAGE_BASE_PATH),
            name="checksum-checker-task",
        )
        logger.info("Cloud Backend API startup complete.")
        try:
            yield
        finally:
            cleanup_task.cancel()
            garbage_task.cancel()
            file_recovery_background_task.cancel()
            checksum_background_task.cancel()
            with suppress(asyncio.CancelledError):
                await cleanup_task
            with suppress(asyncio.CancelledError):
                await garbage_task
            with suppress(asyncio.CancelledError):
                await file_recovery_background_task
            with suppress(asyncio.CancelledError):
                await checksum_background_task
            logger.info("Cloud Backend API shutdown complete.")


app = FastAPI(
    title="Cloud Storage Backend API",
    description="Backend service for secure file management.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a stable public error without exposing database or filesystem details."""
    logger.exception(
        "Unhandled exception while processing %s %s", request.method, request.url.path
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {"code": "INTERNAL_ERROR", "message": "Internal server error."}
        },
    )


@app.exception_handler(ServiceException)
async def service_exception_handler(
    request: Request, exc: ServiceException
) -> JSONResponse:
    """Translates custom domain exceptions into standardized JSON ErrorResponse models."""
    logger.warning(
        "Service error for %s %s: %s", request.method, request.url.path, exc.code
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
            }
        },
    )


for router in (
    auth.router,
    files.router,
    uploads.router,
    storage.router,
    admin.router,
    sse.router,
):
    app.include_router(router)


@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
def health_check() -> dict[str, str]:
    """Public service health check endpoint."""
    with core_engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    with telemetry_engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "healthy"}
