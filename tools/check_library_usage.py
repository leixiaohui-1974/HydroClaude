#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HydroClaude 基础库使用检查工具

检查Python文件是否正确使用了HydroClaude基础库，避免重复造轮子。

用法:
    python tools/check_library_usage.py <文件或目录>
    
示例:
    # 检查单个文件
    python tools/check_library_usage.py examples/my_example.py
    
    # 检查整个目录
    python tools/check_library_usage.py examples/
    
    # 在CI中使用
    python tools/check_library_usage.py examples/ || exit 1

Author: HydroClaude Development Team
Date: 2025-10-27
"""

import ast
import sys
import re
from pathlib import Path
from typing import List, Dict, Tuple

# ========== 检查规则配置 ==========

# 必须导入的基础库（当文件使用相关功能时）
REQUIRED_IMPORTS = {
    'solver': {
        'module': 'solvers.hydrostatic_canal_solver',
        'class': 'HydrostaticCanalSolver',
        'trigger_patterns': ['solve_steady_state', 'step_preissmann'],
    },
    'validator': {
        'module': 'utils.result_validator',
        'class': 'ResultValidator',
        'trigger_patterns': ['solve_steady_state'],
    },
    'canal_utils': {
        'module': 'utils.canal_utils',
        'function': 'compute_steady_uniform_flow',
        'trigger_patterns': ['solver.h[:]', 'h_uniform'],
    }
}

# 禁止使用的废弃类/模块
DEPRECATED = [
    {
        'name': 'SingleCanalSolver',
        'module': 'solvers.single_canal_solver',
        'replacement': 'HydrostaticCanalSolver',
        'reason': '已废弃，使用 HydrostaticCanalSolver'
    },
    {
        'name': 'CanalSolver',
        'module': 'solvers.canal_solver',
        'replacement': 'HydrostaticCanalSolver',
        'reason': '已废弃，使用 HydrostaticCanalSolver'
    },
    {
        'name': 'MOCSolver',
        'module': 'solvers.moc_solver',
        'replacement': 'HydrostaticCanalSolver',
        'reason': 'MOC求解器已删除'
    },
]

# 禁止的模式（表示重复造轮子）
FORBIDDEN_PATTERNS = [
    {
        'pattern': r'def\s+validate_flow\s*\(',
        'description': '自定义流量验证函数',
        'suggestion': '使用 utils.result_validator.ResultValidator'
    },
    {
        'pattern': r'def\s+compute_uniform_\w*\s*\(',
        'description': '自定义均匀流计算函数',
        'suggestion': '使用 utils.canal_utils.compute_steady_uniform_flow'
    },
    {
        'pattern': r'def\s+plot_profile\s*\(',
        'description': '自定义纵剖面绘图函数',
        'suggestion': '使用 utils.plot_helper.PlotHelper.plot_profile'
    },
    {
        'pattern': r'def\s+plot_\w*_distribution\s*\(',
        'description': '自定义分布绘图函数',
        'suggestion': '使用 utils.plot_helper.PlotHelper 或 utils.visualization_templates'
    },
]

# 推荐使用的可视化工具
VISUALIZATION_LIBS = ['PlotHelper', 'VisualizationTemplates']

# ========== 检查函数 ==========

def check_file(file_path: Path) -> Dict:
    """检查单个文件是否符合基础库使用规范"""
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return {
            'file': str(file_path),
            'passed': False,
            'error': f'无法读取文件: {str(e)}',
            'issues': [],
            'warnings': [],
            'suggestions': []
        }
    
    results = {
        'file': str(file_path),
        'passed': True,
        'issues': [],
        'warnings': [],
        'suggestions': []
    }
    
    # 跳过非example/test文件
    file_str = str(file_path)
    is_example = 'example' in file_str.lower() or 'test' in file_str.lower()
    
    # 检查1: 是否使用了废弃的类
    for deprecated in DEPRECATED:
        if deprecated['name'] in content:
            results['issues'].append(
                f" 使用了废弃的类: {deprecated['name']} "
                f"({deprecated['reason']}) → 应使用: {deprecated['replacement']}"
            )
            results['passed'] = False
    
    # 检查2: 是否有重复造轮子的代码模式
    for forbidden in FORBIDDEN_PATTERNS:
        if re.search(forbidden['pattern'], content):
            results['warnings'].append(
                f"️  检测到可能的重复实现: {forbidden['description']}"
            )
            results['suggestions'].append(
                f" {forbidden['suggestion']}"
            )
    
    # 检查3: 如果是example文件，检查是否使用了推荐的基础库
    if is_example:
        # 检查求解器
        if 'solve_steady_state' in content or 'solver' in content.lower():
            if 'HydrostaticCanalSolver' not in content:
                results['issues'].append(
                    ' 未使用推荐的求解器: HydrostaticCanalSolver'
                )
                results['passed'] = False
        
        # 检查验证工具
        if 'solve_steady_state' in content:
            if 'ResultValidator' not in content and 'quick_validate_steady_state' not in content:
                results['warnings'].append(
                    '️  求解后未使用 ResultValidator 验证结果'
                )
                results['suggestions'].append(
                    ' 使用 quick_validate_steady_state 自动验证结果'
                )
        
        # 检查可视化工具
        if 'plt.subplots()' in content or 'fig, ax = plt.subplots' in content:
            has_viz_lib = any(lib in content for lib in VISUALIZATION_LIBS)
            if not has_viz_lib:
                results['warnings'].append(
                    '️  使用原生matplotlib绘图，建议使用专业绘图工具'
                )
                results['suggestions'].append(
                    ' 使用 PlotHelper 或 VisualizationTemplates 简化绘图代码'
                )
    
    # 检查4: 检查是否有明显的性能问题
    if 'convergence_tol=0.001' in content or 'convergence_tol=0.0001' in content:
        results['warnings'].append(
            '️  使用了过于严格的收敛容差，可能导致收敛缓慢'
        )
        results['suggestions'].append(
            ' 推荐使用 convergence_tol=0.1 以获得极快收敛（0-1次迭代）'
        )
    
    return results


def check_multiple_files(paths: List[Path]) -> List[Dict]:
    """批量检查多个文件"""
    all_results = []
    
    for path in paths:
        if path.is_file() and path.suffix == '.py':
            # 跳过__init__.py和测试文件
            if path.name == '__init__.py':
                continue
            all_results.append(check_file(path))
        elif path.is_dir():
            # 递归检查目录
            for py_file in path.rglob('*.py'):
                if py_file.name == '__init__.py':
                    continue
                all_results.append(check_file(py_file))
    
    return all_results


def print_summary(results: List[Dict]):
    """打印检查摘要"""
    print("=" * 80)
    print("HydroClaude 基础库使用检查报告")
    print("=" * 80)
    
    total = len(results)
    passed = sum(1 for r in results if r['passed'])
    failed = total - passed
    
    print(f"\n 总计: {total} 个文件")
    print(f" 通过: {passed} ({passed/total*100:.1f}%)" if total > 0 else " 通过: 0")
    print(f" 未通过: {failed}")
    
    # 统计问题类型
    total_issues = sum(len(r['issues']) for r in results)
    total_warnings = sum(len(r['warnings']) for r in results)
    
    if total_issues > 0:
        print(f"\n️  发现 {total_issues} 个严重问题")
    if total_warnings > 0:
        print(f" 发现 {total_warnings} 个警告")


def print_details(results: List[Dict]):
    """打印详细问题"""
    has_issues = any(not r['passed'] for r in results)
    has_warnings = any(r['warnings'] for r in results)
    
    if has_issues:
        print("\n" + "=" * 80)
        print("严重问题详情（必须修复）")
        print("=" * 80)
        for result in results:
            if not result['passed']:
                print(f"\n {result['file']}")
                for issue in result['issues']:
                    print(f"   {issue}")
                for suggestion in result['suggestions']:
                    print(f"   {suggestion}")
    
    if has_warnings:
        print("\n" + "=" * 80)
        print("警告和建议（推荐修复）")
        print("=" * 80)
        for result in results:
            if result['warnings']:
                print(f"\n {result['file']}")
                for warning in result['warnings']:
                    print(f"   {warning}")
                for suggestion in result['suggestions']:
                    print(f"   {suggestion}")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python check_library_usage.py <文件或目录>")
        print("\n示例:")
        print("  python tools/check_library_usage.py examples/my_example.py")
        print("  python tools/check_library_usage.py examples/")
        print("  python tools/check_library_usage.py examples/ --strict")
        sys.exit(1)
    
    # 解析参数
    input_paths = []
    strict_mode = '--strict' in sys.argv
    
    for arg in sys.argv[1:]:
        if arg.startswith('--'):
            continue
        input_paths.append(Path(arg))
    
    # 检查文件
    all_results = check_multiple_files(input_paths)
    
    if not all_results:
        print("️  没有找到Python文件")
        sys.exit(0)
    
    # 打印结果
    print_summary(all_results)
    print_details(all_results)
    
    # 返回状态码
    failed = sum(1 for r in all_results if not r['passed'])
    warnings = sum(1 for r in all_results if r['warnings'])
    
    print("\n" + "=" * 80)
    if failed > 0:
        print(" 检查失败！发现严重问题，请修复后再提交")
        sys.exit(1)
    elif warnings > 0 and strict_mode:
        print("️  严格模式：发现警告，建议修复")
        sys.exit(1)
    else:
        print(" 检查通过！代码符合基础库使用规范")
        sys.exit(0)


if __name__ == '__main__':
    main()
