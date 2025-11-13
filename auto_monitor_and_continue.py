#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动监控测试进度，完成后自动执行后续Phase
"""

import time
import re
from pathlib import Path
import subprocess
import sys
import os

os.environ['PYTHONIOENCODING'] = 'utf-8'

def check_test_completion():
    """检查测试是否完成"""
    
    log_file = Path("test_results/batch_test_output_v3.txt")
    
    if not log_file.exists():
        return False, 0, 0, 0
    
    content = log_file.read_text(encoding='utf-8', errors='ignore')
    
    # 查找进度
    progress_matches = re.findall(r'\[(\d+)/541\]', content)
    current = int(progress_matches[-1]) if progress_matches else 0
    
    # 统计结果
    pass_lines = [l for l in content.split('\n') if 'PASS' in l and '耗时' in l]
    fail_lines = [l for l in content.split('\n') if 'FAIL' in l and ('错误码' in l or '超时' in l)]
    
    passes = len(pass_lines)
    fails = len(fail_lines)
    
    is_complete = current >= 541
    
    return is_complete, current, passes, fails

def display_progress(current, passes, fails):
    """显示进度"""
    
    total = passes + fails
    pass_rate = passes / total * 100 if total > 0 else 0
    
    progress_bar = "=" * int(current / 541 * 50)
    progress_bar += " " * (50 - len(progress_bar))
    
    print(f"\r[{progress_bar}] {current}/541 | Pass: {passes} | Fail: {fails} | Rate: {pass_rate:.1f}%", 
          end='', flush=True)

def main():
    print("="*70)
    print("自动监控与后续执行")
    print("="*70)
    print("\n[Phase] 监控第三轮测试进度...")
    print("完成后将自动执行 Phase 2-4\n")
    
    last_current = 0
    check_interval = 10  # 秒
    
    while True:
        is_complete, current, passes, fails = check_test_completion()
        
        if current > last_current:
            display_progress(current, passes, fails)
            last_current = current
        
        if is_complete:
            print("\n\n" + "="*70)
            print("[OK] 第三轮测试完成！")
            print("="*70)
            
            total = passes + fails
            pass_rate = passes / total * 100 if total > 0 else 0
            
            print(f"\n最终结果:")
            print(f"  总计: 541")
            print(f"  通过: {passes} ({pass_rate:.2f}%)")
            print(f"  失败: {fails}")
            
            print(f"\n对比:")
            print(f"  第一轮: 19.6%")
            print(f"  第二轮: 18.9%")
            print(f"  第三轮: {pass_rate:.2f}%")
            
            improvement = pass_rate - 19.6
            if improvement > 0:
                print(f"  提升: +{improvement:.1f}% ⬆️")
            
            # 询问是否继续Phase 2
            print("\n" + "="*70)
            print("准备执行 Phase 2: 深度数值稳定性优化")
            print("="*70)
            
            response = input("\n是否立即执行 Phase 2? (y/n): ").lower()
            
            if response == 'y':
                print("\n[执行] Phase 2...")
                subprocess.run([sys.executable, 'phase2_deep_numerical_optimization.py'])
                
                print("\n[完成] Phase 2 执行完毕")
                print("\n建议:")
                print("  1. 运行快速验证: python quick_test_sample.py -n 100")
                print("  2. 或运行完整第四轮测试: python batch_test_all_cases.py")
            else:
                print("\n[跳过] Phase 2")
                print("您可以稍后手动执行: python phase2_deep_numerical_optimization.py")
            
            break
        
        time.sleep(check_interval)
    
    print("\n" + "="*70)
    print("监控结束")
    print("="*70)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[中断] 监控已停止")
        print("测试仍在后台运行，您可以:")
        print("  1. 检查进度: python parse_round3_progress.py")
        print("  2. 继续监控: python auto_monitor_and_continue.py")

