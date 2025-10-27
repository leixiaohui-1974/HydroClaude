"""
情景分析模块

快速运行多个情景并对比分析。

核心功能：
- 批量运行情景
- 自动对比分析
- 生成对比报告

使用示例：
    >>> from scenarios import ScenarioManager
    >>> 
    >>> scenarios = {
    ...     "基准": {},
    ...     "高水": {"downstream_depth": 3.0},
    ... }
    >>> 
    >>> manager = ScenarioManager("config/base.yaml")
    >>> results = manager.run_scenarios(scenarios)
    >>> manager.compare_results(results)

Author: Claude (AI Assistant)
Date: 2025-10-27
"""

from .scenario_manager import ScenarioManager

__all__ = ['ScenarioManager']

__version__ = '2.4.0-alpha'
