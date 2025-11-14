#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面批量测试所有模拟案例
"""
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime
import os
import time

def main():
    # 读取有效脚本列表
    with open('script_analysis.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    valid_scripts = data['valid_scripts']
    
    # 过滤掉不需要测试的脚本
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
        'run_all',
        'validate_all',
        'batch_modify',
        'test_examples.py',
        'comprehensive_animation_generator.py',
        'advanced_animation_generator.py'
    ]
    
    # 筛选需要测试的脚本
    test_scripts = []
    for script in valid_scripts:
        script_name = Path(script).name
        if any(pattern in script_name for pattern in exclude_patterns):
            continue
        test_scripts.append(script)
    
    print(f"{'='*80}")
    print(f"全面批量测试 - 共 {len(test_scripts)} 个脚本")
    print(f"{'='*80}\n")
    
    # 分类测试结果
    results = {
        'passed': [],
        'failed': [],
        'timeout': [],
        'import_error': [],
        'runtime_error': []
    }
    
    start_time = time.time()
    
    for i, script_path in enumerate(test_scripts, 1):
        script = Path(script_path)
        
        if not script.exists():
            print(f"[{i}/{len(test_scripts)}] ⚠️  {script.name} - 文件不存在")
            continue
        
        print(f"[{i}/{len(test_scripts)}] 测试: {script.relative_to('examples')}")
        
        try:
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONUTF8'] = '1'
            user_site = os.path.expanduser('~/.local/lib/python3.12/site-packages')
            if 'PYTHONPATH' in env:
                env['PYTHONPATH'] = f"{user_site}:{env['PYTHONPATH']}"
            else:
                env['PYTHONPATH'] = user_site
            
            # 从workspace根目录运行
            proc = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True,
                text=True,
                timeout=90,  # 90秒超时
                cwd='/workspace',  # 统一从workspace运行
                env=env,
                errors='replace'
            )
            
            if proc.returncode == 0:
                results['passed'].append(str(script))
                print(f"  ✅ 通过\n")
            else:
                # 判断错误类型
                stderr = proc.stderr
                if 'ModuleNotFoundError' in stderr or 'ImportError' in stderr:
                    results['import_error'].append({
                        'path': str(script),
                        'error': stderr.split('\n')[-5:]
                    })
                    print(f"  ❌ 导入错误\n")
                else:
                    results['runtime_error'].append({
                        'path': str(script),
                        'error': stderr.split('\n')[-5:]
                    })
                    print(f"  ❌ 运行错误\n")
        except subprocess.TimeoutExpired:
            results['timeout'].append(str(script))
            print(f"  ⏱️  超时(>90s)\n")
        except Exception as e:
            results['failed'].append({'path': str(script), 'error': str(e)})
            print(f"  ❌ 异常: {e}\n")
    
    elapsed = time.time() - start_time
    
    # 统计
    total = len(test_scripts)
    passed = len(results['passed'])
    failed = len(results['failed']) + len(results['import_error']) + len(results['runtime_error'])
    timeout = len(results['timeout'])
    
    # 保存结果
    output_data = {
        'timestamp': datetime.now().isoformat(),
        'total': total,
        'passed': passed,
        'failed': failed,
        'timeout': timeout,
        'elapsed_seconds': elapsed,
        'results': results
    }
    
    output_file = f'comprehensive_test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    # 打印总结
    print(f"\n{'='*80}")
    print(f"测试总结")
    print(f"{'='*80}")
    print(f"总测试数: {total}")
    print(f"  ✅ 通过: {passed} ({passed/total*100:.1f}%)")
    print(f"  ❌ 失败: {failed} ({failed/total*100:.1f}%)")
    print(f"    - 导入错误: {len(results['import_error'])}")
    print(f"    - 运行错误: {len(results['runtime_error'])}")
    print(f"    - 其他失败: {len(results['failed'])}")
    print(f"  ⏱️  超时: {timeout} ({timeout/total*100:.1f}%)")
    print(f"\n总耗时: {elapsed:.1f}秒 ({elapsed/60:.1f}分钟)")
    print(f"结果已保存到: {output_file}")
    print(f"{'='*80}")
    
    # 列出失败的脚本
    if results['import_error']:
        print(f"\n导入错误的脚本 ({len(results['import_error'])}个):")
        for item in results['import_error'][:10]:
            print(f"  - {Path(item['path']).name}")
        if len(results['import_error']) > 10:
            print(f"  ... 还有 {len(results['import_error'])-10} 个")
    
    if results['runtime_error']:
        print(f"\n运行错误的脚本 ({len(results['runtime_error'])}个):")
        for item in results['runtime_error'][:10]:
            print(f"  - {Path(item['path']).name}")
        if len(results['runtime_error']) > 10:
            print(f"  ... 还有 {len(results['runtime_error'])-10} 个")

if __name__ == '__main__':
    main()
