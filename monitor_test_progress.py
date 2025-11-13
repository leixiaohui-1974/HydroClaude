#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
实时监控批量测试进度
"""
import time
import json
from pathlib import Path
from datetime import datetime

def check_progress():
    """检查测试进度"""
    results_file = Path("test_results/batch_test_results.json")
    
    if not results_file.exists():
        print("[WARN] Results file not found")
        return None
    
    try:
        with open(results_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'results' not in data:
            return None
        
        results = data['results']
        total = len(results)
        success = sum(1 for r in results if r['status'] == 'success')
        failed = sum(1 for r in results if r['status'] == 'failed')
        error = sum(1 for r in results if r['status'] == 'error')
        
        return {
            'total': total,
            'success': success,
            'failed': failed,
            'error': error,
            'progress': total / 541 * 100,
            'pass_rate': success / total * 100 if total > 0 else 0
        }
    except Exception as e:
        print(f"[ERROR] {e}")
        return None

def main():
    print("="*70)
    print("批量测试进度监控器 - Batch Test Progress Monitor")
    print("="*70)
    print("按 Ctrl+C 停止监控\n")
    
    last_total = 0
    start_time = time.time()
    
    try:
        while True:
            stats = check_progress()
            
            if stats:
                # 清屏（简单方式）
                print("\n" + "="*70)
                print(f"更新时间: {datetime.now().strftime('%H:%M:%S')}")
                print("="*70)
                print(f"进度: {stats['total']}/541 ({stats['progress']:.1f}%)")
                print(f"成功: {stats['success']} ({stats['pass_rate']:.1f}%)")
                print(f"失败: {stats['failed']}")
                print(f"错误: {stats['error']}")
                
                # 计算速度
                if stats['total'] > last_total:
                    elapsed = time.time() - start_time
                    speed = stats['total'] / elapsed if elapsed > 0 else 0
                    remaining = (541 - stats['total']) / speed if speed > 0 else 0
                    print(f"\n速度: {speed:.2f} cases/min")
                    print(f"预计剩余时间: {remaining/60:.1f} min")
                    last_total = stats['total']
                
                # 检查是否完成
                if stats['total'] >= 541:
                    print("\n[OK] 批量测试已完成！")
                    print(f"总耗时: {(time.time() - start_time)/60:.1f} min")
                    break
            else:
                print("等待测试开始...")
            
            time.sleep(10)  # 每10秒检查一次
    
    except KeyboardInterrupt:
        print("\n\n[INFO] 监控已停止")

if __name__ == '__main__':
    main()
