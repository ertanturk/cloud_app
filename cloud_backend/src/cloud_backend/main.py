"""
Main entry point for the Cloud Storage Backend FastAPI application.
Configures application lifecycle, CORS middleware, global exception handlers, and routing.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from cloud_backend.api.v1 import admin, auth, files, sse, storage, uploads
from cloud_backend.core.app_logging import ProjectLogger
from cloud_backend.core.exceptions import ServiceException

logger = ProjectLogger.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handles startup and shutdown events for application background tasks and resources."""
    logger.info("Cloud Backend API startup complete.")
    yield
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
    return {"status": "healthy"}
