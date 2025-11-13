#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""快速检查测试状态"""

import re
from pathlib import Path

log_file = Path("test_results/batch_test_output_v3.txt")

if not log_file.exists():
    print("[INFO] 测试尚未开始或日志文件不存在")
    print(f"  文件: {log_file}")
    exit(0)

try:
    content = log_file.read_text(encoding='utf-8', errors='ignore')
    
    # 提取进度
    progress_matches = re.findall(r'\[(\d+)/541\]', content)
    current = int(progress_matches[-1]) if progress_matches else 0
    
    # 统计结果
    passes = len(re.findall(r'通过 PASS', content))
    fails = len(re.findall(r'失败 FAIL', content))
    total = passes + fails
    
    print("="*60)
    print("第三轮测试状态")
    print("="*60)
    print(f"进度: {current}/541 ({current/541*100:.1f}%)")
    print(f"通过: {passes}")
    print(f"失败: {fails}")
    
    if total > 0:
        pass_rate = passes / total * 100
        print(f"当前通过率: {pass_rate:.2f}%")
        
        print(f"\n对比:")
        print(f"  第一轮: 19.6%")
        print(f"  第二轮: 18.9%")
        print(f"  第三轮: {pass_rate:.2f}% {'[提升]' if pass_rate > 19.6 else '[下降]'}")
    
    print("="*60)
    
    # 估算剩余时间
    if current > 0 and current < 541:
        avg_time_per_test = 4  # 秒
        remaining = (541 - current) * avg_time_per_test / 60
        print(f"预计剩余时间: {remaining:.1f} 分钟")
    elif current >= 541:
        print("[OK] 测试已完成！")
    
except Exception as e:
    print(f"[ERROR] {e}")

