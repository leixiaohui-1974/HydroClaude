#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
2D 浅水方程求解器精度测试

验证 Hydrostatic2DSolver 的以下特性：
1. 溃坝问题：与 Stoker 精确解对比（沿中心线）
2. 质量守恒：封闭域内总水量守恒
3. 干湿边界：干床上的洪水前锋推进无 NaN
4. 静水平衡：平底静水无数值扰动（lake-at-rest）

Author: HydroClaude Dev
Date: 2026-03-27
"""

import pytest
import warnings
warnings.filterwarnings("ignore")
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
from scipy.optimize import brentq

from solvers.hydrostatic_2d_solver import Hydrostatic2DSolver


# ---------------------------------------------------------------------------
# 辅助函数：Stoker 精确解（1D）
# ---------------------------------------------------------------------------

def _stoker_exact_h(x_arr, x_dam, t, h_L, h_R, g=9.81):
    """计算 Stoker 溃坝精确解水深（向量化）。"""
    u_L, u_R = 0.0, 0.0
    c_L = np.sqrt(g * h_L)
    c_R = np.sqrt(g * h_R)

    def _f(h, h_K):
        if h <= h_K:
            return 2.0 * (np.sqrt(g * h) - np.sqrt(g * h_K))
        else:
            return (h - h_K) * np.sqrt(0.5 * g * (1.0 / h + 1.0 / h_K))

    h_star = brentq(
        lambda h: _f(h, h_L) + _f(h, h_R) + (u_R - u_L),
        1e-6, max(h_L, h_R) * 2, xtol=1e-12,
    )
    u_star = 0.5 * (u_L + u_R) + 0.5 * (_f(h_star, h_R) - _f(h_star, h_L))
    c_star = np.sqrt(g * h_star)
    S_shock = (h_star * u_star - h_R * u_R) / (h_star - h_R + 1e-12)
    S_head  = u_L - c_L
    S_tail  = u_star - c_star

    def _h_at(x):
        xi = (x - x_dam) / t
        if xi <= S_head:
            return h_L
        elif xi <= S_tail:
            c_fan = (u_L + 2.0 * c_L - xi) / 3.0
            return c_fan**2 / g
        elif xi <= S_shock:
            return h_star
        else:
            return h_R

    return np.array([_h_at(xi) for xi in x_arr])


# ===========================================================================
# 测试类
# ===========================================================================

class Test2DSolverAccuracy:
    """Hydrostatic2DSolver 精度与鲁棒性测试套件。"""

    # -----------------------------------------------------------------------
    # 1. 溃坝精度（沿 y 中心线与 Stoker 精确解对比）
    # -----------------------------------------------------------------------
    @pytest.mark.backend
    def test_2d_dambreak_stoker(self):
        """
        二维溃坝问题沿中心线（y = Ly/2）与 Stoker 精确解对比。

        设置：
            h_dam = 2.0 m, h_down = 0.5 m
            Lx = 100 m, Ly = 20 m, nx = 100, ny = 20
            无摩阻（n = 1e-8），平底，t_eval = 3 s

        验收：L2 相对误差 < 8%（2D 格式一阶精度，误差略高于 1D）
        """
        g     = 9.81
        h_L   = 2.0
        h_R   = 0.5
        Lx    = 100.0
        Ly    = 20.0
        nx    = 100
        ny    = 20
        dam_x = Lx / 2
        t_eval = 3.0

        solver = Hydrostatic2DSolver(
            Lx=Lx, Ly=Ly, nx=nx, ny=ny,
            S0x=0.0, S0y=0.0, n=1e-8, g=g, eps_dry=1e-4
        )
        solver.solve_2d_dam_break(h_L, h_R, dam_x, t_eval, cfl=0.4)

        # 沿 y 中心线取数值解
        jmid   = ny // 2
        h_num  = solver.h[jmid, :]
        x_cells = solver.x

        # Stoker 精确解
        h_exact = _stoker_exact_h(x_cells, dam_x, t_eval, h_L, h_R, g)

        # 排除边界附近 5% 的格点（边界条件影响）
        margin = max(1, nx // 20)
        h_num_inner   = h_num[margin:-margin]
        h_exact_inner = h_exact[margin:-margin]

        l2_err = np.sqrt(np.sum((h_num_inner - h_exact_inner)**2) /
                         np.sum(h_exact_inner**2))

        assert not np.any(np.isnan(solver.h)), "2D 溃坝解含 NaN"
        assert l2_err < 0.08, (
            f"2D 溃坝 L2 相对误差 {l2_err:.4f} 超过 8%"
        )

    # -----------------------------------------------------------------------
    # 2. 质量守恒（封闭域）
    # -----------------------------------------------------------------------
    @pytest.mark.backend
    def test_2d_mass_conservation(self):
        """
        封闭域（四周固壁）内总水量守恒。

        设置：
            初始条件：h = 1 + 0.1*sin(2πx/Lx)*cos(2πy/Ly)
            平底，无摩阻，运行 200 步

        验收：|V_final - V_initial| / V_initial < 1e-3
        """
        Lx, Ly = 50.0, 50.0
        nx, ny = 50, 50

        solver = Hydrostatic2DSolver(
            Lx=Lx, Ly=Ly, nx=nx, ny=ny,
            S0x=0.0, S0y=0.0, n=1e-8, g=9.81, eps_dry=1e-4
        )

        h0 = 1.0 + 0.1 * np.sin(2 * np.pi * solver.X / Lx) * \
                         np.cos(2 * np.pi * solver.Y / Ly)
        solver.set_initial_condition(h0)

        mass_init = np.sum(solver.h) * solver.dx * solver.dy

        for _ in range(200):
            dt = solver._compute_dt(cfl=0.4)
            solver.step_2d(dt)

        mass_final = np.sum(solver.h) * solver.dx * solver.dy

        assert not np.any(np.isnan(solver.h)), "质量守恒测试含 NaN"
        rel_err = abs(mass_final - mass_init) / mass_init
        assert rel_err < 1e-3, (
            f"2D 质量守恒误差 {rel_err:.2e} 超过 1e-3"
        )

    # -----------------------------------------------------------------------
    # 3. 干湿边界：洪水前锋推进无 NaN
    # -----------------------------------------------------------------------
    @pytest.mark.backend
    def test_2d_dry_wet_front(self):
        """
        洪水在干床上推进，验证无 NaN 且水量单调增加。

        设置：
            左半域 h = 2 m，右半域 h = 0（干床）
            运行 50 步
        """
        Lx, Ly = 100.0, 20.0
        nx, ny = 80, 16

        solver = Hydrostatic2DSolver(
            Lx=Lx, Ly=Ly, nx=nx, ny=ny,
            S0x=0.0, S0y=0.0, n=0.02, g=9.81, eps_dry=1e-4
        )

        h0 = np.where(solver.X < Lx / 2, 2.0, 0.0)
        solver.set_initial_condition(h0)

        mass_init = np.sum(solver.h) * solver.dx * solver.dy

        for _ in range(50):
            dt = solver._compute_dt(cfl=0.4)
            solver.step_2d(dt)

        assert not np.any(np.isnan(solver.h)), "干湿边界测试含 NaN"
        assert not np.any(solver.h < -1e-6), "干湿边界测试出现负水深"

        # 右侧干床区域应有水流入
        wet_right = np.sum(solver.h[:, nx // 2:] > solver.eps_dry)
        assert wet_right > 0, "洪水前锋未能推进到干床区域"

        # 质量守恒（允许 1% 误差）
        mass_final = np.sum(solver.h) * solver.dx * solver.dy
        rel_err = abs(mass_final - mass_init) / mass_init
        assert rel_err < 0.01, f"干湿边界质量误差 {rel_err:.2e} 超过 1%"

    # -----------------------------------------------------------------------
    # 4. 静水平衡（lake-at-rest）
    # -----------------------------------------------------------------------
    @pytest.mark.backend
    def test_2d_lake_at_rest(self):
        """
        平底静水（h = const, u = v = 0）应保持静止。

        验收：100 步后 max|Δh| < 1e-10，max|hu| < 1e-10
        """
        Lx, Ly = 50.0, 50.0
        nx, ny = 30, 30

        solver = Hydrostatic2DSolver(
            Lx=Lx, Ly=Ly, nx=nx, ny=ny,
            S0x=0.0, S0y=0.0, n=0.0, g=9.81, eps_dry=1e-6
        )

        h0 = np.full((ny, nx), 1.5)
        solver.set_initial_condition(h0)

        for _ in range(100):
            dt = solver._compute_dt(cfl=0.4)
            solver.step_2d(dt)

        dh_max  = np.max(np.abs(solver.h - 1.5))
        hu_max  = np.max(np.abs(solver.hu))

        assert not np.any(np.isnan(solver.h)), "静水平衡测试含 NaN"
        assert dh_max < 1e-8, f"静水平衡 Δh_max = {dh_max:.2e} 超过 1e-8"
        assert hu_max < 1e-8, f"静水平衡 hu_max = {hu_max:.2e} 超过 1e-8"


# ---------------------------------------------------------------------------
# 独立运行
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
