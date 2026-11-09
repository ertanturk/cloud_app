from cloud_backend.db.telemetry_events import initialize_database
from cloud_backend.main import app
from fastapi.testclient import TestClient


def test_health_endpoint(test_root) -> None:
    initialize_database()

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
