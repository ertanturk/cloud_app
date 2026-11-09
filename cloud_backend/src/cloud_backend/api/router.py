"""
Master API router aggregating all versioned sub-routers for the cloud backend service.
"""

from fastapi import APIRouter

from cloud_backend.api.v1 import admin, auth, files, sse, storage, uploads

master_router = APIRouter()

master_router.include_router(auth.router)
master_router.include_router(files.router)
master_router.include_router(uploads.router)
master_router.include_router(storage.router)
master_router.include_router(admin.router)
master_router.include_router(sse.router)
