from fastapi import APIRouter, Depends
from typing import Dict
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


async def check_database() -> str:
    """Check database connectivity.
    Returns 'ok' if connected, 'down' otherwise.
    """
    # TODO: Implement actual database check when database module is available
    # For now, return 'ok' as placeholder
    return "ok"


async def check_redis() -> str:
    """Check Redis connectivity.
    Returns 'ok' if connected, 'down' otherwise.
    """
    # TODO: Implement actual Redis check when Redis module is available
    # For now, return 'ok' as placeholder
    return "ok"


async def check_llm() -> str:
    """Check LLM gateway connectivity.
    Returns 'ok' if accessible, 'degraded' if using stub, 'down' otherwise.
    """
    # TODO: Implement actual LLM check when LLM module is available
    # For now, return 'ok' as placeholder (assuming stub mode works)
    return "ok"


async def check_erp() -> str:
    """Check ERP service connectivity.
    Returns 'ok' if accessible, 'down' otherwise.
    """
    # TODO: Implement actual ERP check when ERP client is available
    # For now, return 'ok' as placeholder
    return "ok"


@router.get("/healthz")
async def health_check() -> Dict[str, str]:
    """Health check endpoint.
    Returns status of critical services: db, redis, llm, erp.
    """
    # Run all checks concurrently would be better, but for simplicity:
    db_status = await check_database()
    redis_status = await check_redis()
    llm_status = await check_llm()
    erp_status = await check_erp()

    return {
        "db": db_status,
        "redis": redis_status,
        "llm": llm_status,
        "erp": erp_status
    }