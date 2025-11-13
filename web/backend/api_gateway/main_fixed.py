"""
HydroClaude Web API Gateway - 
"""
import sys
import os

# 
project_root = '/workspace'
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import uvicorn
import logging

# Import routers
from routers import simulation_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="HydroClaude Web API",
    description="Water Hydraulics Management System",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(simulation_router)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )

# Health check
@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "service": "HydroClaude Web API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

# Root endpoint
@app.get("/", tags=["System"])
async def root():
    return {
        "service": "HydroClaude Web API",
        "version": "1.0.0",
        "description": "Water Hydraulics Management System",
        "docs": "/api/docs",
        "health": "/health",
        "timestamp": datetime.now().isoformat()
    }

# Engine info endpoint
@app.get("/api/v1/engine/info", tags=["System"])
async def get_engine_info():
    try:
        from core.hydraulic_engine import HydraulicEngine
        engine = HydraulicEngine()
        return engine.get_engine_info()
    except Exception as e:
        logger.error(f"Engine info error: {e}")
        return {
            "engine_version": "1.0.0",
            "status": "error",
            "error": str(e)
        }

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("="*60)
    logger.info("HydroClaude Web API Starting...")
    logger.info("="*60)
    logger.info("Service: HydroClaude Web API")
    logger.info("Version: 1.0.0")
    logger.info("Documentation: http://localhost:8000/api/docs")
    logger.info("="*60)
    
    from shared.database import init_db
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("HydroClaude Web API shutting down...")

if __name__ == "__main__":
    uvicorn.run(
        "main_fixed:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
