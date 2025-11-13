#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""解析第三轮测试进度"""

import re
from pathlib import Path

log_file = Path("test_results/batch_test_output_v3.txt")

if not log_file.exists():
    print("[ERROR] 日志文件不存在")
    exit(1)

content = log_file.read_text(encoding='utf-8', errors='ignore')
lines = content.split('\n')

# 统计
total_lines = len(lines)
progress_lines = [l for l in lines if '/541]' in l]
pass_lines = [l for l in lines if 'PASS' in l and '耗时' in l]
fail_lines = [l for l in lines if 'FAIL' in l and ('错误码' in l or '超时' in l)]

current = len(progress_lines)
passes = len(pass_lines)
fails = len(fail_lines)

print("="*60)
print("第三轮测试实时进度")
print("="*60)
print(f"进度: {current}/541 ({current/541*100:.1f}%)")
print(f"通过: {passes}")
print(f"失败: {fails}")
print(f"总测试: {passes+fails}")

if passes + fails > 0:
    pass_rate = passes / (passes + fails) * 100
    print(f"当前通过率: {pass_rate:.2f}%")
    
    print(f"\n对比:")
    print(f"  第一轮: 19.6%")
    print(f"  第二轮: 18.9%")
    print(f"  第三轮 (当前): {pass_rate:.2f}%")
    
    if pass_rate > 19.6:
        improvement = pass_rate - 19.6
        print(f"  提升: +{improvement:.1f}% ⬆️")
    else:
        decline = 19.6 - pass_rate
        print(f"  下降: -{decline:.1f}% ⬇️")

# 预估剩余时间
if current > 0 and current < 541:
    avg_time = 4  # 秒每测试
    remaining_tests = 541 - current
    remaining_minutes = (remaining_tests * avg_time) / 60
    print(f"\n预计剩余时间: {remaining_minutes:.0f} 分钟")

print("="*60)

# 显示最近3个测试
if progress_lines:
    print(f"\n最近的测试结果:")
    for line in progress_lines[-3:]:
        # 提取测试编号
        match = re.search(r'\[(\d+)/541\]', line)
        if match:
            num = match.group(1)
            print(f"  [{num}/541] {line[20:80].strip()}")

