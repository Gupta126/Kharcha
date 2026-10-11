import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.db.session import AsyncSessionLocal
from app.llm.gateway import LLMGateway, LLMUnavailable, TaskAlias
from app.llm.prompts import load_prompt
from app.models.llm_call import LLMCall
from app.schemas.receipt import ExtractedReceipt


@pytest.fixture(autouse=True)
def reset_gateway_status():
    LLMGateway.set_last_status("ok")
    yield
    LLMGateway.set_last_status("ok")


@pytest.mark.asyncio
async def test_gateway_stub_extract_text_success():
    gw = LLMGateway(mode="stub")
    res = await gw.complete(
        task=TaskAlias.EXTRACT_TEXT.value,
        prompt="Sample OCR text",
    )
    assert isinstance(res, dict)
    assert res["doc_type"] == "meal"
    assert res["total"]["value_paise"] == 164000
    # Validate that it complies with ExtractedReceipt schema
    receipt = ExtractedReceipt.model_validate(res)
    assert receipt.total.value_paise == 164000


@pytest.mark.asyncio
async def test_gateway_stub_extract_image_success():
    gw = LLMGateway(mode="stub")
    res = await gw.complete(
        task=TaskAlias.EXTRACT_IMAGE.value,
        prompt="Image base64 representation",
    )
    assert isinstance(res, dict)
    assert res["doc_type"] == "cab"
    receipt = ExtractedReceipt.model_validate(res)
    assert receipt.vendor.value == "Uber India Technologies Pvt Ltd"


@pytest.mark.asyncio
async def test_gateway_stub_agent_success():
    gw = LLMGateway(mode="stub")
    res = await gw.complete(
        task=TaskAlias.AGENT.value,
        prompt="Conversation history",
    )
    assert isinstance(res, dict)
    assert "questions" in res
    assert res["claim_status"] == "needs_info"


@pytest.mark.asyncio
async def test_gateway_stub_parse_success():
    gw = LLMGateway(mode="stub")
    res = await gw.complete(
        task=TaskAlias.PARSE.value,
        prompt="User answer text",
    )
    assert isinstance(res, dict)
    assert "parsed_value" in res
    assert res["parsed_value"]["category"] == "meal"


@pytest.mark.asyncio
async def test_gateway_repair_retry_success():
    """Simulate initial malformed JSON, followed by successful repair response."""
    gw = LLMGateway(mode="live")

    # Load valid receipt fixture text
    fixture_path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "llm"
        / "kh-extract-text"
        / "receipt_valid.json"
    )
    valid_json_text = fixture_path.read_text(encoding="utf-8")

    mock_resp_fail = MagicMock()
    mock_resp_fail.choices = [
        MagicMock(message=MagicMock(content="Here is the json:\n{bad_json..."))
    ]
    mock_resp_fail.usage = MagicMock(prompt_tokens=50, completion_tokens=20)
    mock_resp_fail.model = "kh-extract-text"

    mock_resp_repair = MagicMock()
    mock_resp_repair.choices = [MagicMock(message=MagicMock(content=valid_json_text))]
    mock_resp_repair.usage = MagicMock(prompt_tokens=60, completion_tokens=150)
    mock_resp_repair.model = "kh-extract-text"

    with patch.object(
        gw.client.chat.completions,
        "create",
        side_effect=[mock_resp_fail, mock_resp_repair],
    ) as mock_create:
        res = await gw.complete(
            task=TaskAlias.EXTRACT_TEXT.value,
            prompt="OCR text",
        )
        assert mock_create.call_count == 2
        assert res["total"]["value_paise"] == 164000
        assert gw.get_last_status() == "ok"


