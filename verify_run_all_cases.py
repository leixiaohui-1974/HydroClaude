#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证run_all_cases.py的实际退出码

Author: HydroClaude
Date: 2025-11-13
"""

import subprocess
import sys
import os

file_path = 'examples/case_library/run_all_cases.py'

result = subprocess.run(
    [sys.executable, file_path],
    capture_output=True,
    timeout=120,
    encoding='utf-8',
    errors='ignore',
    env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
)

print(f"Return code: {result.returncode}")
print(f"\nLast 5 lines of stdout:")
stdout_lines = result.stdout.strip().split('\n')
for line in stdout_lines[-5:]:
    print(f"  {line}")

if result.stderr:
    print(f"\nStderr present: YES (length={len(result.stderr)})")
    stderr_lines = result.stderr.strip().split('\n')
    if len(stderr_lines) > 0:
        print(f"Last stderr line: {stderr_lines[-1]}")
else:
    print(f"\nStderr present: NO")

print(f"\nFinal status: {'PASS' if result.returncode == 0 else 'FAIL'}")

