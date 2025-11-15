"""
HydroClaude Web API Gateway
FastAPI application entry point for hydraulic simulation management
"""

# ========== 关键：首先应用Windows编码补丁 ==========
# 必须在其他任何导入之前执行
import encoding_patch  # 自动修复Windows GBK编码问题

# ========== 设置环境变量，确保后台任务也能找到模块 ==========
import os
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
current_pythonpath = os.environ.get('PYTHONPATH', '')
if backend_dir not in current_pythonpath:
    os.environ['PYTHONPATH'] = f"{backend_dir}:{current_pythonpath}" if current_pythonpath else backend_dir

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import uvicorn

# Add project root and api_gateway to Python path
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
api_gateway_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, api_gateway_dir)

import logging

# Import routers
from routers import simulation_router
from routers import test_cases
from routers import test_runner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="HydroClaude Web API",
    description="Water Hydraulics Management System - Professional simulation platform for open channel and pressurized flow",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS middleware configuration
# Allow frontend development server to access API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # React dev server
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(simulation_router)
app.include_router(test_cases.router)
app.include_router(test_runner.router)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler to catch all unhandled exceptions
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )


# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint for monitoring
    Returns server status and basic system information
    """
    return {
        "status": "healthy",
        "service": "HydroClaude Web API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


# Root endpoint
@app.get("/", tags=["System"])
async def root():
    """
    Root endpoint with API information
    """
    return {
        "service": "HydroClaude Web API",
        "version": "1.0.0",
        "description": "Water Hydraulics Management System",
        "docs": "/api/docs",
        "health": "/health",
        "timestamp": datetime.now().isoformat()
    }


# Engine information endpoint
@app.get("/api/v1/engine/info", tags=["System"])
async def get_engine_info():
    """
    Get HydroClaude engine information
    """
    import sys
    import os

    # Add backend path for core module
    backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    # Import engine
    from core.hydraulic_engine import HydraulicEngine

    engine = HydraulicEngine()
    return engine.get_engine_info()


# Startup event
@app.on_event("startup")
async def startup_event():
    """
    Application startup event
    Initialize connections and resources
    """
    logger.info("=" * 60)
    logger.info("HydroClaude Web API Starting...")
    logger.info("=" * 60)
    logger.info("Service: HydroClaude Web API")
    logger.info("Version: 1.0.0")
    logger.info("Documentation: http://localhost:8000/api/docs")
    logger.info("=" * 60)

    # Initialize database
    import sys
    import os
    backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    from shared.database import init_db
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event
    Cleanup resources
    """
    logger.info("HydroClaude Web API shutting down...")


# Development server
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )
