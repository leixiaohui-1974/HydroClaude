"""
方案C: 间断Galerkin高阶有限元法

核心特性:
1. 高阶精度（3-4阶空间精度）
2. 间断Galerkin框架（DG）
3. ADER时空耦合
4. TVD斜率限制器
5. 专为刚性源项优化（闸门/泵站）

精度目标: 流量误差 < 0.1%
质量守恒: 机器精度
计算成本: +50-100% vs 方案B

理论基础:
- Cockburn & Shu (1998) "Runge-Kutta DG Methods"
- Ern et al. (2015) "DG for Natural Channels"
- Xing & Shu (2012) "DG for Shallow Water"
- Dumbser et al. (2008) "ADER-DG"

优势:
- 粗网格上达到高精度
- h-p自适应（网格+阶数）
- 局部守恒
- 适合并行计算

Author: Claude (AI Assistant)
Date: 2025-10-27
License: MIT
"""

from .dg_basis import LegendreBasis, DGBasisFunctions
from .dg_element import DGElement, DGMesh
from .dg_solver import DGCanalSolver
from .ader_timestepping import ADERTimeStepping
from .tvd_limiter import MinmodLimiter, TVDLimiter

__all__ = [
    'LegendreBasis',
    'DGBasisFunctions',
    'DGElement',
    'DGMesh',
    'DGCanalSolver',
    'ADERTimeStepping',
    'MinmodLimiter',
    'TVDLimiter',
]

__version__ = '3.0.0-alpha'
__author__ = 'Claude AI Assistant'
__description__ = '间断Galerkin高阶法（方案C）- 精度目标: 流量误差 < 0.1%'
