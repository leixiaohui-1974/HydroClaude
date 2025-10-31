#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Godunov有限体积法求解器 - WENO-5重构（5阶精度）

核心：
1. ✅ 有限体积法（FVM）- 守恒
2. ✅ WENO-5重构 - 5阶精度+无振荡
3. ✅ HLL Riemann求解器
4. ✅ TVD-RK3 时间积分（3阶）

MacDonald Test 4专用优化！

参考:
- Jiang & Shu (1996) "Efficient implementation of weighted ENO schemes"
- Toro (2009) "Riemann Solvers and Numerical Methods"

作者: HydroClaude Team
日期: 2025-10-31
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from typing import Tuple, Dict, Optional
from solvers.godunov_fvm_solver import GodunvFVMSolver
from solvers.weno5_reconstruction import weno5_reconstruct


class GodunvFVMWENO5(GodunvFVMSolver):
    """
    Godunov-FVM求解器 + WENO-5重构

    继承GodunvFVMSolver，使用WENO-5替代MUSCL重构

    WENO-5特性：
    - 5阶空间精度（光滑区域）
    - 3个模板（stencils）
    - 自动识别间断
    - 无振荡
    - 极低数值耗散
    """

    def __init__(
        self,
        width: float,
        length: float,
        n_cells: int,
        manning_n: float,
        slope: float,
        g: float = 9.81,
        cfl: float = 0.4,  # WENO5推荐降低CFL
        eps_dry: float = 1e-6,
        weno_epsilon: float = 1e-6,
        riemann_solver: str = 'hll',
        well_balanced: bool = False,
        use_numba: bool = True,
        dt_max: Optional[float] = None,
        entropy_fix: bool = False,
        critical_flow_treatment: bool = False
    ):
        """
        初始化WENO5求解器

        Args:
            (与父类相同)
            weno_epsilon: WENO小量参数（防止除零）
            riemann_solver: Riemann求解器类型 ('hll')
            well_balanced: 是否使用Well-Balanced格式
            use_numba: 是否使用Numba加速
            dt_max: 最大时间步长（秒）
            entropy_fix: 是否使用Harten-Hyman entropy修正
            critical_flow_treatment: 是否使用临界流特殊处理
        """
        # 调用父类初始化，标记为5阶
        super().__init__(
            width=width,
            length=length,
            n_cells=n_cells,
            manning_n=manning_n,
            slope=slope,
            g=g,
            cfl=cfl,
            eps_dry=eps_dry,
            order=5,  # 标记为5阶
            riemann_solver=riemann_solver,
            well_balanced=well_balanced,
            use_numba=use_numba,
            dt_max=dt_max,
            entropy_fix=entropy_fix,
            critical_flow_treatment=critical_flow_treatment
        )

        self.weno_eps = weno_epsilon

        print(f"  WENO-5重构已启用")
        print(f"  空间精度: 5阶")
        print(f"  epsilon: {self.weno_eps}")

    def _compute_rhs(self, h: np.ndarray, Q: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        计算右端项（空间导数+源项）

        使用WENO-5重构替代MUSCL

        dU/dt = L(U) = -1/dx*(F_{i+1/2} - F_{i-1/2}) + S
        """
        n = len(h)

        # 初始化
        dh_dt = np.zeros(n)
        dQ_dt = np.zeros(n)

        # 扩展数组（WENO5需要2层ghost cells）
        h_ext, Q_ext = self._extend_with_ghosts_weno5(h, Q)

        # ===== WENO-5重构（核心）=====
        # weno5_reconstruct期望返回界面值
        # 输入: n+4个单元（包含ghost）
        # 输出: n+1个界面值（实际有用的）

        h_L_ext, h_R_ext = weno5_reconstruct(h_ext, self.weno_eps)
        Q_L_ext, Q_R_ext = weno5_reconstruct(Q_ext, self.weno_eps)

        # weno5_reconstruct返回长度为(n+4)-1 = n+3
        # 有用的界面：索引2到n+2（共n+1个界面）

        # 计算所有界面通量（HLL Riemann求解器）
        F_h = np.zeros(n + 1)
        F_Q = np.zeros(n + 1)

        for i in range(n + 1):
            # 界面i对应重构数组索引i+2
            idx = i + 2
            if idx < len(h_L_ext):
                F_h[i], F_Q[i] = self._hll_flux(
                    h_L_ext[idx], Q_L_ext[idx], h_R_ext[idx], Q_R_ext[idx]
                )
            else:
                # 边界处理：使用最后一个有效值
                idx = len(h_L_ext) - 1
                F_h[i], F_Q[i] = self._hll_flux(
                    h_L_ext[idx], Q_L_ext[idx], h_R_ext[idx], Q_R_ext[idx]
                )

        # 计算每个单元的空间导数
        for i in range(n):
            # 单元i的通量差
            dh_dt[i] = -(F_h[i+1] - F_h[i]) / self.dx
            dQ_dt[i] = -(F_Q[i+1] - F_Q[i]) / self.dx

            # 加上源项
            dQ_dt[i] += self._compute_source_term(h[i], Q[i], i)

        return dh_dt, dQ_dt

    def _extend_with_ghosts_weno5(self, h: np.ndarray, Q: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        扩展数组，添加2层ghost cells（WENO5需要）

        Args:
            h, Q: 内部单元数组 [n]

        Returns:
            h_ext, Q_ext: 扩展数组 [n+4] (2左ghost + n内部 + 2右ghost)
        """
        n = len(h)

        h_ext = np.zeros(n + 4)
        Q_ext = np.zeros(n + 4)

        # 内部单元
        h_ext[2:-2] = h
        Q_ext[2:-2] = Q

        # 左边界ghost cells（基于边界条件）
        if self.bc_left['type'] == 'supercritical':
            # 超临界流：完全由上游决定，直接外推
            h_ext[0] = self.bc_left['h']
            h_ext[1] = self.bc_left['h']
            Q_ext[0] = self.bc_left['Q']
            Q_ext[1] = self.bc_left['Q']
        else:
            # 其他：外推（0阶）
            h_ext[0] = h[0]
            h_ext[1] = h[0]
            Q_ext[0] = Q[0]
            Q_ext[1] = Q[0]

        # 右边界ghost cells
        if self.bc_right['type'] == 'fixed_h':
            # 固定水深
            h_ext[-2] = self.bc_right['h']
            h_ext[-1] = self.bc_right['h']
            Q_ext[-2] = Q[-1]  # 流量外推
            Q_ext[-1] = Q[-1]
        else:
            # 外推（0阶）
            h_ext[-2] = h[-1]
            h_ext[-1] = h[-1]
            Q_ext[-2] = Q[-1]
            Q_ext[-1] = Q[-1]

        return h_ext, Q_ext


def test_weno5_solver():
    """测试WENO5求解器"""
    print("="*80)
    print("WENO5求解器功能测试")
    print("="*80)

    # 简单测试：平底水跃
    L = 100.0
    B = 10.0
    n_cells = 50

    solver = GodunvFVMWENO5(
        width=B,
        length=L,
        n_cells=n_cells,
        manning_n=0.0,
        slope=0.0,
        g=9.81,
        cfl=0.4,
        eps_dry=1e-6,
        weno_epsilon=1e-6
    )

    # 初始条件：简单水跃
    h_init = np.ones(n_cells)
    h_init[:n_cells//2] = 0.5
    h_init[n_cells//2:] = 1.0

    Q_init = np.ones(n_cells) * 5.0

    bc_left = {'type': 'supercritical', 'h': 0.5, 'Q': 5.0}
    bc_right = {'type': 'fixed_h', 'h': 1.0}

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    print(f"\n运行10步测试...")
    for _ in range(10):
        solver.step()

    print(f"\n测试完成:")
    print(f"  时间: t={solver.t:.3f}s")
    print(f"  步数: {solver.step_count}")
    print(f"  水深范围: [{solver.h.min():.3f}, {solver.h.max():.3f}]")
    print(f"  流量范围: [{solver.Q.min():.3f}, {solver.Q.max():.3f}]")

    # 检查数值稳定性
    if np.all(np.isfinite(solver.h)) and np.all(np.isfinite(solver.Q)):
        print("\n✅ WENO5求解器测试通过")
        return True
    else:
        print("\n❌ 出现NaN/Inf")
        return False


if __name__ == '__main__':
    success = test_weno5_solver()
    exit(0 if success else 1)
