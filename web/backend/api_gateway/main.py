# -*- coding: utf-8 -*-
"""
FastAPI 应用主入口 (for testing and modular deployment)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 从同级目录的 routers 子模块中导入所有路由
from .routers import structures

# 可选导入其他路由
try:
    from .routers import simulation
    HAS_SIMULATION = True
except ImportError:
    HAS_SIMULATION = False

try:
    from .routers import simulation_sync
    HAS_SIMULATION_SYNC = True
except ImportError:
    HAS_SIMULATION_SYNC = False

try:
    from .routers import reservoir
    HAS_RESERVOIR = True
except ImportError:
    HAS_RESERVOIR = False

try:
    from .routers import network
    HAS_NETWORK = True
except ImportError:
    HAS_NETWORK = False

try:
    from .routers import analysis
    HAS_ANALYSIS = True
except ImportError:
    HAS_ANALYSIS = False

try:
    from .routers import test_cases
    HAS_TEST_CASES = True
except ImportError:
    HAS_TEST_CASES = False

try:
    from .routers import test_runner
    HAS_TEST_RUNNER = True
except ImportError:
    HAS_TEST_RUNNER = False

app = FastAPI(
    title="HydroClaude API - Refactored",
    description="水力学仿真API服务 - 完整版",
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

# 包含所有可用的路由
# 注意：structures 路由没有内置 prefix，所以需要在这里添加
app.include_router(structures.router, prefix="/api/structures", tags=["structures"])

# 以下路由已经有内置 prefix，不需要再添加
if HAS_SIMULATION:
    app.include_router(simulation.router, tags=["simulations"])

if HAS_SIMULATION_SYNC:
    app.include_router(simulation_sync.router, tags=["simulations-sync"])

if HAS_RESERVOIR:
    app.include_router(reservoir.router, tags=["reservoir"])

if HAS_NETWORK:
    app.include_router(network.router, tags=["network"])

if HAS_ANALYSIS:
    app.include_router(analysis.router, tags=["analysis"])

if HAS_TEST_CASES:
    app.include_router(test_cases.router, tags=["test-cases"])

if HAS_TEST_RUNNER:
    app.include_router(test_runner.router, tags=["test-runner"])

@app.get("/")
async def root():
    """API根端点"""
    available_routers = ["structures"]
    if HAS_SIMULATION:
        available_routers.append("simulations")
    if HAS_SIMULATION_SYNC:
        available_routers.append("simulations-sync")
    if HAS_RESERVOIR:
        available_routers.append("reservoir")
    if HAS_NETWORK:
        available_routers.append("network")
    if HAS_ANALYSIS:
        available_routers.append("analysis")
    if HAS_TEST_CASES:
        available_routers.append("test-cases")
    if HAS_TEST_RUNNER:
        available_routers.append("test-runner")

    return {
        "message": "Welcome to HydroClaude API. Visit /docs for documentation.",
        "api_version": app.version,
        "available_modules": available_routers
    }

