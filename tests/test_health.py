import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_health_endpoint_exists():
    """Test that the health endpoint exists and returns 200."""
    response = client.get("/v1/healthz")
    assert response.status_code == 200


def test_health_endpoint_returns_correct_schema():
    """Test that health endpoint returns the correct JSON schema."""
    response = client.get("/v1/healthz")
    assert response.status_code == 200

    data = response.json()
    assert "db" in data
    assert "redis" in data
    assert "llm" in data
    assert "erp" in data

    # All values should be strings
    assert isinstance(data["db"], str)
    assert isinstance(data["redis"], str)
    assert isinstance(data["llm"], str)
    assert isinstance(data["erp"], str)

    # Values should be from the expected set (for now, we expect 'ok' from placeholders)
    # In a real implementation, these would be 'ok' or 'down' (and 'degraded' for llm)
    assert data["db"] in ["ok", "down"]
    assert data["redis"] in ["ok", "down"]
    assert data["llm"] in ["ok", "degraded", "down"]
    assert data["erp"] in ["ok", "down"]