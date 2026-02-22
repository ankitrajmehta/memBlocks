"""
memBlocks FastAPI Backend - Main Application Entry Point

A RESTful API wrapper for the memBlocks memory management system.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path FIRST (before any imports from parent)
backend_dir = Path(__file__).resolve().parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))

# NOW import from parent directory
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from services.user_service import user_service
from services.block_service import block_service
from vector_db.mongo_manager import mongo_manager
from vector_db.vector_db_manager import VectorDBManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import routers
from backend.routers import (
    users_router,
    blocks_router,
    chat_router,
    memory_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager - handles startup and shutdown.
    """
    import sys
    import io

    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

    print("\n[START] Starting memBlocks FastAPI Backend...")
    print("=" * 50)

    try:
        await mongo_manager._client.admin.command("ping")
        print("[OK] MongoDB: Connected")
    except Exception as e:
        print(f"[WARN] MongoDB: Not reachable - {e}")
        print("   Endpoints requiring MongoDB will return errors until it's available.")

    try:
        VectorDBManager.get_client()
        print("[OK] Qdrant: Connected")
    except Exception as e:
        print(f"[WARN] Qdrant: Not reachable - {e}")
        print("   Endpoints requiring Qdrant will return errors until it's available.")

    print("[OK] All services initialized successfully")
    print("=" * 50)
    print(f"\nAPI Documentation: http://localhost:80001/docs")
    print(f"Health Check: http://localhost:80001/health")
    print(f"Settings: {settings.model_dump()}\n")

    yield

    print("\n[STOP] Shutting down memBlocks FastAPI Backend...")


# Create FastAPI application
app = FastAPI(
    title="memBlocks API",
    description="RESTful API for the memBlocks intelligent memory management system",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite default
        "http://localhost:3000",  # React default
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(users_router)
app.include_router(blocks_router)
app.include_router(chat_router)
app.include_router(memory_router)


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint - API information."""
    return {
        "name": "memBlocks API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint - verifies all services are operational.
    """
    health_status = {"status": "healthy", "services": {}}

    # Check MongoDB
    try:
        await mongo_manager._client.admin.command("ping")
        health_status["services"]["mongodb"] = "connected"
    except Exception as e:
        health_status["services"]["mongodb"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # Check Qdrant
    try:
        VectorDBManager.get_client()
        health_status["services"]["qdrant"] = "connected"
    except Exception as e:
        health_status["services"]["qdrant"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    status_code = (
        status.HTTP_200_OK
        if health_status["status"] == "healthy"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return JSONResponse(content=health_status, status_code=status_code)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for unhandled errors.
    """
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc),
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        reload_dirs=[str(backend_dir)],
        log_level="info",
    )
