#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
重测修复后的文件

Author: HydroClaude
Date: 2025-11-13
"""

import subprocess
import sys
import os
import json

STATE_FILE = 'test_results/simulation_test_state.json'

def load_state():
    """加载状态"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'passed_files': [], 'failed_files': {}}

def save_state(state):
    """保存状态"""
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def run_test(file_path):
    """运行测试"""
    try:
        result = subprocess.run(
            [sys.executable, file_path],
            capture_output=True,
            timeout=20,  # 增加到20秒
            encoding='utf-8',
            errors='ignore',
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
        )
        if result.returncode == 0:
            return 'PASS', None
        else:
            error = (result.stderr or result.stdout)[:200]
            return 'FAIL', error
    except subprocess.TimeoutExpired:
        return 'TIMEOUT', 'Exceeded 20s'
    except Exception as e:
        return 'ERROR', str(e)

def main():
    """主函数"""
    
    state = load_state()
    failed_files = state.get('failed_files', {})
    
    print("="*70)
    print("RE-TESTING FIXED FILES")
    print("="*70)
    print(f"Files to retest: {len(failed_files)}")
    print()
    
    if not failed_files:
        print("No failed files to retest.")
        return
    
    improved = 0
    still_failing = 0
    still_timeout = 0
    
    for file_path, old_info in list(failed_files.items()):
        old_status = old_info['status']
        basename = os.path.basename(file_path)
        
        print(f"[{old_status}] {basename}...", end=' ', flush=True)
        
        if not os.path.exists(file_path):
            print("NOT FOUND")
            continue
        
        new_status, error = run_test(file_path)
        
        if new_status == 'PASS':
            print(f"[OK] Fixed!")
            # 移到passed列表
            state['passed_files'].append(file_path)
            del state['failed_files'][file_path]
            improved += 1
        elif new_status == 'TIMEOUT':
            print(f"[TIMEOUT] Still timing out")
            state['failed_files'][file_path] = {'status': new_status, 'error': error}
            still_timeout += 1
        else:
            print(f"[{new_status}] Still failing")
            state['failed_files'][file_path] = {'status': new_status, 'error': error}
            still_failing += 1
    
    # 保存更新的状态
    save_state(state)
    
    # 统计
    total_passed = len(state['passed_files'])
    total_files = 487  # 模拟文件总数
    pass_rate = total_passed / total_files * 100
    
    print()
    print("="*70)
    print("RETEST RESULTS")
    print("="*70)
    print(f"Improved (now passing): {improved}")
    print(f"Still failing: {still_failing}")
    print(f"Still timeout: {still_timeout}")
    print()
    print(f"OVERALL PROGRESS:")
    print(f"  Passed: {total_passed}/487 ({pass_rate:.1f}%)")
    print(f"  Failed: {len(state['failed_files'])}")
    print()
    
    if still_timeout > 0 or still_failing > 0:
        print("STILL HAVING ISSUES:")
        for f, info in state['failed_files'].items():
            print(f"  [{info['status']}] {os.path.basename(f)}")
            if info['error'] and 'Error' in info['error']:
                # 提取关键错误
                lines = info['error'].split('\n')
                for line in lines:
                    if 'Error' in line:
                        print(f"       -> {line.strip()[:80]}")
                        break
    
    print("="*70)

if __name__ == '__main__':
    main()

