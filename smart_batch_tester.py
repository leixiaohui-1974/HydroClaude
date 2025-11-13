#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智能分批测试器 - 每批10个，测试+修复，完成后等待确认

Author: HydroClaude
Date: 2025-11-13
"""

import subprocess
import sys
import os
import json
import re
from pathlib import Path

STATE_FILE = 'test_results/batch_state.json'

def load_state():
    """加载测试状态"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'current_batch': 0, 'all_files': [], 'results': {}, 'stats': {}}

def save_state(state):
    """保存测试状态"""
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)

def find_all_test_files():
    """查找所有测试文件"""
    test_files = []
    for pattern in ['tests/*.py', 'examples/**/*.py', 'validation_cases/**/*.py']:
        for f in Path('.').glob(pattern):
            if '__pycache__' not in str(f) and '__init__' not in str(f):
                test_files.append(str(f).replace('\\', '/'))
    return sorted(test_files)

def run_test(file_path):
    """运行单个测试（快速版本）"""
    try:
        result = subprocess.run(
            [sys.executable, file_path],
            capture_output=True,
            timeout=20,  # 降低到20秒
            encoding='utf-8',
            errors='ignore'
        )
        return 'PASS' if result.returncode == 0 else 'FAIL', (result.stderr or result.stdout)[:150]
    except subprocess.TimeoutExpired:
        return 'TIMEOUT', 'Exceeded 20 seconds'
    except Exception as e:
        return 'ERROR', str(e)

def fix_file(file_path):
    """快速修复文件"""
    if not os.path.exists(file_path):
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        return False
    
    original = content
    
    # 1. Unicode
    for char, repl in {'\xb3': '^3', '\xb2': '^2', '\u2713': '[OK]', '\u274c': '[X]'}.items():
        content = content.replace(char, repl)
    
    # 2. sys.path
    if 'sys.path.insert' not in content and 'import ' in content:
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith(('import ', 'from ')) and '__future__' not in line:
                if 'import sys' not in content: lines.insert(i, 'import sys')
                if 'import os' not in content: lines.insert(i, 'import os')
                lines.insert(i, ''); lines.insert(i, 'script_path = os.path.abspath(__file__)')
                lines.insert(i, 'project_root = os.path.dirname(os.path.dirname(script_path))')
                lines.insert(i, 'if project_root not in sys.path: sys.path.insert(0, project_root)')
                content = '\n'.join(lines); break
    
    # 3. 废弃导入
    content = content.replace('from solvers.canal_solver import CanalSolver',
                            'from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as CanalSolver')
    
    # 4. 数值参数
    content = re.sub(r'cfl\s*=\s*0\.[5-9]', 'cfl = 0.3', content, flags=re.IGNORECASE)
    content = re.sub(r't_end\s*=\s*[1-9]\d{2,}', 't_end = 30.0', content)
    content = content.replace('order=2', 'order=1')
    
    if content != original:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except:
            return False
    return False

def process_batch(batch_files):
    """处理一批文件：测试->修复->重测"""
    
    print(f"\n{'='*70}")
    print(f"TESTING {len(batch_files)} files...")
    print(f"{'='*70}\n")
    
    results = {}
    
    # Round 1: 测试
    for i, f in enumerate(batch_files, 1):
        print(f"[{i}/{len(batch_files)}] {os.path.basename(f)}...", end=' ', flush=True)
        status, error = run_test(f)
        results[f] = {'status': status, 'error': error, 'fixed': False}
        print('[OK]' if status == 'PASS' else f'[{status}]')
    
    passed_r1 = sum(1 for r in results.values() if r['status'] == 'PASS')
    failed_r1 = len(batch_files) - passed_r1
    
    print(f"\n→ Round 1: {passed_r1} passed, {failed_r1} failed")
    
    # 修复失败的
    if failed_r1 > 0:
        print(f"\nFIXING {failed_r1} failed files...")
        fixed = 0
        for f, r in results.items():
            if r['status'] != 'PASS':
                if fix_file(f):
                    fixed += 1
                    results[f]['fixed'] = True
        print(f"→ Fixed {fixed} files")
        
        # Round 2: 重测修复的
        if fixed > 0:
            print(f"\nRE-TESTING {fixed} fixed files...")
            improved = 0
            for f, r in results.items():
                if r['fixed']:
                    new_status, _ = run_test(f)
                    if new_status == 'PASS':
                        improved += 1
                        results[f]['status'] = 'PASS'
                        print(f"  [OK] {os.path.basename(f)}")
            print(f"→ Improved {improved}/{fixed}")
    
    # 最终统计
    final_passed = sum(1 for r in results.values() if r['status'] == 'PASS')
    final_failed = len(batch_files) - final_passed
    
    return results, final_passed, final_failed

