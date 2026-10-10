"""PRD §22 names for claim intake and status; reuse the existing /erp handlers."""
from typing import Any

from fastapi import APIRouter

from .erp import get_claim_status, submit_claim

router = APIRouter(tags=["reimbursements"])


@router.post("/reimbursements")
async def create_reimbursement(claim_data: dict[str, Any]) -> dict[str, str]:
    return await submit_claim(claim_data)


@router.get("/reimbursements/{ref}")
async def get_reimbursement(ref: str) -> dict[str, Any]:
    return await get_claim_status(ref)
