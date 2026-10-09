from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel

from ..core.config import settings

router = APIRouter()


class ScenarioConfig(BaseModel):
    in_review_delay: Optional[int] = None
    approved_delay: Optional[int] = None
    paid_delay: Optional[int] = None


@router.post("/scenario")
async def configure_scenario(config: ScenarioConfig) -> Dict[str, Any]:
    """
    Configure scenario timings for claim status transitions.
    Allows testing different timing scenarios.
    """
    updated = []
    
    if config.in_review_delay is not None:
        settings.IN_REVIEW_DELAY = config.in_review_delay
        updated.append("in_review_delay")
    
    if config.approved_delay is not None:
        settings.APPROVED_DELAY = config.approved_delay
        updated.append("approved_delay")
    
    if config.paid_delay is not None:
        settings.PAID_DELAY = config.paid_delay
        updated.append("paid_delay")
    
    # Update the global storage instance's delays
    # Note: In a real implementation, we'd need to update existing claims too
    # For simplicity, we'll apply to new claims only
    
    return {
        "status": "scenario_updated",
        "updated_fields": ", ".join(updated) if updated else "none",
        "new_values": {
            "in_review_delay": settings.IN_REVIEW_DELAY,
            "approved_delay": settings.APPROVED_DELAY,
            "paid_delay": settings.PAID_DELAY
        }
    }


@router.get("/scenario")
async def get_scenario() -> Dict[str, Any]:
    """
    Get current scenario timing configuration.
    """
    return {
        "in_review_delay": settings.IN_REVIEW_DELAY,
        "approved_delay": settings.APPROVED_DELAY,
        "paid_delay": settings.PAID_DELAY,
        "description": "Status transition delays in seconds"
    }
