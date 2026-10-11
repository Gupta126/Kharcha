import json
import logging
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from openai import OpenAI
from pydantic import ValidationError

from app.core.settings import settings
from app.db.session import AsyncSessionLocal
from app.models.llm_call import LLMCall
from app.schemas.receipt import ExtractedReceipt

logger = logging.getLogger(__name__)


class TaskAlias(str, Enum):
    EXTRACT_IMAGE = "kh-extract-image"
    EXTRACT_TEXT = "kh-extract-text"
    AGENT = "kh-agent"
    PARSE = "kh-parse"


# Timeouts per alias from SPEC §6:
# kh-extract-image 20 s, kh-extract-text 20 s, kh-agent 8 s, kh-parse 5 s
TIMEOUT_MAP: dict[str, float] = {
    TaskAlias.EXTRACT_IMAGE.value: 20.0,
    TaskAlias.EXTRACT_TEXT.value: 20.0,
    TaskAlias.AGENT.value: 8.0,
    TaskAlias.PARSE.value: 5.0,
}


class LLMUnavailable(HTTPException):
    """Raised when LLM gateway is unreachable, timed out, or exhausted retries (SPEC §6)."""

    def __init__(self, detail: str = "LLM gateway is unavailable"):
        super().__init__(status_code=503, detail=detail)


