import pytest
from fastapi.testclient import TestClient
import jwt
from datetime import datetime, timezone

from app.main import app
from app.core.settings import settings
from app.api.auth import require_role, require_token
from app.db.session import get_db
from fastapi import APIRouter, Depends

# Create a test router to test protected routes
test_router = APIRouter(prefix="/v1/test_protected", tags=["test"])

@test_router.get("/user", dependencies=[Depends(require_token)])
async def get_user_protected():
    return {"status": "ok"}

@test_router.get("/admin", dependencies=[Depends(require_role(["approver", "finance"]))])
async def get_admin_protected():
    return {"status": "ok"}

app.include_router(test_router)

class MockResult:
    def __init__(self, data):
        self.data = data
    def fetchone(self):
        return self.data

class MockAsyncSession:
    async def execute(self, query, params=None):
        email = params.get("email") if params else None
        if email == "priya@kharcha.test":
            return MockResult(("0192f000-0000-7000-8000-000000000001", "employee"))
        elif email == "meera@kharcha.test":
            return MockResult(("0192f000-0000-7000-8000-000000000003", "approver"))
        return MockResult(None)

async def override_get_db():
    yield MockAsyncSession()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def test_login_success():
    response = client.post("/v1/auth/login", json={"email": "priya@kharcha.test"})
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["role"] == "employee"
    assert data["employee_id"] == "0192f000-0000-7000-8000-000000000001"
    
def test_login_unknown_email():
    response = client.post("/v1/auth/login", json={"email": "unknown@example.com"})
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHORIZED"

def test_protected_route_missing_token():
    response = client.get("/v1/test_protected/user")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"

def test_protected_route_invalid_token():
    response = client.get("/v1/test_protected/user", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"

def test_protected_route_valid_token():
    # login first
    resp = client.post("/v1/auth/login", json={"email": "priya@kharcha.test"})
    token = resp.json()["token"]
    
    response = client.get("/v1/test_protected/user", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

def test_protected_route_wrong_role():
    # login as employee
    resp = client.post("/v1/auth/login", json={"email": "priya@kharcha.test"})
    token = resp.json()["token"]
    
    # try to access approver route
    response = client.get("/v1/test_protected/admin", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"

def test_protected_route_correct_role():
    # login as approver
    resp = client.post("/v1/auth/login", json={"email": "meera@kharcha.test"})
    token = resp.json()["token"]
    
    # try to access approver route
    response = client.get("/v1/test_protected/admin", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
