import os
import time

from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.settings import settings
from app.db import session as db_session
from app.llm.gateway import LLMGateway
from app.main import app

client = TestClient(app)

UNUSED_URL_HTTP = "http://127.0.0.1:59999"
UNUSED_URL_REDIS = "redis://127.0.0.1:59999/0"
UNUSED_URL_DB = (
    make_url(os.environ["TEST_DATABASE_URL"]).set(port=59999).render_as_string(hide_password=False)
)


def test_healthz_all_ok():
    """When everything is reachable, all four services report 'ok'."""
    try:
        LLMGateway.set_last_status("ok")
        response = client.get("/v1/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data == {
            "db": "ok",
            "redis": "ok",
            "llm": "ok",
            "erp": "ok",
        }
    finally:
        LLMGateway.set_last_status("ok")


def test_healthz_db_unreachable_only(monkeypatch):
    """When database is unreachable, db is 'down' and others stay 'ok'."""
    orig_engine = db_session.engine
    bad_engine = create_async_engine(UNUSED_URL_DB)
    try:
        db_session.engine = bad_engine
        db_session.AsyncSessionLocal.configure(bind=bad_engine)
        response = client.get("/v1/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["db"] == "down"
        assert data["redis"] == "ok"
        assert data["llm"] == "ok"
        assert data["erp"] == "ok"
    finally:
        db_session.engine = orig_engine
        db_session.AsyncSessionLocal.configure(bind=orig_engine)


def test_healthz_redis_unreachable_only(monkeypatch):
    """When Redis is unreachable, redis is 'down' and others stay 'ok'."""
    monkeypatch.setattr(settings, "REDIS_URL", UNUSED_URL_REDIS)
    response = client.get("/v1/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["db"] == "ok"
    assert data["redis"] == "down"
    assert data["llm"] == "ok"
    assert data["erp"] == "ok"


def test_healthz_erp_unreachable_only(monkeypatch):
    """When ERP is unreachable, erp is 'down' and others stay 'ok'."""
    monkeypatch.setattr(settings, "ERP_BASE_URL", UNUSED_URL_HTTP)
    response = client.get("/v1/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["db"] == "ok"
    assert data["redis"] == "ok"
    assert data["llm"] == "ok"
    assert data["erp"] == "down"


def test_healthz_llm_unreachable_only(monkeypatch):
    """When LLM gateway is unreachable, llm is 'degraded' and others stay 'ok'."""
    monkeypatch.setattr(settings, "LITELLM_URL", UNUSED_URL_HTTP)
    response = client.get("/v1/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["db"] == "ok"
    assert data["redis"] == "ok"
    assert data["llm"] == "degraded"
    assert data["erp"] == "ok"


def test_healthz_llm_degraded_in_stub_mode(monkeypatch):
    """In stub mode, LLM probe is still made: if gateway is unreachable, llm is 'degraded'."""
    monkeypatch.setattr(settings, "LLM_MODE", "stub")
    monkeypatch.setattr(settings, "LITELLM_URL", UNUSED_URL_HTTP)
    response = client.get("/v1/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["llm"] == "degraded"


def test_healthz_answers_within_3_seconds_when_all_unreachable(monkeypatch):
    """Healthz answers within 3 s even when every dependency is unreachable."""
    orig_engine = db_session.engine
    bad_engine = create_async_engine(UNUSED_URL_DB)
    try:
        db_session.engine = bad_engine
        db_session.AsyncSessionLocal.configure(bind=bad_engine)
        monkeypatch.setattr(settings, "REDIS_URL", UNUSED_URL_REDIS)
        monkeypatch.setattr(settings, "ERP_BASE_URL", UNUSED_URL_HTTP)
        monkeypatch.setattr(settings, "LITELLM_URL", UNUSED_URL_HTTP)

        start = time.monotonic()
        response = client.get("/v1/healthz")
        elapsed = time.monotonic() - start

        assert response.status_code == 200
        data = response.json()
        assert data["db"] == "down"
        assert data["redis"] == "down"
        assert data["llm"] == "degraded"
        assert data["erp"] == "down"
        assert elapsed < 3.0, f"Health check took {elapsed:.2f}s, expected < 3.0s"
    finally:
        db_session.engine = orig_engine
        db_session.AsyncSessionLocal.configure(bind=orig_engine)


def test_healthz_llm_degraded_by_last_gateway_call():
    """Probe is ok, but last real gateway call failed -> degraded."""
    try:
        LLMGateway.set_last_status("degraded")
        response = client.get("/v1/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["llm"] == "degraded"
    finally:
        LLMGateway.set_last_status("ok")
