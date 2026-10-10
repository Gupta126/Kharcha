from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from .api.health import router as health_router
from .api.erp import router as erp_router
from .api.employees import router as employees_router
from .api.reimbursements import router as reimbursements_router
from .api.admin import router as admin_router
from .core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Kharcha Mock ERP Service",
    description="Mock ERP service for expense reimbursement system",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, tags=["health"])
app.include_router(erp_router, prefix="/erp", tags=["erp"])
app.include_router(employees_router)
app.include_router(reimbursements_router)
app.include_router(admin_router, prefix="/admin", tags=["admin"])

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Mock ERP Service...")
    logger.info(f"Server will run on {settings.HOST}:{settings.PORT}")
    logger.info(f"Employees file: {settings.EMPLOYEES_FILE}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Mock ERP Service...")


# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "Kharcha Mock ERP",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health"
    }
