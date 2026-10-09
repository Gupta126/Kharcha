import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from app.core.errors import (
    create_error_response,
    NotFoundError,
    ValidationError,
    IllegalTransitionError,
    NotEntitledError,
    DuplicateDocumentError,
    LlmUnavailableError,
    ErpUnavailableError,
    UnauthorizedError,
    ForbiddenError,
    exception_handlers
)


def create_test_app():
    """Create a test FastAPI app with error handlers."""
    app = FastAPI()

    # Add exception handlers
    for exc_type, handler in exception_handlers.items():
        app.add_exception_handler(exc_type, handler)

    return app


def test_error_response_format():
    """Test that create_error_response produces correct format."""
    response = create_error_response(
        code="TEST_ERROR",
        message="Test error message",
        details={"key": "value"},
        status_code=400
    )

    assert response.status_code == 400
    data = response.body.decode()
    assert '"error"' in data
    assert '"code":"TEST_ERROR"' in data  # No space after colon in compact JSON
    assert '"message":"Test error message"' in data
    assert '"key":"value"' in data


def test_not_found_error():
    """Test NotFoundError produces correct response."""
    app = create_test_app()

    @app.get("/test-not-found")
    async def test_not_found():
        raise NotFoundError("Resource not found")

    client = TestClient(app)
    response = client.get("/test-not-found")

    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "NOT_FOUND"
    assert data["error"]["message"] == "Resource not found"


def test_validation_error():
    """Test ValidationError produces correct response."""
    app = create_test_app()

    @app.post("/test-validation")
    async def test_validation():
        raise ValidationError("Invalid input")

    client = TestClient(app)
    response = client.post("/test-validation")

    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_FAILED"
    assert data["error"]["message"] == "Invalid input"


def test_illegal_transition_error():
    """Test IllegalTransitionError produces correct response."""
    app = create_test_app()

    @app.post("/test-illegal")
    async def test_illegal():
        raise IllegalTransitionError("Invalid state transition")

    client = TestClient(app)
    response = client.post("/test-illegal")

    assert response.status_code == 409
    data = response.json()
    assert data["error"]["code"] == "ILLEGAL_TRANSITION"
    assert data["error"]["message"] == "Invalid state transition"


def test_http_exception_handler():
    """Test that standard HTTPException is handled correctly."""
    app = create_test_app()

    @app.get("/test-http")
    async def test_http():
        raise HTTPException(status_code=404, detail="Not Found")

    client = TestClient(app)
    response = client.get("/test-http")

    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "NOT_FOUND"
    assert data["error"]["message"] == "Not Found"


def test_validation_exception_handler():
    """Test that request validation errors are handled correctly."""
    app = create_test_app()

    @app.post("/test-req-validation")
    async def test_req_validation(item_id: int):
        return {"item_id": item_id}

    client = TestClient(app)
    # Send invalid data (string instead of int)
    response = client.post("/test-req-validation", json={"item_id": "not-an-int"})

    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_FAILED"
    assert "validation_errors" in data["error"]["details"]