"""
结果可视化模块

自动生成标准水力学图表。

核心功能：
- 纵断面图
- 流量分布图
- 时间历程图
- 收敛历史图

使用示例：
    >>> from visualization import ResultVisualizer
    >>> 
    >>> viz = ResultVisualizer(result)
    >>> viz.plot_all("figures/")  # 一键生成

Author: Claude (AI Assistant)
Date: 2025-10-27
"""

from .auto_plot import ResultVisualizer

__all__ = ['ResultVisualizer']

__version__ = '2.3.0-alpha'
