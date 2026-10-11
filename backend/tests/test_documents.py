"""Unit tests for POST /v1/documents API and Tier C extraction."""

import json
import uuid
from datetime import date
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.llm.gateway import LLMUnavailable
from app.main import app
from app.models.document import Document
from app.models.employee import Employee
from app.models.expense_line import ExpenseLine
from app.models.extracted_field import ExtractedField
from app.models.question import Question
from app.workers.extract_document import extract_document_task

client = TestClient(app)

SAMPLE_SHA256 = "1122334455667788990011223344556677889900112233445566778899001122"
SAMPLE_RECEIPT = {
    "doc_id": "d_1234",
    "doc_type": "meal",
    "vendor": {"value": "Barbeque Nation, Pune", "conf": 0.98},
    "date": {"value": "2026-10-13", "conf": 0.99},
    "total": {"value_paise": 164000, "currency": "INR", "conf": 0.95},
    "tax": {
        "taxable_paise": 156190,
        "cgst_paise": 3905,
        "sgst_paise": 3905,
        "rate": 5,
        "conf": 0.92,
    },
    "gstin": {"value": "27ABCDE1234F1Z0", "checksum_ok": True},
    "prompt_version": "extract_text_v1",
}


@pytest.fixture(autouse=True)
def ensure_test_employees():
    """Ensure test employees exist and clean up test documents in kharcha_test."""
    import asyncio

    from sqlalchemy import delete

    async def _setup_and_cleanup():
        async with AsyncSessionLocal() as session:
            priya = await session.get(Employee, uuid.UUID("0192f000-0000-7000-8000-000000000001"))
            if not priya:
                priya = Employee(
                    id=uuid.UUID("0192f000-0000-7000-8000-000000000001"),
                    email="priya@kharcha.test",
                    name="Priya Sharma",
                    grade="L4",
                    role="employee",
                )
                session.add(priya)

            arjun = await session.get(Employee, uuid.UUID("0192f000-0000-7000-8000-000000000002"))
            if not arjun:
                arjun = Employee(
                    id=uuid.UUID("0192f000-0000-7000-8000-000000000002"),
                    email="arjun@kharcha.test",
                    name="Arjun Patel",
                    grade="L4",
                    role="employee",
                )
                session.add(arjun)

            # Clean up test documents created by this suite
            test_shas = [
                "0101010101010101010101010101010101010101010101010101010101010101",
                "0202020202020202020202020202020202020202020202020202020202020202",
                "0303030303030303030303030303030303030303030303030303030303030303",
                "0404040404040404040404040404040404040404040404040404040404040404",
                "0505050505050505050505050505050505050505050505050505050505050505",
            ]
            doc_res = await session.execute(
                select(Document.id).where(Document.sha256.in_(test_shas))
            )
            doc_ids = doc_res.scalars().all()
            if doc_ids:
                line_res = await session.execute(
                    select(ExpenseLine.id).where(ExpenseLine.document_id.in_(doc_ids))
                )
                line_ids = line_res.scalars().all()
                if line_ids:
                    await session.execute(delete(Question).where(Question.line_id.in_(line_ids)))
                    await session.execute(delete(ExpenseLine).where(ExpenseLine.id.in_(line_ids)))
                await session.execute(delete(Document).where(Document.id.in_(doc_ids)))
            await session.commit()

    asyncio.run(_setup_and_cleanup())


def get_token(email: str = "priya@kharcha.test") -> str:
    res = client.post("/v1/auth/login", json={"email": email})
    assert res.status_code == 200
    return res.json()["token"]


