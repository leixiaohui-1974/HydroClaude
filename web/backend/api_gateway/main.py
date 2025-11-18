# -*- coding: utf-8 -*-
"""
FastAPI 应用主入口 (for testing and modular deployment)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 从同级目录的 routers 子模块中导入 structures 路由
from .routers import structures

app = FastAPI(
    title="HydroClaude API - Refactored",
    description="水力学仿真API服务",
    version="2.2.0-service-layer"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含 structures 路由
app.include_router(structures.router, prefix="/api/structures")

@app.get("/")
async def root():
    return {
        "message": "Welcome to HydroClaude API. Visit /docs for documentation.",
        "api_version": app.version
    }

