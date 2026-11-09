"""Run the separate Core and Telemetry Alembic migration environments."""

from pathlib import Path


def _upgrade(database_url: str, script_location: Path) -> None:
    from alembic import command
    from alembic.config import Config

    config = Config()
    config.set_main_option("script_location", str(script_location))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")


def run_migrations(root: Path, core_url: str, telemetry_url: str) -> None:
    _upgrade(core_url, root / "cloud_backend" / "migrations_core")
    _upgrade(telemetry_url, root / "cloud_backend" / "migrations_telemetry")
