"""
Database connection engine and session dependency definitions.
"""

from collections.abc import Generator
from typing import Any

from fastapi.exceptions import RequestValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from cloud_backend.core.app_logging import ProjectLogger
from cloud_backend.core.config import get_config

logger = ProjectLogger.get_logger(__name__)
config = get_config()


def _engine_options(url: str) -> dict[str, object]:
    """Use pooling options only for database dialects that support them."""
    if url.startswith("sqlite"):
        return {"pool_pre_ping": True}
    return {"pool_size": 10, "max_overflow": 20, "pool_pre_ping": True}


def _create_engine(url: str):
    engine = create_engine(url, **_engine_options(url))
    if url.startswith("sqlite"):
        return engine.execution_options(schema_translate_map={"dbo": None})
    return engine


# Core Database Engine & Connection Pool Configuration
core_engine = _create_engine(config.CORE_DB_URL.get_secret_value())

# Core Session Factory
CoreSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=core_engine,
)

# Telemetry Database Engine & Connection Pool Configuration
telemetry_engine = _create_engine(config.TELEMETRY_DB_URL.get_secret_value())

# Telemetry Session Factory
TelemetrySessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=telemetry_engine,
)


def get_core_db() -> Generator[Session, Any, None]:
    """
    FastAPI dependency that provides a transactional database session for Core DB.
    Ensures the session is safely closed after handling a request.
    """
    db = CoreSessionLocal()
    try:
        yield db
    except RequestValidationError:
        raise
    except Exception:
        logger.exception("Core database request failed")
        raise
    finally:
        db.close()


def get_telemetry_db() -> Generator[Session, Any, None]:
    """
    FastAPI dependency that provides a transactional database session for Telemetry DB.
    Ensures the session is safely closed after handling a request.
    """
    db = TelemetrySessionLocal()
    try:
        yield db
    except RequestValidationError:
        raise
    except Exception:
        logger.exception("Telemetry database request failed")
        raise
    finally:
        db.close()
