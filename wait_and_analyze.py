#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
等待测试完成并进行完整分析
"""
import time
import re
from pathlib import Path
from datetime import datetime

def parse_log(log_file):
    """解析日志文件"""
    if not Path(log_file).exists():
        return None
    
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 统计PASS和FAIL
    pass_matches = re.findall(r'PASS \(', content)
    fail_matches = re.findall(r'FAIL \(', content)
    
    # 找到最后的测试编号
    test_numbers = re.findall(r'\[(\d+)/541\]', content)
    current = int(test_numbers[-1]) if test_numbers else 0
    
    return {
        'current': current,
        'passed': len(pass_matches),
        'failed': len(fail_matches),
        'total': 541
    }

def main():
    log_file = "test_results/batch_test_output_v2.txt"
    
    print("="*70)
    print("等待测试完成 - Waiting for Test Completion")
    print("="*70)
    print("\n按 Ctrl+C 停止监控\n")
    
    last_current = 0
    start_time = time.time()
    last_update_time = start_time
    
    try:
        while True:
            stats = parse_log(log_file)
            
            if not stats:
                print("等待日志文件...")
                time.sleep(10)
                continue
            
            current_time = time.time()
            
            # 清屏效果
            print("\n" + "="*70)
            print(f"更新时间: {datetime.now().strftime('%H:%M:%S')}")
            print("="*70)
            
            # 显示进度
            progress = stats['current'] / stats['total'] * 100
            bar_length = 50
            filled = int(bar_length * stats['current'] / stats['total'])
            bar = '█' * filled + '░' * (bar_length - filled)
            
            print(f"\n进度: [{bar}] {stats['current']}/{stats['total']} ({progress:.1f}%)")
            print(f"\n已通过: {stats['passed']} 个")
            print(f"已失败: {stats['failed']} 个")
            
            if stats['current'] > 0:
                pass_rate = stats['passed'] / stats['current'] * 100
                print(f"通过率: {pass_rate:.1f}%")
                
                # 与第一轮对比
                print(f"\n对比第一轮:")
                print(f"  第一轮: 19.6%")
                print(f"  当前: {pass_rate:.1f}%")
                diff = pass_rate - 19.6
                if diff > 0:
                    print(f"  改进: +{diff:.1f}% [OK]")
                elif diff < 0:
                    print(f"  下降: {diff:.1f}% [WARN]")
                else:
                    print(f"  持平 [INFO]")
            
            # 计算速度和预估时间
            if stats['current'] > last_current:
                time_diff = current_time - last_update_time
                cases_diff = stats['current'] - last_current
                speed = cases_diff / time_diff * 60  # cases per minute
                remaining = stats['total'] - stats['current']
                eta_minutes = remaining / speed if speed > 0 else 0
                
                print(f"\n速度: {speed:.1f} cases/min")
                print(f"预计剩余: {eta_minutes:.1f} 分钟")
                
                last_current = stats['current']
                last_update_time = current_time
            
            # 检查是否完成
            if stats['current'] >= stats['total']:
                elapsed = (current_time - start_time) / 60
                print(f"\n[SUCCESS] 测试完成!")
                print(f"总耗时: {elapsed:.1f} 分钟")
                print(f"\n最终结果:")
                print(f"  通过: {stats['passed']} ({stats['passed']/stats['total']*100:.1f}%)")
                print(f"  失败: {stats['failed']} ({stats['failed']/stats['total']*100:.1f}%)")
                
                # 生成下一步建议
                print("\n" + "="*70)
                print("下一步操作:")
                print("="*70)
                print("\n1. 运行完整分析:")
                print("   python analyze_test_results.py")
                print("\n2. 对比两轮结果:")
                print("   python compare_test_rounds.py")
                print("\n3. 如果通过率<19.6%，考虑回滚:")
                print("   python rollback_and_fix_properly.py")
                print("\n4. 如果通过率>19.6%，查看改进的案例:")
                print("   python identify_improvements.py")
                print("")
                break
            
            time.sleep(15)  # 每15秒更新一次
            
    except KeyboardInterrupt:
        print("\n\n[INFO] 监控已停止")
        print(f"当前进度: {stats['current']}/{stats['total']}")

if __name__ == '__main__':
    main()