@pytest.mark.asyncio
async def test_gateway_repair_retry_failure():
    """Simulate initial bad JSON and failed repair attempt, raising LLMUnavailable."""
    gw = LLMGateway(mode="live")

    mock_resp_fail1 = MagicMock()
    mock_resp_fail1.choices = [MagicMock(message=MagicMock(content="malformed 1"))]
    mock_resp_fail1.usage = MagicMock(prompt_tokens=50, completion_tokens=20)
    mock_resp_fail1.model = "kh-extract-text"

    mock_resp_fail2 = MagicMock()
    mock_resp_fail2.choices = [MagicMock(message=MagicMock(content="still malformed 2"))]
    mock_resp_fail2.usage = MagicMock(prompt_tokens=50, completion_tokens=20)
    mock_resp_fail2.model = "kh-extract-text"

    with patch.object(
        gw.client.chat.completions,
        "create",
        side_effect=[mock_resp_fail1, mock_resp_fail2],
    ):
        with pytest.raises(LLMUnavailable):
            await gw.complete(
                task=TaskAlias.EXTRACT_TEXT.value,
                prompt="OCR text",
            )
        assert gw.get_last_status() == "degraded"


@pytest.mark.asyncio
async def test_gateway_timeout_raises_llm_unavailable():
    """Simulate network timeout raising LLMUnavailable."""
    gw = LLMGateway(mode="live")

    import httpx

    with patch.object(
        gw.client.chat.completions,
        "create",
        side_effect=httpx.TimeoutException("Read timed out"),
    ):
        with pytest.raises(LLMUnavailable):
            await gw.complete(
                task=TaskAlias.EXTRACT_TEXT.value,
                prompt="OCR text",
            )
        assert gw.get_last_status() == "degraded"


@pytest.mark.asyncio
async def test_gateway_connection_error_raises_llm_unavailable():
    """Simulate connection refused raising LLMUnavailable."""
    gw = LLMGateway(mode="live")

    import httpx

    with patch.object(
        gw.client.chat.completions,
        "create",
        side_effect=httpx.ConnectError("Connection refused"),
    ):
        with pytest.raises(LLMUnavailable):
            await gw.complete(
                task=TaskAlias.AGENT.value,
                prompt="prompt",
            )
        assert gw.get_last_status() == "degraded"


@pytest.mark.asyncio
async def test_gateway_writes_llm_calls_row():
    """Check that llm_calls entry is logged in the database with all fields."""
    from sqlalchemy import select

    gw = LLMGateway(mode="stub")
    claim_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    await gw.complete(
        task=TaskAlias.EXTRACT_TEXT.value,
        prompt="Sample OCR text",
        claim_id=claim_id,
        document_id=doc_id,
    )

    # Query the db to verify insertion and assert every field
    async with AsyncSessionLocal() as session:
        query = select(LLMCall).where(LLMCall.claim_id == claim_id)
        result = await session.execute(query)
        record = result.scalars().first()

        assert record is not None
        assert record.task == TaskAlias.EXTRACT_TEXT.value
        assert record.provider == "nvidia"
        assert record.model == "stub"
        assert record.claim_id == claim_id
        assert record.document_id == doc_id
        assert isinstance(record.latency_ms, int) and record.latency_ms >= 0
        assert record.tokens_in == 100
        assert record.tokens_out == 100
        assert record.success is True
        assert record.failure is None
        assert record.created_at is not None


def test_prompt_loader_extract_text():
    prompt = load_prompt("extract_text_v1", schema="SCHEMA_JSON", ocr_text="SOME OCR TEXT")
    assert "SCHEMA_JSON" in prompt
    assert "SOME OCR TEXT" in prompt
    assert "You extract data from one Indian receipt or invoice." in prompt


def test_no_vendor_model_names_in_backend_app():
    """Ensure no forbidden vendor model names exist anywhere in backend/app."""
    import re

    app_dir = Path(__file__).resolve().parents[1] / "app"
    forbidden = re.compile(r"(llama|nemotron|mistral|qwen|gpt-4|claude-3)", re.IGNORECASE)

    matches = []
    for p in app_dir.rglob("*.py"):
        text = p.read_text(encoding="utf-8")
        if forbidden.search(text):
            matches.append(str(p))

    assert not matches, f"Forbidden vendor model names found in: {matches}"
