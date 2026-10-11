"""Worker task for processing Tier C document extraction asynchronously via RQ."""

import asyncio
import logging
import uuid

from sqlalchemy import select

from app.core.settings import settings
from app.db.session import AsyncSessionLocal
from app.llm.gateway import LLMGateway, LLMUnavailable
from app.models.claim import Claim
from app.models.document import Document
from app.schemas.receipt import ExtractedReceipt
from app.services.extraction import run_degraded_fallback, save_extracted_receipt

logger = logging.getLogger(__name__)


async def _extract_document_async(document_id: str, ocr_text: str | None = None) -> None:
    """Async handler for document extraction worker."""
    doc_uuid = uuid.UUID(document_id)

    async with AsyncSessionLocal() as db:
        # Load document and claim
        stmt = select(Document).where(Document.id == doc_uuid)
        res = await db.execute(stmt)
        doc = res.scalar_one_or_none()
        if not doc:
            logger.error(f"Document {document_id} not found for extraction.")
            return

        claim_stmt = select(Claim).where(Claim.id == doc.claim_id)
        claim_res = await db.execute(claim_stmt)
        claim = claim_res.scalar_one_or_none()
        if not claim:
            logger.error(f"Claim {doc.claim_id} not found for document {document_id}.")
            return

        # Read prompt template
        prompt_content = ocr_text or ""

        gateway = LLMGateway(mode=settings.LLM_MODE)
        try:
            # Call gateway alias kh-extract-text
            llm_result = await gateway.complete(
                task="kh-extract-text",
                prompt=prompt_content,
                claim_id=claim.id,
                document_id=doc.id,
                validate_schema=True,
            )

            # Validate extraction result
            extracted_receipt = ExtractedReceipt.model_validate(llm_result)
            doc.prompt_version = extracted_receipt.prompt_version or "extract_text_v1"

            # Store line and extracted fields
            await save_extracted_receipt(
                db=db,
                doc=doc,
                claim=claim,
                receipt=extracted_receipt,
                default_source="llm",
            )
            await db.commit()
            logger.info(f"Document {document_id} extracted successfully via LLM.")

        except LLMUnavailable as e:
            logger.warning(
                f"LLM unavailable for document {document_id}: {e}. Activating degraded mode."
            )
            # Degraded mode: mark document needs_confirmation and create 3 questions
            await run_degraded_fallback(
                db=db,
                doc=doc,
                claim=claim,
                ocr_text=prompt_content,
            )
            await db.commit()
            logger.info(f"Document {document_id} processed in degraded mode.")


def extract_document_task(document_id: str, ocr_text: str | None = None) -> None:
    """Entrypoint called by RQ worker synchronously in a worker process."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # If already running inside an event loop (e.g., pytest-asyncio)
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                lambda: asyncio.run(_extract_document_async(document_id, ocr_text))
            )
            future.result()
    else:
        asyncio.run(_extract_document_async(document_id, ocr_text))
