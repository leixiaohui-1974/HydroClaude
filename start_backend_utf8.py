#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
UTF-8编码启动脚本 - 解决Windows GBK编码问题
"""

import sys
import os
import io

# 强制设置UTF-8编码
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

# 重定向stdout和stderr为UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 切换到后端目录
backend_dir = os.path.join(os.path.dirname(__file__), 'web', 'backend', 'api_gateway')
os.chdir(backend_dir)

# 启动uvicorn
import uvicorn

print("=" * 60)
print(" Starting HydroClaude Web Backend")
print(" Encoding: UTF-8")
print(" Platform: " + sys.platform)
print("=" * 60)

uvicorn.run(
    "main:app",
    host="0.0.0.0",
    port=8000,
    reload=True,
    log_level="info"
)






