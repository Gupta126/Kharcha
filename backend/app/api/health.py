import asyncio
import logging
from enum import Enum

import httpx
import redis.asyncio as aioredis
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.core.settings import settings
from app.db.session import AsyncSessionLocal
from app.llm.gateway import LLMGateway

logger = logging.getLogger(__name__)

router = APIRouter()


class ServiceStatus(str, Enum):
    ok = "ok"
    down = "down"


class LlmStatus(str, Enum):
    ok = "ok"
    degraded = "degraded"
    down = "down"


class HealthResponse(BaseModel):
    db: ServiceStatus
    redis: ServiceStatus
    llm: LlmStatus
    erp: ServiceStatus


async def check_database() -> str:
    """Check database connectivity.
    Returns 'ok' if connected, 'down' otherwise.
    Timeout: ~2.0 seconds.
    """
    try:

        async def _query():
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))

        await asyncio.wait_for(_query(), timeout=2.0)
        return "ok"
    except Exception as exc:
        logger.warning(f"Database health check failed: {exc}")
        return "down"


async def check_redis() -> str:
    """Check Redis connectivity.
    Returns 'ok' if connected, 'down' otherwise.
    Timeout: ~1.0 second.
    """
    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_timeout=1.0)
        try:
            await asyncio.wait_for(r.ping(), timeout=1.0)
            return "ok"
        finally:
            await r.aclose()
    except Exception as exc:
        logger.warning(f"Redis health check failed: {exc}")
        return "down"


async def check_llm() -> str:
    """Check LLM gateway connectivity.
    ALWAYS probe the gateway: GET {LITELLM_URL}/health/liveliness with ~2s timeout.
    Probe fails -> 'degraded'.
    Probe ok but last real gateway calls failed -> 'degraded'.
    Otherwise 'ok'.
    """
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.LITELLM_URL.rstrip('/')}/health/liveliness")
            if resp.status_code != 200:
                return "degraded"
    except Exception as exc:
        logger.warning(f"LLM liveliness check failed: {exc}")
        return "degraded"

    if LLMGateway.get_last_status() == "degraded":
        return "degraded"

    return "ok"


async def check_erp() -> str:
    """Check ERP service connectivity.
    GET {ERP_BASE_URL}/health with ~2s timeout. HTTP 200 -> 'ok', otherwise 'down'.
    """
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.ERP_BASE_URL.rstrip('/')}/health")
            if resp.status_code == 200:
                return "ok"
            return "down"
    except Exception as exc:
        logger.warning(f"ERP health check failed: {exc}")
        return "down"


@router.get("/healthz", response_model=HealthResponse)
async def health_check():
    """Health check endpoint.
    Returns status of critical services: db, redis, llm, erp.
    Runs all four checks concurrently so it answers within ~2.5s even if all are down.
    """
    db_status, redis_status, llm_status, erp_status = await asyncio.gather(
        check_database(),
        check_redis(),
        check_llm(),
        check_erp(),
    )

    return HealthResponse(
        db=db_status,
        redis=redis_status,
        llm=llm_status,
        erp=erp_status,
    )
