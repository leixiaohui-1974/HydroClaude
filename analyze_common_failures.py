#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""分析常见失败模式并提供修复方案"""

import os
import re
from pathlib import Path
from collections import Counter

def analyze_import_errors():
    """分析导入错误"""
    
    print("\n" + "="*70)
    print("分析1: 导入错误（ModuleNotFoundError）")
    print("="*70)
    
    # 扫描所有Python文件，查找导入语句
    import_errors = {
        'physics': [],
        'solvers.godunov_fvm_weno3': [],
        'other': []
    }
    
    for root_dir in ['tests', 'examples']:
        if Path(root_dir).exists():
            for py_file in Path(root_dir).rglob('*.py'):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 查找 from physics.xxx import
                    if 'from physics.' in content:
                        import_errors['physics'].append(str(py_file))
                    
                    # 查找 from solvers.godunov_fvm_weno3 import
                    if 'from solvers.godunov_fvm_weno3' in content:
                        import_errors['solvers.godunov_fvm_weno3'].append(str(py_file))
                
                except:
                    pass
    
    print(f"\n发现潜在导入问题:")
    print(f"  physics模块: {len(import_errors['physics'])} 个文件")
    print(f"  godunov_fvm_weno3: {len(import_errors['solvers.godunov_fvm_weno3'])} 个文件")
    
    if import_errors['physics']:
        print(f"\n使用physics模块的文件（前5个）:")
        for f in import_errors['physics'][:5]:
            print(f"    - {f}")
    
    return import_errors

def analyze_deprecated_imports():
    """分析废弃的求解器导入"""
    
    print("\n" + "="*70)
    print("分析2: 废弃求解器导入")
    print("="*70)
    
    deprecated_solvers = {
        'SingleCanalSolver': [],
        'CanalSolver': [],
    }
    
    for root_dir in ['tests', 'examples']:
        if Path(root_dir).exists():
            for py_file in Path(root_dir).rglob('*.py'):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if 'SingleCanalSolver' in content and 'import' in content:
                        deprecated_solvers['SingleCanalSolver'].append(str(py_file))
                    
                    if 'CanalSolver' in content and 'import' in content:
                        deprecated_solvers['CanalSolver'].append(str(py_file))
                
                except:
                    pass
    
    print(f"\n发现废弃求解器使用:")
    print(f"  SingleCanalSolver: {len(deprecated_solvers['SingleCanalSolver'])} 个文件")
    print(f"  CanalSolver: {len(deprecated_solvers['CanalSolver'])} 个文件")
    
    return deprecated_solvers

def check_solver_files():
    """检查求解器文件是否存在"""
    
    print("\n" + "="*70)
    print("分析3: 检查关键模块文件")
    print("="*70)
    
    critical_files = {
        'solvers/hydrostatic_canal_solver.py': Path('solvers/hydrostatic_canal_solver.py').exists(),
        'solvers/gate.py': Path('solvers/gate.py').exists(),
        'utils/canal_utils.py': Path('utils/canal_utils.py').exists(),
        'utils/result_validator.py': Path('utils/result_validator.py').exists(),
        'physics/': Path('physics/').exists(),
        'solvers/godunov_fvm_weno3.py': Path('solvers/godunov_fvm_weno3.py').exists(),
    }
    
    print(f"\n关键文件状态:")
    for file, exists in critical_files.items():
        status = "[OK]" if exists else "[MISSING]"
        print(f"  {status} {file}")
    
    return critical_files

def generate_fix_recommendations():
    """生成修复建议"""
    
    print("\n" + "="*70)
    print("修复建议")
    print("="*70)
    
    print("""
优先级P0（必须修复）:
  1. 确保所有关键模块文件存在
  2. 修复所有导入路径错误

优先级P1（重要）:
  3. 替换废弃的求解器导入
  4. 添加缺失的sys.path配置

优先级P2（优化）:
  5. 优化数值稳定性参数
  6. 增加超时时间配置

修复脚本:
  - fix_import_paths.py (修复导入路径)
  - fix_deprecated_solvers.py (替换废弃求解器)
  - add_sys_path.py (添加路径配置)
""")

def main():
    print("="*70)
    print("常见失败模式分析")
    print("="*70)
    print("\n基于快速测试(30个样本):")
    print("  通过: 18 (60%)")
    print("  失败: 12 (40%)")
    
    # 分析
    import_errors = analyze_import_errors()
    deprecated = analyze_deprecated_imports()
    files_status = check_solver_files()
    
    # 建议
    generate_fix_recommendations()
    
    print("\n" + "="*70)
    print("下一步:")
    print("  1. 等待第三轮完整测试完成")
    print("  2. 根据详细结果制定修复计划")
    print("  3. 批量修复导入和配置问题")
    print("  4. 优化数值稳定性")
    print("  5. 达到100%通过率")
    print("="*70)

if __name__ == '__main__':
    main()

