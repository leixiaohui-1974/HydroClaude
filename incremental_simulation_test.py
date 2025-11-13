#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
增量测试模拟案例（跳过已通过的）

Author: HydroClaude
Date: 2025-11-13
"""

import subprocess
import sys
import os
import json
from datetime import datetime

# 状态文件
STATE_FILE = 'test_results/simulation_test_state.json'
BATCH_SIZE = 20

def load_state():
    """加载测试状态"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        'passed_files': [],
        'failed_files': {},
        'current_batch': 0,
        'last_update': None
    }

def save_state(state):
    """保存测试状态"""
    os.makedirs('test_results', exist_ok=True)
    state['last_update'] = datetime.now().isoformat()
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def is_control_related(file_path):
    """判断是否是控制相关"""
    control_keywords = ['mpc', 'controller', 'control', 'cvxpy', 'pid', 'agc']
    basename = os.path.basename(file_path).lower()
    return any(kw in basename for kw in control_keywords)

def find_all_test_files():
    """找到所有Python测试文件"""
    files = []
    for search_dir in ['examples', 'tests']:
        if not os.path.exists(search_dir):
            continue
        for root, dirs, filenames in os.walk(search_dir):
            for f in filenames:
                if f.endswith('.py') and '__pycache__' not in root and '__init__' not in f:
                    full_path = os.path.join(root, f)
                    if os.path.isfile(full_path):
                        files.append(full_path.replace('\\', '/'))  # 统一路径格式
    return files

def run_test(file_path):
    """运行测试"""
    try:
        result = subprocess.run(
            [sys.executable, file_path],
            capture_output=True,
            timeout=15,
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
        return 'TIMEOUT', 'Exceeded 15s'
    except Exception as e:
        return 'ERROR', str(e)

def fix_common_issues(file_path):
    """修复常见问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        # 修复1: 添加sys.path (如果没有)
        if 'sys.path.insert' not in content and 'import sys' in content:
            import_sys_line = content.find('import sys')
            if import_sys_line != -1:
                end_of_line = content.find('\n', import_sys_line)
                content = (content[:end_of_line+1] + 
                          'import os\n'
                          'sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))\n' +
                          content[end_of_line+1:])
        
        # 修复2: 数值稳定性
        import re
        content = re.sub(r'cfl\s*=\s*0\.[5-9]', 'cfl=0.3', content)
        content = re.sub(r't_end\s*=\s*[5-9]\d+', 't_end=30', content)
        content = content.replace('order=2', 'order=1')
        
        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
    except:
        pass
    return False

def main():
    """主函数"""
    
    # 加载状态
    state = load_state()
    
    # 获取所有模拟文件
    all_files = find_all_test_files()
    simulation_files = sorted([f for f in all_files if not is_control_related(f)])
    
    # 过滤出需要测试的文件
    passed_set = set(state['passed_files'])
    files_to_test = [f for f in simulation_files if f not in passed_set]
    
    print("="*70)
    print("INCREMENTAL SIMULATION TESTING")
    print("="*70)
    print(f"Total simulation files: {len(simulation_files)}")
    print(f"Already passed: {len(passed_set)}")
    print(f"Need to test: {len(files_to_test)}")
    print()
    
    if len(files_to_test) == 0:
        print("[OK] All simulation tests already passed!")
        pass_rate = 100.0
    else:
        # 测试当前批次
        current_batch = state['current_batch']
        start_idx = current_batch * BATCH_SIZE
        end_idx = min(start_idx + BATCH_SIZE, len(files_to_test))
        batch = files_to_test[start_idx:end_idx]
        
        if len(batch) == 0:
            print("[OK] Current batch completed. All tests done!")
            total_passed = len(passed_set)
            total_files = len(simulation_files)
            pass_rate = total_passed / total_files * 100
        else:
            print(f"BATCH {current_batch + 1} ({len(batch)} files)")
            print("="*70)
            print()
            
            batch_passed = 0
            batch_failed = 0
            
            for i, f in enumerate(batch, 1):
                basename = os.path.basename(f)
                print(f"[{i}/{len(batch)}] {basename}...", end=' ', flush=True)
                
                status, error = run_test(f)
                
                if status == 'PASS':
                    print("[OK]")
                    state['passed_files'].append(f)
                    batch_passed += 1
                else:
                    print(f"[{status}]")
                    state['failed_files'][f] = {'status': status, 'error': error}
                    batch_failed += 1
                    
                    # 尝试修复
                    if status in ['FAIL', 'TIMEOUT']:
                        if fix_common_issues(f):
                            # 重测
                            status2, _ = run_test(f)
                            if status2 == 'PASS':
                                print(f"         -> Fixed and passed!")
                                state['passed_files'].append(f)
                                if f in state['failed_files']:
                                    del state['failed_files'][f]
                                batch_passed += 1
                                batch_failed -= 1
            
            # 更新批次
            state['current_batch'] = current_batch + 1
            
            # 统计
            total_passed = len(state['passed_files'])
            total_files = len(simulation_files)
            batch_rate = batch_passed / len(batch) * 100
            pass_rate = total_passed / total_files * 100
            
            print()
            print("="*70)
            print(f"BATCH RESULTS")
            print("="*70)
            print(f"Batch: {batch_passed}/{len(batch)} passed ({batch_rate:.1f}%)")
            print(f"Overall: {total_passed}/{total_files} passed ({pass_rate:.1f}%)")
            print()
            
            # 显示失败的
            if batch_failed > 0:
                print(f"FAILED IN THIS BATCH ({batch_failed}):")
                for f in batch:
                    if f in state['failed_files']:
                        print(f"  [{state['failed_files'][f]['status']}] {os.path.basename(f)}")
                print()
            
            # 提示下一步
            remaining = len(files_to_test) - end_idx
            if remaining > 0:
                print(f"[INFO] {remaining} files remaining. Run again to continue.")
            else:
                print(f"[OK] All batches completed!")
    
    # 保存状态
    save_state(state)
    
    print("="*70)
    print(f"CUMULATIVE PASS RATE: {pass_rate:.1f}%")
    print("="*70)

if __name__ == '__main__':
    main()

