from cloud_backend.db.connection import TelemetrySessionLocal
from cloud_backend.db.models.telemetry import TelemetryEvents
from cloud_backend.db.telemetry_events import TELEMETRY_EVENTS, initialize_database
from sqlalchemy import select


def test_database_initializer_creates_and_seeds_event_catalog(test_root) -> None:
    initialize_database()
    db = TelemetrySessionLocal()
    try:
        rows = db.scalars(select(TelemetryEvents)).all()
        actual = {row.event_type_id: row.event_type for row in rows}
    finally:
        db.close()

    assert actual == TELEMETRY_EVENTS

    initialize_database()
    db = TelemetrySessionLocal()
    try:
        assert len(db.scalars(select(TelemetryEvents)).all()) == len(TELEMETRY_EVENTS)
    finally:
        db.close()
