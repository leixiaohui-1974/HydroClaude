#!/usr/bin/env python3
"""
直接启动脚本 - 确保导入路径正确
"""
import sys
import os

# 设置正确的路径
backend_dir = os.path.dirname(os.path.abspath(__file__))
web_dir = os.path.dirname(backend_dir)
project_root = os.path.dirname(web_dir)

sys.path.insert(0, project_root)
sys.path.insert(0, backend_dir)
sys.path.insert(0, web_dir)

print(f"项目根目录: {project_root}")
print(f"Backend目录: {backend_dir}")
print(f"Web目录: {web_dir}")
print()

# 验证导入
print("验证核心模块导入...")
try:
    from core.hydraulic_engine_v2 import HydraulicEngineV2
    print("✅ HydraulicEngineV2 导入成功")
    engine = HydraulicEngineV2()
    print(f"✅ 引擎初始化成功 (版本: {engine.version})")
except Exception as e:
    print(f"❌ 引擎导入失败: {e}")
    sys.exit(1)

print()
print("启动FastAPI服务器...")
print("="*60)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="HydroClaude API",
    description="水力学仿真API服务",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 导入structures路由
try:
    from api_gateway.routers import structures
    app.include_router(structures.router, prefix="/api")
    print("✅ Structures路由加载成功")
    print(f"   路由数量: {len(structures.router.routes)}")
except Exception as e:
    print(f"❌ Structures路由加载失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

@app.get("/")
async def root():
    return {
        "name": "HydroClaude API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    from datetime import datetime
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    print("="*60)
    print("🚀 服务器启动在 http://0.0.0.0:8000")
    print("📚 API文档: http://0.0.0.0:8000/docs")
    print("="*60)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
