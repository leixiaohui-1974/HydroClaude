"""
HydroClaude Web API Gateway - Simplified Version
FastAPI application entry point for hydraulic simulation management
"""

import os
import sys

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, project_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="HydroClaude API",
    description="水力学仿真API服务 - Hydraulic Simulation API",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import only structures router (the main one we need)
try:
    # Try direct import first
    from api_gateway.routers import structures
    app.include_router(structures.router, prefix="/api/structures", tags=["structures"])
    logger.info("✅ Structures router loaded")
except Exception as e:
    logger.warning(f"⚠️ Failed to load structures router: {e}")
    # Create a minimal fallback router
    from fastapi import APIRouter
    router = APIRouter()
    
    @router.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0"
        }
    
    app.include_router(router, prefix="/api/structures", tags=["structures"])
    logger.info("✅ Fallback router loaded")

@app.get("/")
async def root():
    return {
        "name": "HydroClaude API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "api_base": "/api/structures"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting HydroClaude API Server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
