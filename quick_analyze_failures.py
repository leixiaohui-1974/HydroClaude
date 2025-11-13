#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""快速分析失败案例"""

import json
from pathlib import Path
from collections import Counter

# 读取第一轮测试结果
results_file = Path("test_results/batch_test_results.json")
if not results_file.exists():
    print("[ERROR] batch_test_results.json not found")
    exit(1)

with open(results_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

results = data.get('results', [])

print(f"\n总测试数: {len(results)}")

# 统计状态
statuses = Counter(r['status'] for r in results)
print(f"\n状态分布:")
for status, count in statuses.items():
    print(f"  {status}: {count}")

# 先看看error字段的格式
print(f"\n失败案例的error字段示例（前3个）:")
failed_cases = [r for r in results if r['status'] in ['failed', 'error']]
for i, case in enumerate(failed_cases[:3], 1):
    error = case.get('error', 'No error message')
    print(f"  {i}. {error[:100]}")

# 统计各种错误类型
error_patterns = Counter()
for r in failed_cases:
    error = r.get('error', '')
    if 'Exit code' in error:
        # 提取exit code
        import re
        match = re.search(r'Exit code:\s*(\d+)', error)
        if match:
            code = match.group(1)
            error_patterns[f'Exit code {code}'] += 1
        else:
            error_patterns['Exit code (unknown)'] += 1
    elif 'ModuleNotFoundError' in error:
        error_patterns['ModuleNotFoundError'] += 1
    elif 'ImportError' in error:
        error_patterns['ImportError'] += 1
    elif 'timeout' in error.lower():
        error_patterns['Timeout'] += 1
    else:
        error_patterns['Other'] += 1

print(f"\n错误类型分布:")
for error_type, count in error_patterns.most_common():
    print(f"  {error_type}: {count} ({count/len(failed_cases)*100:.1f}%)")

