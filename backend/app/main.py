from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.errors import exception_handlers

app = FastAPI(
    title="Kharcha API",
    description="Expense reimbursement system API",
    version="0.1.0",
)

# Register exception handlers
for exc_type, handler in exception_handlers.items():
    app.add_exception_handler(exc_type, handler)

app.include_router(health_router, prefix="/v1")
