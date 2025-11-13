#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Windows环境专用的服务器启动脚本
彻底解决编码问题
"""

import sys
import os
import io
import warnings

# ========== 第1步：强制设置UTF-8编码 ==========
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

# Windows下重定向所有输出到UTF-8
if sys.platform == 'win32':
    # 重定向stdout和stderr
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer,
        encoding='utf-8',
        errors='replace',
        line_buffering=True
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer,
        encoding='utf-8',
        errors='replace',
        line_buffering=True
    )

# ========== 第2步：禁用所有警告 ==========
warnings.filterwarnings('ignore')

# ========== 第3步：配置日志系统 ==========
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# 禁用uvicorn的默认日志器，使用我们自己的
for logger_name in ['uvicorn', 'uvicorn.access', 'uvicorn.error']:
    logger = logging.getLogger(logger_name)
    logger.handlers = []
    logger.propagate = False

print("="*60)
print(" HydroClaude Web Backend Server")
print(" Windows UTF-8 Compatible Mode")
print(" Platform:", sys.platform)
print(" Encoding:", sys.stdout.encoding)
print("="*60)

# ========== 第4步：启动服务器 ==========
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="warning",  # 降低日志级别
        access_log=False,  # 禁用访问日志
        use_colors=False   # 禁用颜色输出
    )






