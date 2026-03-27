"""
hydrostatic_2d_solver.py — Hydrostatic 2D SWE 求解器（CPU 参考实现）

本模块为 GPU2DSolver（cpu 模式）的薄包装层，提供兼容接口：
  - step_2d(dt)  ← GPU2DSolver.step(dt)
  - _compute_dt(cfl) ← GPU2DSolver.compute_dt(cfl)

GPU2DSolver 文档说明：数值方法与本类完全一致，仅后端不同。
"""

from __future__ import annotations
from typing import Optional, Tuple

import numpy as np

from solvers.gpu_2d_solver import GPU2DSolver


class Hydrostatic2DSolver(GPU2DSolver):
    """
    2D 浅水方程 CPU 参考求解器。

    采用向量化 HLLC Riemann 求解器 + Audusse 干湿重构 + 显式 Euler 时间推进。
    本类是 GPU2DSolver 的 CPU 专用版本（force_cpu=True），并提供 step_2d / _compute_dt 等别名接口。
    """

    def __init__(
        self,
        Lx: float,
        Ly: float,
        nx: int,
        ny: int,
        S0x: float = 0.0,
        S0y: float = 0.0,
        n: float = 0.025,
        g: float = 9.81,
        eps_dry: float = 1e-4,
        z_bed: Optional[np.ndarray] = None,
    ):
        # 强制 CPU 模式：不使用 GPU
        super().__init__(
            Lx=Lx, Ly=Ly, nx=nx, ny=ny,
            S0x=S0x, S0y=S0y, n=n, g=g,
            eps_dry=eps_dry, z_bed=z_bed,
            force_cpu=True,
        )

    # ------------------------------------------------------------------
    # 兼容性别名
    # ------------------------------------------------------------------

    def step_2d(self, dt: float) -> None:
        """等同于 GPU2DSolver.step(dt)，供测试和耦合求解器调用。"""
        self.step(dt)

    def _compute_dt(self, cfl: float = 0.45) -> float:
        """等同于 GPU2DSolver.compute_dt(cfl)。"""
        return self.compute_dt(cfl)

    def set_initial_condition(
        self,
        h: np.ndarray,
        hu: Optional[np.ndarray] = None,
        hv: Optional[np.ndarray] = None,
        hu0: Optional[np.ndarray] = None,
        hv0: Optional[np.ndarray] = None,
    ) -> None:
        """兼容 hu0/hv0 关键字（旧接口别名），转发给父类。"""
        super().set_initial_condition(
            h,
            hu=hu if hu is not None else hu0,
            hv=hv if hv is not None else hv0,
        )
