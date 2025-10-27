"""
方案B: 混合有限体积/有限差分法 + 交错网格

核心特性:
1. 连续性方程：有限体积法（FV）→ 精确质量守恒
2. 动量方程：有限差分法（FD）→ 计算高效
3. 交错网格：h在单元中心，Q在单元界面
4. Riemann求解器：精确处理间断

精度目标: 流量误差 < 0.3%
质量守恒: 机器精度

理论基础:
- Lai & Khan (2018) "Hybrid FV/FD" - Journal of Hydrodynamics
- Stelling & Duinmeijer (2003) "Staggered Grid"

优势:
- 精确质量守恒（FV连续性方程）
- 计算高效（FD动量方程）
- 自然处理间断（交错网格 + Riemann求解器）
- 适合结构物（闸门、泵站）

Author: Claude (AI Assistant)
Date: 2025-10-27
License: MIT
"""

from .staggered_grid import StaggeredGrid, GridType
from .fv_continuity import FVContinuityEquation
from .fd_momentum import FDMomentumEquation
from .riemann_solver import ExactRiemannSolver, HLLRiemannSolver
from .hybrid_canal_solver import HybridCanalSolver
from .boundary_conditions import (
    BoundaryCondition,
    ConstantBC,
    TimeSeriesBC,
    ControlRuleBC,
    BoundaryManager
)
from .unsteady_solver import UnsteadySolver

__all__ = [
    'StaggeredGrid',
    'GridType',
    'FVContinuityEquation',
    'FDMomentumEquation',
    'ExactRiemannSolver',
    'HLLRiemannSolver',
    'HybridCanalSolver',
    'BoundaryCondition',
    'ConstantBC',
    'TimeSeriesBC',
    'ControlRuleBC',
    'BoundaryManager',
    'UnsteadySolver',
]

__version__ = '2.1.0-alpha'
__author__ = 'Claude AI Assistant'
__description__ = '混合FV/FD法 + 交错网格（方案B）- 稳态+非恒定流'
