#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Windows中文环境兼容性测试

专门测试在Windows中文环境下的运行情况

Author: HydroClaude
Date: 2025-11-13
"""

import subprocess
import sys
import os
import time
import json
from pathlib import Path
import locale

def setup_chinese_env():
    """设置中文环境"""
    # 检测当前环境
    print("="*80)
    print("环境检测")
    print("="*80)
    print(f"系统编码: {sys.getdefaultencoding()}")
    print(f"文件系统编码: {sys.getfilesystemencoding()}")
    print(f"标准输出编码: {sys.stdout.encoding}")
    print(f"标准错误编码: {sys.stderr.encoding}")
    print(f"区域设置: {locale.getdefaultlocale()}")
    print()

def test_file_chinese_safe(file_path, timeout=60):
    """
    在Windows中文环境下安全测试文件
    
    关键改进：
    1. 设置PYTHONIOENCODING=utf-8
    2. 使用errors='replace'处理无法编码的字符
    3. 捕获并处理编码错误
    """
    try:
        start = time.time()
        
        # 设置环境变量，强制UTF-8编码
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONLEGACYWINDOWSSTDIO'] = '0'  # Python 3.6+
        
        result = subprocess.run(
            [sys.executable, str(file_path)],
            capture_output=True,
            timeout=timeout,
            encoding='utf-8',
            errors='replace',  # 关键：替换无法解码的字符
            env=env
        )
        
        elapsed = time.time() - start
        
        if result.returncode == 0:
            return 'PASS', elapsed, None, result.stdout, result.stderr
        else:
            # 提取错误信息
            err = result.stderr if result.stderr else result.stdout
            lines = err.split('\n')
            error_msg = 'Unknown error'
            
            for line in lines:
                line_clean = line.strip()
                if any(keyword in line_clean for keyword in 
                      ['Error', 'Exception', 'Traceback', 'Failed']):
                    error_msg = line_clean[:200]
                    break
            
            return 'FAIL', elapsed, error_msg, result.stdout, result.stderr
        
    except subprocess.TimeoutExpired:
        return 'TIMEOUT', timeout, f'Timeout (>{timeout}s)', '', ''
    except UnicodeDecodeError as e:
        return 'UNICODE_ERROR', 0, f'编码错误: {str(e)[:80]}', '', ''
    except Exception as e:
        return 'ERROR', 0, str(e)[:80], '', ''

def categorize_error(error_msg):
    """分类错误类型"""
    if not error_msg:
        return 'Unknown'
    
    error_lower = error_msg.lower()
    
    # Windows中文环境特有错误
    if 'gbk' in error_lower or 'cp936' in error_lower:
        return 'GBK编码'
    elif 'unicodeencodeerror' in error_lower:
        return 'Unicode编码'
    elif 'unicodedecodeerror' in error_lower:
        return 'Unicode解码'
    elif 'modulenotfounderror' in error_lower or 'importerror' in error_lower:
        return '模块导入'
    elif 'attributeerror' in error_lower:
        return '属性错误'
    elif 'typeerror' in error_lower:
        return '类型错误'
    elif 'valueerror' in error_lower:
        return '值错误'
    elif 'filenotfounderror' in error_lower:
        return '文件未找到'
    elif 'timeout' in error_lower:
        return '超时'
    elif 'indentationerror' in error_lower:
        return '缩进错误'
    else:
        return '其他错误'

def find_all_simulation_files():
    """查找所有仿真文件"""
    examples_dir = Path('examples')
    
    # 排除
    exclude_patterns = [
        '**/backups/**',
        '**/*.bak*',
        '**/__pycache__/**',
        '**/output_helper.py',
    ]
    
    # 包含
    include_patterns = [
        '**/example_*.py',
        '**/demo_*.py',
        '**/case_*.py',
        '**/run_*.py',
        '**/*_v2.py',
    ]
    
    all_files = []
    for pattern in include_patterns:
        files = list(examples_dir.glob(pattern))
        all_files.extend(files)
    
    # 去重并排除
    unique_files = []
    seen = set()
    for f in all_files:
        if f.is_file() and str(f) not in seen:
            exclude = False
            for exclude_pattern in exclude_patterns:
                if f.match(exclude_pattern):
                    exclude = True
                    break
            
            if not exclude:
                seen.add(str(f))
                unique_files.append(f)
    
    return sorted(unique_files)

def main():
    """主函数"""
    
    print("="*80)
    print("Windows中文环境兼容性测试")
    print("="*80)
    print()
    
    # 环境检测
    setup_chinese_env()
    
    # 查找所有文件
    print("正在搜索仿真文件...")
    all_files = find_all_simulation_files()
    print(f"找到 {len(all_files)} 个文件")
    print()
    
    # 测试所有文件
    results = {}
    errors = []
    error_categories = {}
    encoding_issues = []
    
    print("开始测试...")
    print("-"*80)
    
    for i, file_path in enumerate(all_files, 1):
        rel_path = file_path.relative_to('examples')
        
        # 根据文件位置设置超时
        if 'scenario' in str(file_path) or 'optimization' in str(file_path):
            timeout = 120
        elif 'benchmark' in str(file_path):
            timeout = 60
        else:
            timeout = 30
        
        print(f"[{i:3d}/{len(all_files)}] {str(rel_path):60s}", end=" ", flush=True)
        
        status, elapsed, error, stdout, stderr = test_file_chinese_safe(file_path, timeout=timeout)
        print(f"[{status:15s}] ({elapsed:.1f}s)")
        
        results[str(rel_path)] = {
            'status': status,
            'elapsed': elapsed,
            'error': error
        }
        
        # 检测编码相关问题
        if error and ('gbk' in error.lower() or 'unicode' in error.lower() or '编码' in error):
            encoding_issues.append({
                'file': str(rel_path),
                'error': error
            })
        
        if status in ['FAIL', 'ERROR', 'UNICODE_ERROR'] and error:
            error_cat = categorize_error(error)
            errors.append({
                'file': str(rel_path),
                'category': error_cat,
                'error': error
            })
            error_categories[error_cat] = error_categories.get(error_cat, 0) + 1
    
    print()
    print("="*80)
    print("测试结果汇总")
    print("="*80)
    
    passed = sum(1 for r in results.values() if r['status'] == 'PASS')
    failed = sum(1 for r in results.values() if r['status'] == 'FAIL')
    timeout_count = sum(1 for r in results.values() if r['status'] == 'TIMEOUT')
    error_count = sum(1 for r in results.values() if r['status'] in ['ERROR', 'UNICODE_ERROR'])
    
    total = len(results)
    
    print(f"\n总计: {total} 个文件")
    print(f"通过: {passed} ({passed/total*100:.1f}%)")
    print(f"失败: {failed} ({failed/total*100:.1f}%)")
    print(f"超时: {timeout_count} ({timeout_count/total*100:.1f}%)")
    print(f"错误: {error_count} ({error_count/total*100:.1f}%)")
    
    print(f"\n通过率: {passed}/{total} = {passed/total*100:.1f}%")
    
    # Windows中文环境特有问题统计
    encoding_error_count = error_categories.get('GBK编码', 0) + \
                          error_categories.get('Unicode编码', 0) + \
                          error_categories.get('Unicode解码', 0)
    
    if encoding_error_count > 0:
        print(f"\n⚠️ 编码相关错误: {encoding_error_count} 个 ({encoding_error_count/total*100:.1f}%)")
        print("这些需要特别修复以适配Windows中文环境")
    
    # 错误分类统计
    if error_categories:
        print(f"\n错误类型分布:")
        for cat, count in sorted(error_categories.items(), key=lambda x: -x[1]):
            print(f"  {cat:15s}: {count:3d}")
    
    # 编码问题详情
    if encoding_issues:
        print(f"\n编码问题详情 (前10个):")
        print("-"*80)
        for issue in encoding_issues[:10]:
            print(f"\n{issue['file']}")
            print(f"  错误: {issue['error'][:150]}")
    
    # 保存结果
    output = {
        'summary': {
            'total': total,
            'passed': passed,
            'failed': failed,
            'timeout': timeout_count,
            'error': error_count,
            'encoding_errors': encoding_error_count,
            'pass_rate': passed / total * 100 if total > 0 else 0
        },
        'results': results,
        'errors': errors,
        'error_categories': error_categories,
        'encoding_issues': encoding_issues
    }
    
    with open('windows_chinese_test_results.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n结果已保存到: windows_chinese_test_results.json")
    
    # 显示建议
    print("\n" + "="*80)
    print("Windows中文环境兼容性建议")
    print("="*80)
    
    if encoding_error_count == 0:
        print("✅ 没有编码相关错误！所有脚本在Windows中文环境下运行良好。")
    else:
        print(f"⚠️ 发现 {encoding_error_count} 个编码相关错误，建议：")
        print("  1. 确保所有文件使用UTF-8编码保存")
        print("  2. 所有open()调用添加encoding='utf-8'")
        print("  3. 移除所有emoji和特殊Unicode字符")
        print("  4. print()输出避免使用无法编码的字符")
        print("  5. 使用errors='replace'处理编码错误")
    
    print("\n" + "="*80)
    
    return passed, total, encoding_error_count

if __name__ == '__main__':
    passed, total, encoding_errors = main()
    
    # 评价
    pass_rate = passed / total * 100 if total > 0 else 0
    
    print(f"\n最终评价: ", end="")
    if pass_rate >= 95 and encoding_errors == 0:
        print("优秀 ⭐⭐⭐⭐⭐ (完美适配Windows中文环境)")
    elif pass_rate >= 85 and encoding_errors <= 5:
        print("良好 ⭐⭐⭐⭐ (基本适配Windows中文环境)")
    elif pass_rate >= 75:
        print("合格 ⭐⭐⭐ (需改进编码处理)")
    elif pass_rate >= 60:
        print("需改进 ⭐⭐ (编码问题较多)")
    else:
        print("不及格 ⭐ (严重编码问题)")
    
    if encoding_errors > 0:
        print(f"\n⚠️ 编码兼容性: {total - encoding_errors}/{total} ({(total-encoding_errors)/total*100:.1f}%)")

