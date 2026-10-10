from fastapi.testclient import TestClient
from app.main import app
import pytest

client = TestClient(app)

def test_healthz_endpoint():
    response = client.get("/v1/healthz")
    assert response.status_code == 200
    data = response.json()
    
    # SPEC shape: {"db": "...", "redis": "...", "llm": "...", "erp": "..."}
    assert "db" in data
    assert "redis" in data
    assert "llm" in data
    assert "erp" in data
    
    # db and redis are "ok" against dev services (assuming the mock returns "ok")
    assert data["db"] == "ok"
    assert data["redis"] == "ok"
