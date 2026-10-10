from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, Optional
from uuid import UUID
import logging

from ..core.storage import storage, ClaimStatus
from ..core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/submit")
async def submit_claim(claim_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Submit a reimbursement claim to the ERP system.
    Returns an ERP reference number.
    """
    # Validate required fields
    required_fields = ["employee_id", "amount_paise"]
    for field in required_fields:
        if field not in claim_data:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}"
            )
    
    # Verify employee exists
    employee = storage.get_employee_by_email(claim_data["employee_id"])
    if not employee:
        # Try to find by employee ID if email not found
        employee = None
        for emp in storage.employees.values():
            if emp.get("id") == claim_data["employee_id"]:
                employee = emp
                break
    
    if not employee:
        raise HTTPException(
            status_code=400,
            detail=f"Employee not found: {claim_data['employee_id']}"
        )
    
    # Submit the claim
    claim = storage.submit_claim(claim_data)
    
    logger.info(f"Submitted claim {claim.id} for employee {claim.employee_id}")
    
    return {
        "status": "submitted",
        "erp_ref": claim.erp_ref,
        "claim_id": claim.id
    }


@router.get("/claim/{claim_id}")
async def get_claim_status(claim_id: str) -> Dict[str, Any]:
    """
    Get the status of a specific claim by its ID or ERP reference.
    """
    claim = storage.get_claim(claim_id)
    
    # If not found by ID, try to find by ERP reference
    if not claim:
        for c in storage.claims.values():
            if c.erp_ref == claim_id:
                claim = c
                break
    
    if not claim:
        raise HTTPException(
            status_code=404,
            detail=f"Claim not found: {claim_id}"
        )
    
    return claim.to_dict()


@router.get("/claims/{employee_email}")
async def get_employee_claims(employee_email: str) -> Dict[str, Any]:
    """
    Get all claims for a specific employee.
    """
    employee = storage.get_employee_by_email(employee_email)
    if not employee:
        raise HTTPException(
            status_code=404,
            detail=f"Employee not found: {employee_email}"
        )
    
    claims = storage.get_claims_by_employee(employee_email)
    
    return {
        "employee": employee,
        "claims": [claim.to_dict() for claim in claims]
    }
