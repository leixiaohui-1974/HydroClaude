"""
方案A: 良平衡有限差分法

核心特性:
- 静水重构法（Audusse et al. 2004）
- 正确的非均匀网格处理
- 守恒的边界条件
- 可选的能量方程稳态求解器

精度目标: 流量误差 < 0.5%
"""

from .hydrostatic_reconstruction import HydrostaticReconstruction
from .wellbalanced_canal_solver import WellBalancedCanalSolver
from .energy_equation_solver import EnergyEquationSolver
from .structures import SluiceGate, PumpStation, BroadCrestedWeir

__all__ = [
    'HydrostaticReconstruction',
    'WellBalancedCanalSolver',
    'EnergyEquationSolver',
    'SluiceGate',
    'PumpStation',
    'BroadCrestedWeir',
]

__version__ = '1.0.0-alpha'
