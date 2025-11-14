#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全面测试所有模拟脚本 - 确保100%成功率
"""
import subprocess
import sys
import json
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def run_script_test(script_path, timeout=120):
    """运行单个脚本测试"""
    script = Path(script_path)
    
    try:
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1'
        user_site = os.path.expanduser('~/.local/lib/python3.12/site-packages')
        if 'PYTHONPATH' in env:
            env['PYTHONPATH'] = f"{user_site}:{env['PYTHONPATH']}"
        else:
            env['PYTHONPATH'] = user_site
        
        # 运行脚本
        proc = subprocess.run(
            [sys.executable, script.name],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(script.parent),
            env=env,
            errors='replace'
        )
        
        if proc.returncode == 0:
            return {'status': 'passed', 'error': None}
        else:
            # 提取错误信息
            error_lines = proc.stderr.strip().split('\n')
            error_msg = '\n'.join(error_lines[-10:]) if error_lines else 'Unknown error'
            return {'status': 'failed', 'error': error_msg}
    
    except subprocess.TimeoutExpired:
        return {'status': 'timeout', 'error': f'Timeout after {timeout}s'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

def categorize_script(script_path):
    """脚本分类"""
    path_str = str(script_path)
    
    if 'example_01_canal_flow' in path_str:
        return '01_明渠流动'
    elif 'gate_pump' in path_str:
        return '02_闸门泵站'
    elif any(x in path_str for x in ['network', 'loop_network', 'tree_network']):
        return '03_管网系统'
    elif 'structure' in path_str:
        return '04_水工结构'
    elif any(x in path_str.lower() for x in ['case', 'engineering_cases', 'real_world']):
        return '05_工程案例'
    elif 'control' in path_str or 'mpc' in path_str or 'pid' in path_str:
        return '06_控制系统'
    elif any(x in path_str for x in ['example_02', 'example_03', 'example_04', 'example_05',
                                       'example_06', 'example_07', 'example_08', 'example_09',
                                       'example_10', 'example_11', 'example_12', 'example_13',
                                       'example_14', 'example_15', 'example_16', 'example_17',
                                       'example_18', 'example_19', 'example_20', 'example_21',
                                       'example_22', 'example_23', 'example_24']):
        return '07_高级示例'
    elif 'test' in path_str.lower() or 'benchmark' in path_str.lower():
        return '08_测试基准'
    else:
        return '09_其他'

def main():
    print("="*80)
    print("全面测试所有模拟脚本")
    print("="*80)
    print()
    
    # 读取有效脚本列表
    with open('script_analysis.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    valid_scripts = data['valid_scripts']
    
    # 排除不需要测试的脚本
    exclude_patterns = [
        'output_helper.py',
        'animation_utils.py',
        'organize_examples.py',
        'generate_readmes.py',
        'supplement_readmes.py',
        'generate_html_index.py',
        'optimize_gifs.py',
        'generate_animations.py',
        'preview_animations.py',
        'batch_generate_animations.py',
        'batch_modify',
        '/tests/test_',
        'run_all',
        'validate_all'
    ]
    
    # 筛选测试脚本
    test_scripts = []
    for script in valid_scripts:
        if any(pattern in script for pattern in exclude_patterns):
            continue
        if Path(script).exists():
            test_scripts.append(script)
    
    print(f"总计需要测试: {len(test_scripts)} 个脚本")
    print(f"开始测试...\n")
    
    # 按类别分组
    scripts_by_category = defaultdict(list)
    for script in test_scripts:
        category = categorize_script(script)
        scripts_by_category[category].append(script)
    
    # 测试结果
    all_results = {}
    category_stats = {}
    
    start_time = datetime.now()
    
    # 按类别测试
    for category in sorted(scripts_by_category.keys()):
        scripts = scripts_by_category[category]
        print(f"\n{'='*80}")
        print(f"类别: {category} ({len(scripts)} 个脚本)")
        print(f"{'='*80}\n")
        
        cat_results = {'passed': 0, 'failed': 0, 'timeout': 0, 'error': 0}
        
        for i, script_path in enumerate(scripts, 1):
            script = Path(script_path)
            print(f"[{i}/{len(scripts)}] {script.name}...", end=" ", flush=True)
            
            result = run_script_test(script_path, timeout=90)
            all_results[str(script_path)] = result
            
            cat_results[result['status']] += 1
            
            # 显示结果
            status_icons = {
                'passed': '✅',
                'failed': '❌',
                'timeout': '⏱️',
                'error': '❌'
            }
            print(f"{status_icons[result['status']]} {result['status']}")
            
            # 如果失败，显示简短错误
            if result['status'] in ['failed', 'error'] and result['error']:
                error_line = result['error'].split('\n')[-1][:100]
                print(f"    错误: {error_line}")
        
        category_stats[category] = cat_results
    
    end_time = datetime.now()
    
    # 生成总结报告
    print(f"\n{'='*80}")
    print(f"测试总结")
    print(f"{'='*80}\n")
    
    print(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总耗时: {(end_time - start_time).total_seconds():.1f} 秒\n")
    
    # 按类别统计
    print(f"{'类别':<20} {'总数':>6} {'通过':>6} {'失败':>6} {'超时':>6} {'成功率':>8}")
    print(f"-" * 80)
    
    total_all = total_passed = 0
    for category in sorted(category_stats.keys()):
        stats = category_stats[category]
        total = sum(stats.values())
        passed = stats['passed']
        failed = stats['failed']
        timeout = stats['timeout']
        success_rate = passed / total * 100 if total > 0 else 0
        
        print(f"{category:<20} {total:>6} {passed:>6} {failed:>6} {timeout:>6} {success_rate:>7.1f}%")
        
        total_all += total
        total_passed += passed
    
    print(f"-" * 80)
    overall_success_rate = total_passed / total_all * 100 if total_all > 0 else 0
    print(f"{'总计':<20} {total_all:>6} {total_passed:>6} "
          f"{sum(s['failed'] for s in category_stats.values()):>6} "
          f"{sum(s['timeout'] for s in category_stats.values()):>6} "
          f"{overall_success_rate:>7.1f}%\n")
    
    # 保存详细结果
    output_data = {
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat(),
        'total_scripts': total_all,
        'passed': total_passed,
        'overall_success_rate': overall_success_rate,
        'category_stats': category_stats,
        'results': all_results
    }
    
    output_file = 'comprehensive_test_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"详细结果已保存到: {output_file}")
    print(f"\n{'='*80}")
    print(f"总成功率: {overall_success_rate:.1f}%")
    print(f"{'='*80}")
    
    # 列出失败的脚本
    failed_scripts = [path for path, result in all_results.items() 
                     if result['status'] in ['failed', 'error']]
    
    if failed_scripts:
        print(f"\n失败的脚本 ({len(failed_scripts)} 个):")
        for script in failed_scripts[:20]:
            print(f"  - {Path(script).name}")
        if len(failed_scripts) > 20:
            print(f"  ... 还有 {len(failed_scripts)-20} 个")
    
    return 0 if overall_success_rate == 100.0 else 1

if __name__ == '__main__':
    sys.exit(main())
