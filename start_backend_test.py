#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试后端启动
"""

import sys
import os

# 切换到正确的目录
os.chdir("E:/OneDrive/Documents/GitHub/Test/HydroClaude/web/backend/api_gateway")
sys.path.insert(0, os.getcwd())

print("="*60)
print(" Testing Backend Startup")
print("="*60)
print(f"Working directory: {os.getcwd()}")
print(f"Python path: {sys.executable}")

# 测试编码补丁
print("\n[1] Testing encoding patch...")
try:
    import encoding_patch
    print("[OK] Encoding patch loaded")
except Exception as e:
    print(f"[X] Failed to load encoding patch: {e}")
    sys.exit(1)

# 测试主模块
print("\n[2] Testing main module...")
try:
    import main
    print("[OK] Main module loaded")
    print(f"[OK] App instance: {main.app}")
except Exception as e:
    print(f"[X] Failed to load main: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 启动uvicorn
print("\n[3] Starting uvicorn...")
try:
    import uvicorn
    print("[OK] Starting server on http://0.0.0.0:8000")
    print("="*60)
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # 禁用reload以便调试
        log_level="info"
    )
except Exception as e:
    print(f"[X] Failed to start server: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)




