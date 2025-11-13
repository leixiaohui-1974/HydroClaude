#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析失败模式 - 识别需要优化的场景
"""
import json
import re
from pathlib import Path
from collections import defaultdict

def load_test_results():
    """加载测试结果"""
    results_file = Path("test_results/batch_test_results.json")
    
    if not results_file.exists():
        print("[ERROR] Results file not found")
        return None
    
    with open(results_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def categorize_failures(results):
    """按失败原因分类"""
    categories = defaultdict(list)
    
    for result in results.get('results', []):
        if result['status'] in ['failed', 'error']:
            error = result.get('error', '')
            
            # 分类失败原因
            if 'ModuleNotFoundError' in error or 'ImportError' in error:
                categories['import_error'].append(result)
            elif 'UnicodeEncodeError' in error:
                categories['unicode_error'].append(result)
            elif 'TimeoutError' in error or 'timeout' in error.lower():
                categories['timeout'].append(result)
            elif 'Exit code: 1' in error or 'Exit code:1' in error:
                categories['exit_code_1'].append(result)
            elif 'RuntimeError' in error:
                categories['runtime_error'].append(result)
            elif 'ValueError' in error:
                categories['value_error'].append(result)
            elif 'AssertionError' in error:
                categories['assertion_error'].append(result)
            else:
                categories['other'].append(result)
    
    return categories

def identify_optimization_candidates(categories):
    """识别需要优化的候选场景"""
    candidates = []
    
    # Exit code 1通常是数值稳定性问题，优先级最高
    if categories.get('exit_code_1'):
        for result in categories['exit_code_1'][:10]:  # 取前10个
            candidates.append({
                'file': result['file_path'],
                'issue': 'Numerical instability (exit code 1)',
                'priority': 'HIGH',
                'suggested_fix': [
                    'Lower CFL number',
                    'Reduce dt_max',
                    'Increase grid resolution',
                    'Use 1st order scheme',
                    'Adjust initial conditions'
                ]
            })
    
    # Runtime错误可能是边界条件或参数问题
    if categories.get('runtime_error'):
        for result in categories['runtime_error'][:5]:
            candidates.append({
                'file': result['file_path'],
                'issue': 'Runtime error',
                'priority': 'MEDIUM',
                'suggested_fix': [
                    'Check boundary conditions',
                    'Validate parameter ranges',
                    'Add error handling'
                ]
            })
    
    # 超时可能需要性能优化
    if categories.get('timeout'):
        for result in categories['timeout'][:5]:
            candidates.append({
                'file': result['file_path'],
                'issue': 'Timeout (>60s)',
                'priority': 'MEDIUM',
                'suggested_fix': [
                    'Reduce simulation time',
                    'Increase dt_max',
                    'Reduce grid resolution',
                    'Enable numba JIT'
                ]
            })
    
    return candidates

def generate_optimization_script(candidates):
    """生成优化脚本"""
    script = f"""#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
自动优化失败场景
基于失败模式分析，自动调整参数
Generated: {Path.ctime(Path(__file__))}
'''

import sys
import os
import json

sys.path.insert(0, os.path.abspath('.'))

# 需要优化的场景
OPTIMIZATION_TARGETS = [
"""
    
    for i, candidate in enumerate(candidates):
        script += f"""    {{
        'id': {i},
        'file': '{candidate['file']}',
        'issue': '{candidate['issue']}',
        'priority': '{candidate['priority']}'
    }},
"""
    
    script += """]

def optimize_numerical_stability(config):
    '''优化数值稳定性'''
    optimized = config.copy()
    
    # 降低CFL
    if 'cfl' in optimized:
        optimized['cfl'] = min(optimized['cfl'], 0.3)
    
    # 减小时间步
    if 'dt_max' in optimized:
        optimized['dt_max'] = min(optimized['dt_max'], 0.2)
    
    # 使用一阶精度
    if 'order' in optimized:
        optimized['order'] = 1
    
    # 增加网格分辨率
    if 'n_cells' in optimized:
        optimized['n_cells'] = int(optimized['n_cells'] * 1.2)
    
    return optimized

def optimize_timeout(config):
    '''优化超时问题'''
    optimized = config.copy()
    
    # 缩短模拟时间
    if 't_end' in optimized:
        optimized['t_end'] = min(optimized['t_end'], 60.0)
    
    # 增大时间步
    if 'dt_max' in optimized:
        optimized['dt_max'] = min(optimized['dt_max'] * 1.5, 1.0)
    
    # 启用numba
    if 'use_numba' in optimized:
        optimized['use_numba'] = True
    
    return optimized

def main():
    print("="*70)
    print("自动场景优化 - Automatic Scenario Optimization")
    print("="*70)
    print(f"\\nOptimizing {len(OPTIMIZATION_TARGETS)} scenarios...\\n")
    
    for target in OPTIMIZATION_TARGETS:
        print(f"[{target['id']}] {target['file']}")
        print(f"    Issue: {target['issue']}")
        print(f"    Priority: {target['priority']}")
        print()

if __name__ == '__main__':
    main()
"""
    
    return script

def main():
    print("="*70)
    print("失败模式分析 - Failure Pattern Analysis")
    print("="*70)
    
    print("\n[1/4] 加载测试结果...")
    data = load_test_results()
    if not data:
        return
    
    total = len(data.get('results', []))
    failed = sum(1 for r in data['results'] if r['status'] in ['failed', 'error'])
    print(f"[OK] 总测试: {total}, 失败: {failed}")
    
    print("\n[2/4] 分类失败原因...")
    categories = categorize_failures(data)
    
    print("\n失败分类:")
    for category, items in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  - {category}: {len(items)} 个")
    
    print("\n[3/4] 识别优化候选...")
    candidates = identify_optimization_candidates(categories)
    print(f"[OK] 识别出 {len(candidates)} 个优化候选")
    
    print("\n优化优先级:")
    high_priority = [c for c in candidates if c['priority'] == 'HIGH']
    medium_priority = [c for c in candidates if c['priority'] == 'MEDIUM']
    
    print(f"  HIGH: {len(high_priority)} 个")
    print(f"  MEDIUM: {len(medium_priority)} 个")
    
    print("\n前5个高优先级候选:")
    for i, candidate in enumerate(high_priority[:5], 1):
        print(f"\n  {i}. {Path(candidate['file']).name}")
        print(f"     问题: {candidate['issue']}")
        print(f"     建议修复:")
        for fix in candidate['suggested_fix']:
            print(f"       - {fix}")
    
    print("\n[4/4] 生成优化脚本...")
    script_content = generate_optimization_script(candidates)
    
    script_file = Path("auto_optimize_scenarios.py")
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"[OK] 脚本已生成: {script_file}")
    
    # 保存分析结果
    analysis_result = {
        'total_tests': total,
        'failed_tests': failed,
        'categories': {k: len(v) for k, v in categories.items()},
        'optimization_candidates': candidates
    }
    
    with open('test_results/failure_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(analysis_result, f, indent=2, ensure_ascii=False)
    
    print("[OK] 分析结果已保存: test_results/failure_analysis.json")
    
    print("\n" + "="*70)
    print("下一步:")
    print("="*70)
    print("\n1. 查看详细分析:")
    print("   cat test_results/failure_analysis.json")
    print("\n2. 运行自动优化:")
    print("   python auto_optimize_scenarios.py")
    print("\n3. 手动优化特定场景:")
    print("   python optimize_failing_scenarios.py")
    print("")

if __name__ == '__main__':
    main()