def test_create_document_unauthorized():
    """POST /v1/documents returns 401 when token is missing."""
    res = client.post(
        "/v1/documents",
        json={
            "sha256": SAMPLE_SHA256,
            "mime": "image/jpeg",
            "pages": 1,
            "capture_source": "camera_scan",
            "device_tier": "A",
            "extraction": SAMPLE_RECEIPT,
        },
    )
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_create_document_validation_failed():
    """POST /v1/documents returns 422 when body is invalid."""
    token = get_token()
    # Missing required fields
    res = client.post(
        "/v1/documents",
        headers={"Authorization": f"Bearer {token}"},
        json={"sha256": "invalid-sha"},
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_FAILED"

    # Extraction is null but ocr_text is omitted
    res2 = client.post(
        "/v1/documents",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "sha256": SAMPLE_SHA256,
            "mime": "image/jpeg",
            "pages": 1,
            "capture_source": "camera_scan",
            "device_tier": "C",
            "extraction": None,
        },
    )
    assert res2.status_code == 422
    assert res2.json()["error"]["code"] == "VALIDATION_FAILED"


@pytest.mark.asyncio
async def test_create_document_path1_extraction_provided():
    """Path 1: on-device extraction stores fields and line immediately -> status extracted."""
    token = get_token("priya@kharcha.test")
    test_sha = "0101010101010101010101010101010101010101010101010101010101010101"

    payload = {
        "sha256": test_sha,
        "mime": "image/jpeg",
        "pages": 1,
        "capture_source": "camera_scan",
        "device_tier": "A",
        "extraction": SAMPLE_RECEIPT,
        "trust_signals": [{"name": "camera_scan", "failed": False}],
    }

    res = client.post(
        "/v1/documents",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "extracted"
    assert data["document_id"]
    assert data["claim_id"]
    assert data["line_id"]

    # Verify database state
    async with AsyncSessionLocal() as session:
        doc = await session.get(Document, uuid.UUID(data["document_id"]))
        assert doc is not None
        assert doc.sha256 == test_sha
        assert doc.device_tier == "A"

        line = await session.get(ExpenseLine, uuid.UUID(data["line_id"]))
        assert line is not None
        assert line.amount_paise == 164000
        assert line.category == "meal"
        assert line.vendor == "Barbeque Nation, Pune"
        assert line.expense_date == date(2026, 10, 13)

        # Check extracted_fields
        ef_res = await session.execute(
            select(ExtractedField).where(ExtractedField.document_id == doc.id)
        )
        fields = {f.name: f for f in ef_res.scalars().all()}
        assert "vendor" in fields
        assert fields["vendor"].value == "Barbeque Nation, Pune"
        assert fields["vendor"].source == "ocr"
        assert "total" in fields
        assert fields["total"].value == "164000"


@pytest.mark.asyncio
async def test_create_document_idempotency_same_employee():
    """Posting same sha256 for same employee returns 200 with same IDs and zero new rows."""
    token = get_token("priya@kharcha.test")
    test_sha = "0202020202020202020202020202020202020202020202020202020202020202"

    payload = {
        "sha256": test_sha,
        "mime": "image/jpeg",
        "pages": 1,
        "capture_source": "camera_scan",
        "device_tier": "A",
        "extraction": SAMPLE_RECEIPT,
    }

    res1 = client.post(
        "/v1/documents",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert res1.status_code == 201
    data1 = res1.json()

    # Re-post exact same payload
    res2 = client.post(
        "/v1/documents",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert res2.status_code == 200
    data2 = res2.json()

    assert data1["document_id"] == data2["document_id"]
    assert data1["claim_id"] == data2["claim_id"]
    assert data1["line_id"] == data2["line_id"]


@pytest.mark.asyncio
async def test_create_document_different_employee_same_sha256():
    """A different employee with the same sha256 gets a new document (idempotency is per employee)."""
    token_priya = get_token("priya@kharcha.test")
    token_arjun = get_token("arjun@kharcha.test")
    test_sha = "0303030303030303030303030303030303030303030303030303030303030303"

    payload = {
        "sha256": test_sha,
        "mime": "image/jpeg",
        "pages": 1,
        "capture_source": "camera_scan",
        "device_tier": "A",
        "extraction": SAMPLE_RECEIPT,
    }

    res_priya = client.post(
        "/v1/documents",
        headers={"Authorization": f"Bearer {token_priya}"},
        json=payload,
    )
    assert res_priya.status_code == 201

    res_arjun = client.post(
        "/v1/documents",
        headers={"Authorization": f"Bearer {token_arjun}"},
        json=payload,
    )
    assert res_arjun.status_code == 201
    assert res_priya.json()["document_id"] != res_arjun.json()["document_id"]


@pytest.mark.asyncio
async def test_create_document_path2_queued_and_worker_extracts():
    """Path 2: extraction null with ocr_text -> 201 queued; worker job fills line and fields."""
    token = get_token("priya@kharcha.test")
    test_sha = "0404040404040404040404040404040404040404040404040404040404040404"
    ocr_text = "Barbeque Nation, Koregaon Park Date: 13/10/2026 Total: Rs 1640.00 Veg buffet x2"

    payload = {
        "sha256": test_sha,
        "mime": "image/jpeg",
        "pages": 1,
        "capture_source": "camera_scan",
        "device_tier": "C",
        "extraction": None,
        "ocr_text": ocr_text,
    }

    res = client.post(
        "/v1/documents",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "queued"
    assert data["line_id"] is None
    doc_id = data["document_id"]

    # Run the worker task synchronously in stub mode (uses gateway fixture)
    extract_document_task(doc_id, ocr_text)

    # Check line and fields are populated
    async with AsyncSessionLocal() as session:
        line_stmt = select(ExpenseLine).where(ExpenseLine.document_id == uuid.UUID(doc_id))
        line_res = await session.execute(line_stmt)
        line = line_res.scalar_one_or_none()
        assert line is not None
        assert line.amount_paise == 164000
        assert line.category == "meal"

        ef_stmt = select(ExtractedField).where(ExtractedField.document_id == uuid.UUID(doc_id))
        ef_res = await session.execute(ef_stmt)
        fields = {f.name: f for f in ef_res.scalars().all()}
        assert fields["vendor"].source == "llm"


@pytest.mark.asyncio
async def test_create_document_degraded_mode_creates_questions():
    """Degraded mode: when LLM raises LLMUnavailable, worker sets needs_confirmation and creates 3 questions."""
    token = get_token("priya@kharcha.test")
    test_sha = "0505050505050505050505050505050505050505050505050505050505050505"
    ocr_text = "Taj Hotel, Mumbai Date: 2026-10-15 Total: Rs 4500.00 Room stay"

    payload = {
        "sha256": test_sha,
        "mime": "image/jpeg",
        "pages": 1,
        "capture_source": "camera_scan",
        "device_tier": "C",
        "extraction": None,
        "ocr_text": ocr_text,
    }

    res = client.post(
        "/v1/documents",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert res.status_code == 201
    doc_id = res.json()["document_id"]

    # Mock gateway to raise LLMUnavailable
    with patch(
        "app.workers.extract_document.LLMGateway.complete",
        side_effect=LLMUnavailable("Gateway connection timeout"),
    ):
        extract_document_task(doc_id, ocr_text)

    # Check questions and line were generated via regex heuristics
    async with AsyncSessionLocal() as session:
        q_stmt = select(Question).where(
            Question.line_id == ExpenseLine.id,
            ExpenseLine.document_id == uuid.UUID(doc_id),
        )
        q_res = await session.execute(q_stmt)
        questions = q_res.scalars().all()
        assert len(questions) == 3

        q_fields = {q.field: json.loads(q.options) for q in questions}
        assert "total" in q_fields
        assert "date" in q_fields
        assert "vendor" in q_fields

        # Check options pre-fill
        assert "4500" in q_fields["total"][0] or "450000" in q_fields["total"][0]
        assert "2026-10-15" in q_fields["date"][0]
        assert "Taj Hotel" in q_fields["vendor"][0]
