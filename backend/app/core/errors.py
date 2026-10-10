import logging
import traceback
from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


# Error response schema matching SPEC §2
def create_error_response(
    code: str, message: str, details: dict[str, Any] | None = None, status_code: int = 400
) -> JSONResponse:
    """Create a standardized error response per SPEC §2."""
    error_content = {"error": {"code": code, "message": message, "details": details or {}}}
    return JSONResponse(status_code=status_code, content=error_content)


# Exception classes for different error types
class NotFoundError(HTTPException):
    def __init__(self, detail: str, headers: dict[str, Any] | None = None):
        super().__init__(status_code=404, detail=detail, headers=headers)


class ValidationError(HTTPException):
    def __init__(self, detail: str, headers: dict[str, Any] | None = None):
        super().__init__(status_code=422, detail=detail, headers=headers)


class IllegalTransitionError(HTTPException):
    def __init__(self, detail: str, headers: dict[str, Any] | None = None):
        super().__init__(status_code=409, detail=detail, headers=headers)


class NotEntitledError(HTTPException):
    def __init__(self, detail: str, headers: dict[str, Any] | None = None):
        super().__init__(status_code=403, detail=detail, headers=headers)


class DuplicateDocumentError(HTTPException):
    def __init__(self, detail: str, headers: dict[str, Any] | None = None):
        super().__init__(status_code=409, detail=detail, headers=headers)


class LlmUnavailableError(HTTPException):
    def __init__(self, detail: str, headers: dict[str, Any] | None = None):
        super().__init__(status_code=503, detail=detail, headers=headers)


class ErpUnavailableError(HTTPException):
    def __init__(self, detail: str, headers: dict[str, Any] | None = None):
        super().__init__(status_code=503, detail=detail, headers=headers)


class UnauthorizedError(HTTPException):
    def __init__(self, detail: str, headers: dict[str, Any] | None = None):
        super().__init__(status_code=401, detail=detail, headers=headers)


class ForbiddenError(HTTPException):
    def __init__(self, detail: str, headers: dict[str, Any] | None = None):
        super().__init__(status_code=403, detail=detail, headers=headers)


# Exception handlers
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTPException and convert to standardized error format."""
    # If detail is already in our error format, return as-is
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    # Otherwise, wrap in standard format
    error_code_map = {
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "ILLEGAL_TRANSITION",  # Default for 409, can be overridden
        422: "VALIDATION_FAILED",
        503: "ERP_UNAVAILABLE",  # Default for 503, can be overridden
    }

    code = error_code_map.get(exc.status_code, "VALIDATION_FAILED")
    return create_error_response(code=code, message=str(exc.detail), status_code=exc.status_code)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors from request parsing."""
    return create_error_response(
        code="VALIDATION_FAILED",
        message="Invalid input data",
        details={"validation_errors": exc.errors()},
        status_code=422,
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    logger.error(traceback.format_exc())
    return create_error_response(
        code="VALIDATION_FAILED",  # Generic fallback
        message="Internal server error",
        status_code=500,
    )


# Map of exception classes to handlers
exception_handlers = {
    HTTPException: http_exception_handler,
    StarletteHTTPException: http_exception_handler,
    RequestValidationError: validation_exception_handler,
    Exception: general_exception_handler,
}
