"""
FastAPI application initialization and configuration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import get_settings
from app.database import init_db
from app.api import routes

# Configure logging
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Devin GitHub Issues Automation",
    description="Orchestrator for automating GitHub issue triaging and execution with Devin AI",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database and other resources on startup."""
    logger.info("Starting Devin GitHub Issues Automation Orchestrator")
    logger.info(f"Initializing database...")
    init_db()
    logger.info("Database initialized successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown."""
    logger.info("Shutting down Devin GitHub Issues Automation Orchestrator")


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "service": "Devin GitHub Issues Automation",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Include API routes
app.include_router(routes.router, prefix="/api/v1", tags=["automation"])

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.api.main:app",
        host=settings.orchestrator_host,
        port=settings.orchestrator_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
