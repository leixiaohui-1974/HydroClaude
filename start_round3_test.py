#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""启动第三轮测试"""

import os
import sys
import subprocess
from pathlib import Path
import time

# 设置UTF-8环境
os.environ['PYTHONIOENCODING'] = 'utf-8'

log_file = Path("test_results/batch_test_output_v3.txt")

# 检查是否已经在运行
if log_file.exists():
    size = log_file.stat().st_size
    mtime = time.ctime(log_file.stat().st_mtime)
    print(f"日志文件已存在")
    print(f"  大小: {size} bytes")
    print(f"  修改时间: {mtime}")
    
    if size > 1000:  # 如果文件有内容
        print("\n测试可能已经在运行或已完成")
        print("运行 'python check_test_status.py' 查看详情")
        sys.exit(0)
    else:
        print("\n日志文件为空，重新启动测试...")
        log_file.unlink()

# 启动测试
print("\n" + "="*60)
print("启动第三轮完整测试 (541个案例)")
print("="*60)
print("\n预期时间: 35-40分钟")
print("预期通过率: 50-65%")
print("\n测试开始...\n")

# 运行测试
with open(log_file, 'w', encoding='utf-8') as f:
    process = subprocess.Popen(
        [sys.executable, 'batch_test_all_cases.py'],
        stdout=f,
        stderr=subprocess.STDOUT,
        encoding='utf-8',
        env=os.environ
    )

print(f"测试进程已启动 (PID: {process.pid})")
print(f"日志文件: {log_file}")
print(f"\n监控命令:")
print(f"  python check_test_status.py")
print(f"\n等待5秒后检查启动状态...")

time.sleep(5)

# 检查是否成功启动
if log_file.exists() and log_file.stat().st_size > 0:
    print(f"\n[OK] 测试已成功启动！")
    print(f"  日志文件大小: {log_file.stat().st_size} bytes")
else:
    print(f"\n[WARN] 测试可能未成功启动，请手动检查")