class LLMGateway:
    """OpenAI-compatible client pointing to LiteLLM proxy at LITELLM_URL.

    - Calls by task alias only (never vendor model name).
    - Enforces timeouts per task alias.
    - Validates JSON against ExtractedReceipt for extraction tasks with ONE repair retry.
    - Respects LLM_MODE=stub using test fixtures without network calls.
    - Logs every attempt to database table llm_calls.
    """

    _last_status: str = "ok"

    def __init__(
        self, base_url: str | None = None, api_key: str | None = None, mode: str | None = None
    ):
        self.base_url = (base_url or settings.LITELLM_URL).rstrip("/")
        if not self.base_url.endswith("/v1"):
            self.api_base = f"{self.base_url}/v1"
        else:
            self.api_base = self.base_url

        self.api_key = api_key or settings.LITELLM_MASTER_KEY or "dummy-key"
        self.mode = mode or settings.LLM_MODE

        self._client: OpenAI | None = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                base_url=self.api_base,
                api_key=self.api_key,
            )
        return self._client

    @classmethod
    def get_last_status(cls) -> str:
        return cls._last_status

    @classmethod
    def set_last_status(cls, status: str) -> None:
        cls._last_status = status

    def _get_stub_fixture(self, task: str) -> dict[str, Any]:
        """Load fixture for stub mode from backend/tests/fixtures/llm/<alias>/*.json."""
        fixtures_dir = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "llm" / task
        if not fixtures_dir.exists():
            raise FileNotFoundError(f"Fixture directory not found for task {task}: {fixtures_dir}")

        json_files = list(fixtures_dir.glob("*.json"))
        if not json_files:
            raise FileNotFoundError(f"No JSON fixtures found in {fixtures_dir}")

        content = json_files[0].read_text(encoding="utf-8")
        return json.loads(content)

    async def log_call(
        self,
        task: str,
        provider: str,
        model: str,
        claim_id: uuid.UUID | None,
        document_id: uuid.UUID | None,
        latency_ms: int,
        tokens_in: int | None,
        tokens_out: int | None,
        success: bool,
        failure: str | None = None,
    ) -> None:
        """Write an entry to llm_calls table."""
        try:
            # We generate a UUID for the call record
            call_id = uuid.uuid4()
            async with AsyncSessionLocal() as session:
                record = LLMCall(
                    id=call_id,
                    provider=provider,
                    model=model,
                    claim_id=claim_id or uuid.uuid4(),  # DB column currently NOT NULL
                    document_id=document_id,
                    latency_ms=latency_ms,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    success=success,
                    failure=failure,
                )
                session.add(record)
                await session.commit()
        except Exception as e:
            logger.warning(f"Failed to log llm_call to database: {e}")

    async def complete(
        self,
        task: str,
        prompt: str,
        system_prompt: str | None = None,
        claim_id: uuid.UUID | None = None,
        document_id: uuid.UUID | None = None,
        validate_schema: bool = True,
    ) -> dict[str, Any]:
        """Execute a completion for a task alias.

        Returns parsed JSON object or validated ExtractedReceipt dictionary.
        """
        valid_aliases = {alias.value for alias in TaskAlias}
        if task not in valid_aliases:
            raise ValueError(f"Invalid task alias: {task}. Must be one of {valid_aliases}")

        timeout = TIMEOUT_MAP.get(task, 15.0)

        # STUB MODE
        if self.mode == "stub":
            start_time = time.monotonic()
            data = self._get_stub_fixture(task)
            latency_ms = int((time.monotonic() - start_time) * 1000)

            # If it's an extraction task, validate against ExtractedReceipt
            if validate_schema and task in (
                TaskAlias.EXTRACT_TEXT.value,
                TaskAlias.EXTRACT_IMAGE.value,
            ):
                try:
                    receipt = ExtractedReceipt.model_validate(data)
                    data = receipt.model_dump()
                except ValidationError as ve:
                    await self.log_call(
                        task=task,
                        provider="nvidia",
                        model="stub",
                        claim_id=claim_id,
                        document_id=document_id,
                        latency_ms=latency_ms,
                        tokens_in=100,
                        tokens_out=100,
                        success=False,
                        failure=str(ve),
                    )
                    raise ve

            await self.log_call(
                task=task,
                provider="nvidia",
                model="stub",
                claim_id=claim_id,
                document_id=document_id,
                latency_ms=latency_ms,
                tokens_in=100,
                tokens_out=100,
                success=True,
                failure=None,
            )
            return data

        # LIVE MODE
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        start_time = time.monotonic()
        tokens_in = 0
        tokens_out = 0
        model_returned = task

        try:
            response = self.client.chat.completions.create(
                model=task,
                messages=messages,
                timeout=timeout,
            )
            latency_ms = int((time.monotonic() - start_time) * 1000)
            if response.usage:
                tokens_in = response.usage.prompt_tokens or 0
                tokens_out = response.usage.completion_tokens or 0
            if response.model:
                model_returned = response.model

            raw_content = response.choices[0].message.content or ""
            raw_content = raw_content.strip()

            # Direct parse
            parsed_data, parse_err = self._parse_json(raw_content)

            # If invalid JSON or failed schema validation, try ONE repair retry
            if parse_err is not None or (
                validate_schema
                and task in (TaskAlias.EXTRACT_TEXT.value, TaskAlias.EXTRACT_IMAGE.value)
                and not self._validate_receipt(parsed_data)[0]
            ):
                err_msg = parse_err or self._validate_receipt(parsed_data)[1]
                logger.info(f"LLM output failed validation ({err_msg}). Initiating 1 repair retry.")

                repair_messages = list(messages)
                repair_messages.append({"role": "assistant", "content": raw_content})
                repair_messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"The response was invalid JSON or failed the schema check: {err_msg}. "
                            "Return ONLY valid corrected JSON matching the schema."
                        ),
                    }
                )

                repair_resp = self.client.chat.completions.create(
                    model=task,
                    messages=repair_messages,
                    timeout=timeout,
                )
                if repair_resp.usage:
                    tokens_in += repair_resp.usage.prompt_tokens or 0
                    tokens_out += repair_resp.usage.completion_tokens or 0
                if repair_resp.model:
                    model_returned = repair_resp.model

                repaired_content = (repair_resp.choices[0].message.content or "").strip()
                parsed_data, parse_err = self._parse_json(repaired_content)

                if parse_err is not None:
                    raise ValueError(f"Repair retry failed to produce valid JSON: {parse_err}")

                if validate_schema and task in (
                    TaskAlias.EXTRACT_TEXT.value,
                    TaskAlias.EXTRACT_IMAGE.value,
                ):
                    is_valid, schema_err = self._validate_receipt(parsed_data)
                    if not is_valid:
                        raise ValueError(f"Repair retry failed schema check: {schema_err}")

            # Successful completion
            await self.log_call(
                task=task,
                provider="nvidia",
                model=model_returned,
                claim_id=claim_id,
                document_id=document_id,
                latency_ms=latency_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                success=True,
                failure=None,
            )
            self.set_last_status("ok")
            return parsed_data

        except Exception as exc:
            latency_ms = int((time.monotonic() - start_time) * 1000)
            self.set_last_status("degraded")
            await self.log_call(
                task=task,
                provider="nvidia",
                model=model_returned,
                claim_id=claim_id,
                document_id=document_id,
                latency_ms=latency_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                success=False,
                failure=str(exc),
            )
            logger.error(f"LLM call for task {task} failed: {exc}")
            raise LLMUnavailable(str(exc)) from exc

    def _parse_json(self, content: str) -> tuple[dict[str, Any] | None, str | None]:
        if not content:
            return None, "Empty response"
        try:
            return json.loads(content), None
        except Exception as e:
            # Strip potential ```json fences if model wrapped them
            cleaned = content
            if cleaned.startswith("```"):
                lines = cleaned.splitlines()
                if len(lines) >= 2 and lines[-1].startswith("```"):
                    cleaned = "\n".join(lines[1:-1]).strip()
            try:
                return json.loads(cleaned), None
            except Exception:
                return None, str(e)

    def _validate_receipt(self, data: dict[str, Any] | None) -> tuple[bool, str | None]:
        if not isinstance(data, dict):
            return False, "Data is not a JSON object"
        try:
            ExtractedReceipt.model_validate(data)
            return True, None
        except ValidationError as ve:
            return False, str(ve)
