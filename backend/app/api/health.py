import logging
from enum import Enum

from fastapi import APIRouter
from pydantic import BaseModel

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
    """
    # TODO: Implement actual database check when database module is available
    return "ok"


async def check_redis() -> str:
    """Check Redis connectivity.
    Returns 'ok' if connected, 'down' otherwise.
    """
    # TODO: Implement actual Redis check when Redis module is available
    return "ok"


async def check_llm() -> str:
    """Check LLM gateway connectivity.
    Returns 'ok' if accessible, 'degraded' if using stub, 'down' otherwise.
    """
    # TODO: Implement actual LLM check when LLM module is available
    return "ok"


async def check_erp() -> str:
    """Check ERP service connectivity.
    Returns 'ok' if accessible, 'down' otherwise.
    """
    # TODO: Implement actual ERP check when ERP client is available
    return "ok"


@router.get("/healthz", response_model=HealthResponse)
async def health_check():
    """Health check endpoint.
    Returns status of critical services: db, redis, llm, erp.
    """
    db_status = await check_database()
    redis_status = await check_redis()
    llm_status = await check_llm()
    erp_status = await check_erp()

    return HealthResponse(db=db_status, redis=redis_status, llm=llm_status, erp=erp_status)
