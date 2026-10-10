from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.main import app

client = TestClient(app)


class DummyItem(BaseModel):
    name: str


# Create a temporary route to test validation
test_router = APIRouter()


@test_router.post("/v1/_test_validation")
def dummy_validation_endpoint(item: DummyItem):
    return item


probe_app = FastAPI()
probe_app.exception_handlers.update(app.exception_handlers)  # same SPEC error format
probe_app.dependency_overrides = app.dependency_overrides  # same DB override as the real app
probe_app.include_router(test_router)
probe_client = TestClient(probe_app)


def test_unknown_route():
    response = client.get("/v1/this-route-does-not-exist")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert "message" in data["error"]
    assert "details" in data["error"]
    assert data["error"]["details"] == {}


def test_request_validation_error():
    # Missing required 'name' field
    response = probe_client.post("/v1/_test_validation", json={"wrong_field": "value"})
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_FAILED"
    assert "message" in data["error"]
    assert "validation_errors" in data["error"]["details"]
