"""POST /v1/documents API endpoint implementing SPEC §3 and contracts/openapi.yaml."""

import logging
import uuid
from enum import Enum
from typing import Any, Literal

import redis
import uuid6
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from rq import Queue
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.errors import ValidationError
from app.core.settings import settings
from app.db.session import get_db
from app.models.claim import Claim
from app.models.document import Document
from app.models.expense_line import ExpenseLine
from app.schemas.receipt import ExtractedReceipt
from app.services.extraction import save_extracted_receipt
from app.workers.extract_document import extract_document_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/documents", tags=["documents"])


class CaptureSource(str, Enum):
    camera_scan = "camera_scan"
    gallery = "gallery"
    share = "share"
    screenshot = "screenshot"
    pdf_download = "pdf_download"


class DeviceTier(str, Enum):
    A = "A"
    B = "B"
    C = "C"


class DocumentStatus(str, Enum):
    extracted = "extracted"
    queued = "queued"
    needs_confirmation = "needs_confirmation"


class TrustSignal(BaseModel):
    name: str
    failed: bool


class DocumentCreateRequest(BaseModel):
    sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    mime: Literal["image/jpeg", "image/png", "image/webp", "image/heic", "application/pdf"]
    pages: int = Field(default=1, ge=1, le=10)
    capture_source: CaptureSource
    device_tier: DeviceTier
    extraction: dict[str, Any] | None = None
    trust_signals: list[TrustSignal] | None = Field(default_factory=list)
    ocr_text: str | None = None


class DocumentCreatedResponse(BaseModel):
    document_id: str
    status: DocumentStatus
    claim_id: str
    line_id: str | None = None


@router.post(
    "",
    response_model=DocumentCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        200: {
            "description": "already exists (same sha256)",
            "model": DocumentCreatedResponse,
        },
        201: {
            "description": "created",
            "model": DocumentCreatedResponse,
        },
    },
)
async def create_document(
    request: DocumentCreateRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or attach a document to an employee draft claim with Tier A/B/C extraction."""
    # Validate ocr_text is provided when extraction is null per contract
    if request.extraction is None and not (request.ocr_text and request.ocr_text.strip()):
        raise ValidationError("ocr_text is required when extraction is null")

    # Validate extraction schema if present
    parsed_extraction: ExtractedReceipt | None = None
    if request.extraction is not None:
        try:
            parsed_extraction = ExtractedReceipt.model_validate(request.extraction)
        except Exception as e:
            raise ValidationError(f"Invalid extraction payload: {e}") from e

    employee_id_str = current_user.get("sub")
    if not employee_id_str:
        raise ValidationError("Invalid employee token")
    employee_id = uuid.UUID(employee_id_str)

    # 1. Idempotency check: same sha256 for the same employee -> 200 with existing IDs
    existing_doc_stmt = select(Document).where(
        Document.employee_id == employee_id, Document.sha256 == request.sha256
    )
    res = await db.execute(existing_doc_stmt)
    existing_doc = res.scalar_one_or_none()

    if existing_doc:
        # Fetch corresponding line_id if created
        line_stmt = select(ExpenseLine.id).where(ExpenseLine.document_id == existing_doc.id)
        line_res = await db.execute(line_stmt)
        existing_line_id = line_res.scalar_one_or_none()

        # Determine status
        doc_status = DocumentStatus.extracted if existing_line_id else DocumentStatus.queued

        from fastapi.responses import JSONResponse

        resp_content = DocumentCreatedResponse(
            document_id=str(existing_doc.id),
            status=doc_status,
            claim_id=str(existing_doc.claim_id),
            line_id=str(existing_line_id) if existing_line_id else None,
        ).model_dump()
        return JSONResponse(status_code=status.HTTP_200_OK, content=resp_content)

    # 2. Attach to the employee's open draft claim (create one if none exists)
    claim_stmt = (
        select(Claim)
        .where(Claim.employee_id == employee_id, Claim.status == "draft")
        .order_by(Claim.created_at.asc())
    )
    claim_res = await db.execute(claim_stmt)
    draft_claim = claim_res.scalars().first()

    if not draft_claim:
        draft_claim = Claim(
            id=uuid6.uuid7(),
            employee_id=employee_id,
            title="Draft Claim",
            status="draft",
            total_paise=0,
        )
        db.add(draft_claim)
        await db.flush()

    # 3. Create document row
    new_doc_id = uuid6.uuid7()
    doc = Document(
        id=new_doc_id,
        employee_id=employee_id,
        claim_id=draft_claim.id,
        sha256=request.sha256,
        mime=request.mime,
        pages=request.pages,
        capture_source=request.capture_source.value,
        device_tier=request.device_tier.value,
        prompt_version=parsed_extraction.prompt_version if parsed_extraction else None,
    )
    db.add(doc)
    await db.flush()

    # Path 1: Extraction provided (Tier A/B) -> process immediately, return extracted
    if parsed_extraction:
        line = await save_extracted_receipt(
            db=db,
            doc=doc,
            claim=draft_claim,
            receipt=parsed_extraction,
            default_source="ocr",  # on-device extraction from Tier A/B
        )
        await db.commit()

        return DocumentCreatedResponse(
            document_id=str(doc.id),
            status=DocumentStatus.extracted,
            claim_id=str(draft_claim.id),
            line_id=str(line.id),
        )

    # Path 2: Extraction null with ocr_text (Tier C) -> enqueue RQ job, return queued
    await db.commit()

    # Enqueue on ${QUEUE_PREFIX}extract
    try:
        redis_conn = redis.from_url(settings.REDIS_URL)
        q = Queue(f"{settings.QUEUE_PREFIX}extract", connection=redis_conn)
        q.enqueue(extract_document_task, str(doc.id), request.ocr_text)
    except Exception as e:
        logger.error(f"Failed to enqueue extraction job for doc {doc.id}: {e}")

    return DocumentCreatedResponse(
        document_id=str(doc.id),
        status=DocumentStatus.queued,
        claim_id=str(draft_claim.id),
        line_id=None,
    )
