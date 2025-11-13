#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整自动化Pipeline
从当前状态自动执行到100%目标
"""

import os
import sys
import time
import subprocess
from pathlib import Path

os.environ['PYTHONIOENCODING'] = 'utf-8'

def wait_for_test_completion(log_file, timeout_minutes=180):
    """等待测试完成"""
    
    print(f"等待测试完成...")
    print(f"日志文件: {log_file}")
    print(f"超时时间: {timeout_minutes} 分钟")
    print(f"\n按 Ctrl+C 可以中断等待\n")
    
    start_time = time.time()
    last_progress = 0
    
    while True:
        if time.time() - start_time > timeout_minutes * 60:
            print(f"\n[TIMEOUT] 等待超时")
            return False
        
        if not Path(log_file).exists():
            time.sleep(10)
            continue
        
        try:
            import re
            content = Path(log_file).read_bytes().decode('utf-16-le', errors='ignore')
            
            nums = [int(m.group(1)) for m in re.finditer(r'\[(\d+)/541\]', content)]
            current = max(nums) if nums else 0
            
            if current > last_progress:
                passes = content.count('PASS')
                fails = content.count('FAIL')
                rate = passes / (passes + fails) * 100 if (passes + fails) > 0 else 0
                
                print(f"\r[{current}/541] Pass: {passes} Fail: {fails} Rate: {rate:.1f}%", 
                      end='', flush=True)
                last_progress = current
            
            if current >= 541:
                print(f"\n\n[OK] 测试完成！")
                return True
        
        except Exception as e:
            pass
        
        time.sleep(15)

def run_phase(phase_num, script_name, description):
    """运行Phase"""
    
    print(f"\n{'='*70}")
    print(f"Phase {phase_num}: {description}")
    print(f"{'='*70}\n")
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=False,
            text=True,
            env=os.environ
        )
        
        if result.returncode == 0:
            print(f"\n[OK] Phase {phase_num} 完成")
            return True
        else:
            print(f"\n[WARN] Phase {phase_num} 返回码: {result.returncode}")
            return False
    
    except Exception as e:
        print(f"\n[ERROR] Phase {phase_num} 失败: {e}")
        return False

def main():
    print("="*70)
    print("HydroClaude 完整自动化Pipeline")
    print("="*70)
    print("\n目标: 从当前状态达到100%测试通过率")
    print("\nPipeline:")
    print("  1. 等待第三轮测试完成")
    print("  2. Phase 2: 深度数值优化")
    print("  3. Phase 3: 边界情况处理")
    print("  4. 第四轮完整测试")
    print("  5. Phase 4: 结果验证")
    print("  6. 生成最终报告")
    
    response = input("\n是否开始自动化执行? (y/n): ").lower()
    
    if response != 'y':
        print("\n[取消] 自动化Pipeline已取消")
        print("您可以手动执行各个Phase")
        return
    
    print("\n" + "="*70)
    print("开始自动化Pipeline")
    print("="*70)
    
    # Step 1: 等待第三轮测试完成
    print("\n[Step 1/6] 等待第三轮测试完成...")
    
    log_v3 = 'test_results/batch_test_output_v3.txt'
    
    if Path(log_v3).exists():
        completed = wait_for_test_completion(log_v3)
        
        if not completed:
            print("\n[WARN] 测试未完成，继续下一步可能不准确")
            response = input("是否继续? (y/n): ").lower()
            if response != 'y':
                return
    else:
        print(f"[WARN] 第三轮测试日志不存在: {log_v3}")
        print("跳过等待，直接执行Phase 2-4")
    
    # Step 2: Phase 2
    print("\n[Step 2/6] 执行Phase 2: 深度数值优化")
    run_phase(2, 'phase2_deep_numerical_optimization.py', '深度数值优化')
    
    # Step 3: Phase 3
    print("\n[Step 3/6] 执行Phase 3: 边界情况处理")
    run_phase(3, 'phase3_boundary_cases.py', '边界情况处理')
    
    # Step 4: 第四轮测试
    print("\n[Step 4/6] 执行第四轮完整测试")
    print("\n启动测试...")
    
    log_v4 = 'test_results/batch_test_output_v4.txt'
    
    # 启动测试（后台）
    with open(log_v4, 'w', encoding='utf-8') as f:
        process = subprocess.Popen(
            [sys.executable, 'batch_test_all_cases.py'],
            stdout=f,
            stderr=subprocess.STDOUT,
            encoding='utf-8',
            env=os.environ
        )
    
    print(f"测试进程已启动 (PID: {process.pid})")
    
    # 等待完成
    completed = wait_for_test_completion(log_v4)
    
    if not completed:
        print("\n[WARN] 第四轮测试超时")
    
    # Step 5: Phase 4
    print("\n[Step 5/6] 执行Phase 4: 结果验证")
    run_phase(4, 'phase4_validate_all_results.py', '结果验证')
    
    # Step 6: 生成最终报告
    print("\n[Step 6/6] 生成最终报告")
    
    print("\n" + "="*70)
    print("Pipeline 完成")
    print("="*70)
    
    print("\n请查看:")
    print("  - test_results/batch_test_output_v4.txt (第四轮测试日志)")
    print("  - test_results/validation_report.json (验证报告)")
    
    print("\n" + "="*70)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[中断] Pipeline已中断")
        print("您可以继续手动执行剩余步骤")

