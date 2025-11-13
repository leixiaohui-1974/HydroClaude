#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动检测测试完成并运行分析
"""
import time
import subprocess
import re
from pathlib import Path

def check_test_complete():
    """检查测试是否完成"""
    log_file = Path("test_results/batch_test_output_v2.txt")
    
    if not log_file.exists():
        return False, 0, 0
    
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    pass_count = len(re.findall(r'PASS \(', content))
    fail_count = len(re.findall(r'FAIL \(', content))
    total = pass_count + fail_count
    
    return total >= 541, total, pass_count

def run_analyses():
    """运行所有分析"""
    print("\n" + "="*70)
    print("测试完成！开始自动分析...")
    print("="*70 + "\n")
    
    analyses = [
        ("finalize_test_round.py", "生成最终报告"),
        ("compare_test_rounds.py", "对比两轮结果"),
        ("analyze_failure_patterns.py", "分析失败模式"),
    ]
    
    for script, description in analyses:
        print(f"\n[{description}]")
        print("-" * 70)
        try:
            result = subprocess.run(
                ["python", script],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            print(result.stdout)
            if result.stderr:
                print("Errors:", result.stderr)
        except Exception as e:
            print(f"Error running {script}: {e}")
    
    print("\n" + "="*70)
    print("所有分析完成！")
    print("="*70)
    print("\n查看结果:")
    print("  - cat test_results/round2_final_report.md")
    print("  - cat test_results/comparison_report.json")
    print("  - cat test_results/failure_analysis.json")
    print("")

def main():
    print("等待测试完成...")
    print("按 Ctrl+C 停止监控\n")
    
    last_total = 0
    
    try:
        while True:
            complete, total, passed = check_test_complete()
            
            if total > last_total:
                progress = total / 541 * 100
                pass_rate = passed / total * 100 if total > 0 else 0
                print(f"\rProgress: {total}/541 ({progress:.1f}%) | Pass: {passed} ({pass_rate:.1f}%)", end='', flush=True)
                last_total = total
            
            if complete:
                print("\n\n测试完成！")
                print(f"最终结果: {passed}/{total} ({passed/total*100:.1f}%)")
                
                # 自动运行分析
                run_analyses()
                break
            
            time.sleep(5)  # 每5秒检查一次
    
    except KeyboardInterrupt:
        print("\n\n监控已停止")
        if last_total > 0:
            print(f"当前进度: {last_total}/541")

if __name__ == '__main__':
    main()

