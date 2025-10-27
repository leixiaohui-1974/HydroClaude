"""
HydroClaude测试模块

包含：
- 解析解库
- Week 1-4测试套件
- 基准数据

Author: Claude (AI Assistant)
Date: 2025-10-27
"""

import os
import sys

# 添加tests目录到Python路径
tests_dir = os.path.dirname(os.path.abspath(__file__))
if tests_dir not in sys.path:
    sys.path.insert(0, tests_dir)

# 添加项目根目录到Python路径
project_root = os.path.dirname(tests_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

__all__ = [
    'analytical_solutions',
    'test_analytical_validation',
    'test_benchmark_cases',
    'test_extreme_conditions',
    'test_long_term_stability',
]

__version__ = '1.0.0'
