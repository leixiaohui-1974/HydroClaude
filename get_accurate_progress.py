#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""获取准确的测试进度"""

import re
from pathlib import Path

log_file = Path("test_results/batch_test_output_v3.txt")

if not log_file.exists():
    print("日志文件不存在")
    exit(1)

# 读取文件
with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# 统计进度
lines = content.split('\n')

# 方法1: 查找包含[X/541]的行
progress_lines = [l for l in lines if '/541]' in l]
current = len(progress_lines)

# 方法2: 使用正则提取最大数字
progress_numbers = re.findall(r'\[(\d+)/541\]', content)
if progress_numbers:
    current_max = max([int(n) for n in progress_numbers])
else:
    current_max = 0

# 统计PASS和FAIL
pass_count = 0
fail_count = 0

for line in lines:
    if '通过 PASS' in line or 'PASS (' in line:
        pass_count += 1
    if '失败 FAIL' in line or 'FAIL (' in line:
        fail_count += 1

print("="*60)
print("第三轮测试准确进度")
print("="*60)
print(f"进度: {current_max}/541 ({current_max/541*100:.1f}%)")
print(f"通过: {pass_count}")
print(f"失败: {fail_count}")
print(f"总测试: {pass_count+fail_count}")

if pass_count + fail_count > 0:
    pass_rate = pass_count / (pass_count + fail_count) * 100
    print(f"当前通过率: {pass_rate:.2f}%")
    
    print(f"\n对比:")
    print(f"  第一轮: 19.6%")
    print(f"  第三轮: {pass_rate:.2f}%")
    
    if pass_rate > 19.6:
        print(f"  提升: +{pass_rate-19.6:.1f}% ⬆️⬆️")
    elif pass_rate < 19.6:
        print(f"  下降: -{19.6-pass_rate:.1f}% ⬇️")
    else:
        print(f"  持平")

# 预估剩余时间
if 0 < current_max < 541:
    remaining = 541 - current_max
    avg_time = 4  # 秒每测试
    remaining_minutes = (remaining * avg_time) / 60
    print(f"\n预计剩余时间: {remaining_minutes:.0f} 分钟")

print("="*60)

# 显示最近的测试
print(f"\n最近的5个测试:")
for line in progress_lines[-5:]:
    if '/541]' in line:
        # 提取测试编号和名称
        match = re.search(r'\[(\d+)/541\]\s*测试:\s*(.{0,50})', line)
        if match:
            num = match.group(1)
            name = match.group(2).strip()
            print(f"  [{num}/541] {name}")

