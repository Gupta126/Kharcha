from fastapi import APIRouter
from typing import Dict

router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.
    Returns OK status for the ERP service.
    """
    return {"status": "ok", "service": "mock-erp"}


@router.get("/healthz")
async def health_check_spec() -> Dict[str, str]:
    """
    SPEC-compliant health check endpoint.
    Matches the format expected by the backend: {"erp":"ok"}
    """
    return {"erp": "ok"}