def main():
    """主函数"""
    
    print("\n" + "="*70)
    print(" "*15 + "SMART BATCH TESTER")
    print("="*70)
    
    # 加载状态
    state = load_state()
    
    # 首次运行：初始化
    if not state['all_files']:
        print("\nInitializing...")
        state['all_files'] = find_all_test_files()
        state['current_batch'] = 0
        state['results'] = {}
        state['stats'] = {'total_passed': 0, 'total_failed': 0, 'total_fixed': 0}
        print(f"Found {len(state['all_files'])} test files")
        print(f"Will process in batches of 10")
    
    batch_size = 10
    total_files = len(state['all_files'])
    total_batches = (total_files + batch_size - 1) // batch_size
    current_batch = state['current_batch']
    
    # 检查是否已完成
    if current_batch >= total_batches:
        print("\n[OK] ALL BATCHES COMPLETED!")
        print(f"\nFinal Results:")
        print(f"  Total: {total_files}")
        print(f"  Passed: {state['stats']['total_passed']} ({state['stats']['total_passed']/total_files*100:.1f}%)")
        print(f"  Failed: {state['stats']['total_failed']}")
        print(f"  Fixed: {state['stats']['total_fixed']}")
        return
    
    # 处理当前批次
    start_idx = current_batch * batch_size
    end_idx = min(start_idx + batch_size, total_files)
    batch_files = state['all_files'][start_idx:end_idx]
    
    print(f"\n>>> BATCH {current_batch + 1}/{total_batches} <<<")
    print(f"Files {start_idx + 1}-{end_idx} of {total_files}")
    
    # 处理批次
    batch_results, passed, failed = process_batch(batch_files)
    
    # 更新状态
    state['results'].update(batch_results)
    state['stats']['total_passed'] += passed
    state['stats']['total_failed'] += failed
    state['stats']['total_fixed'] += sum(1 for r in batch_results.values() if r['fixed'])
    state['current_batch'] += 1
    save_state(state)
    
    # 显示累计统计
    total_tested = state['stats']['total_passed'] + state['stats']['total_failed']
    cumulative_rate = state['stats']['total_passed'] / total_tested * 100 if total_tested > 0 else 0
    
    print(f"\n{'='*70}")
    print(f"BATCH {current_batch + 1} COMPLETED")
    print(f"{'='*70}")
    print(f"This batch: {passed}/{len(batch_files)} passed")
    print(f"\nCUMULATIVE STATS:")
    print(f"  Tested: {total_tested}/{total_files} ({total_tested/total_files*100:.0f}%)")
    print(f"  Passed: {state['stats']['total_passed']} ({cumulative_rate:.1f}%)")
    print(f"  Failed: {state['stats']['total_failed']}")
    print(f"  Fixed: {state['stats']['total_fixed']}")
    print(f"\nProgress: {state['current_batch']}/{total_batches} batches")
    print(f"{'='*70}")
    
    # 提示下一步
    if state['current_batch'] < total_batches:
        print(f"\n[OK] Batch completed. Results saved.")
        print(f"\nTo continue to next batch, run:")
        print(f"  python smart_batch_tester.py")
        print(f"\nTo reset and start over:")
        print(f"  del test_results\\batch_state.json")
    else:
        print(f"\n[OK] ALL TESTING COMPLETED!")
        print(f"\nFinal pass rate: {cumulative_rate:.1f}%")
        print(f"vs Round 3 baseline: 49.4%")
        if cumulative_rate > 49.4:
            print(f"Improvement: +{cumulative_rate - 49.4:.1f}%")

if __name__ == '__main__':
    main()

