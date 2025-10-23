#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
改进的渠道求解器 - FVM思想增强版

将Phase 3 FVM的核心思想融入FDM框架：
1. 严格通量守恒格式
2. 闸门处使用精确闸门通量
3. 移除破坏守恒性的空间滤波

基于canal_solver.py，但采用更严格的守恒形式

作者: Claude
日期: 2025-10-23
"""

import numpy as np
from typing import List, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.canal_solver import CanalSolver
from solvers.riemann_solvers import hll_flux_shallow_water


class CanalSolverImproved(CanalSolver):
    """
    改进的渠道求解器

    核心改进：
    1. 使用严格的通量守恒格式（FVM思想）
    2. 闸门处使用闸门通量方程（不平滑）
    3. 移除守恒性破坏因素
    """

    def __init__(self, *args, use_gate_flux=True, **kwargs):
        """
        Args:
            use_gate_flux: 是否在闸门处使用精确闸门通量（默认True）
            其他参数同CanalSolver
        """
        super().__init__(*args, **kwargs)
        self.use_gate_flux = use_gate_flux

        print("=" * 70)
        print("CanalSolverImproved 初始化")
        print("=" * 70)
        print(f"  守恒格式: FVM-enhanced")
        print(f"  闸门通量: {'精确闸门方程' if use_gate_flux else '标准Riemann求解器'}")
        print(f"  空间滤波: 禁用（保持严格守恒）")
        print("=" * 70)
        print()

    def apply_spatial_filter(self, field: np.ndarray) -> np.ndarray:
        """
        覆盖父类的空间滤波器

        在改进版本中，**完全禁用**空间滤波以保持严格守恒性
        """
        # 直接返回原场，不做任何平滑
        return field

    def step_fvm_conservative(self, dt: float, Q_upstream: float,
                              h_downstream: float) -> tuple:
        """
        严格守恒的FVM格式

        核心改进：
        1. 正确的通量差分：dU/dt = -1/dx * [F(i+1/2) - F(i-1/2)] + S
        2. 闸门处使用闸门通量方程
        3. 无任何平滑操作

        Args:
            dt: 时间步长 (s)
            Q_upstream: 上游边界流量 (m³/s)
            h_downstream: 下游边界水深 (m)

        Returns:
            (h_new, Q_new): 更新后的水深和流量数组
        """
        h_old = self.h.copy()
        Q_old = self.Q.copy()

        # 计算摩阻坡度
        Sf = self.compute_friction_slope(h_old, Q_old)

        # 计算所有界面通量
        # 界面i在节点i和i+1之间
        F_interfaces = np.zeros((self.nx + 1, 2))  # [F_mass, F_momentum]

        # 计算内部界面通量
        for i in range(1, self.nx):
            # 左侧状态（节点i-1）
            h_L = h_old[i-1]
            Q_L = Q_old[i-1]
            A_L = self.B * h_L
            U_L = np.array([A_L, Q_L])

            # 右侧状态（节点i）
            h_R = h_old[i]
            Q_R = Q_old[i]
            A_R = self.B * h_R
            U_R = np.array([A_R, Q_R])

            # 检查是否是闸门界面
            is_gate_interface = False
            gate_info = None

            if self.use_gate_flux and self.structure_indices:
                for idx, structure in zip(self.structure_indices, self.structure_objects):
                    # 闸门在节点idx，对应界面idx和idx+1
                    if i == idx or i == idx + 1:
                        is_gate_interface = True
                        gate_info = structure
                        break

            if is_gate_interface and gate_info is not None:
                # 使用闸门通量方程
                F_interfaces[i] = self._compute_gate_flux_interface(
                    U_L, U_R, gate_info, h_old[idx] if i == idx else h_old[idx-1],
                    h_old[idx+1] if i == idx+1 else h_old[idx]
                )
            else:
                # 使用HLL Riemann求解器
                F_interfaces[i] = hll_flux_shallow_water(U_L, U_R, self.B, self.g)

        # 左边界通量
        F_interfaces[0] = np.array([Q_upstream, 0.0])  # 简化处理

        # 右边界通量
        F_interfaces[-1] = F_interfaces[-2]  # 外推

        # 更新守恒变量
        h_new = h_old.copy()
        Q_new = Q_old.copy()

        for i in range(1, self.nx - 1):
            A_old = self.B * h_old[i]

            # 通量差分
            dF_mass = F_interfaces[i+1][0] - F_interfaces[i][0]
            dF_momentum = F_interfaces[i+1][1] - F_interfaces[i][1]

            # 源项
            S_mass = 0.0
            S_momentum = self.g * A_old * (self.S0 - Sf[i])

            # 时间积分（显式Euler）
            # dA/dt = -1/dx * dF_mass + S_mass
            # dQ/dt = -1/dx * dF_momentum + S_momentum

            dx_local = self.dx_local[i] if hasattr(self, 'dx_local') else self.dx

            dA_dt = -dF_mass / dx_local + S_mass
            dQ_dt = -dF_momentum / dx_local + S_momentum

            A_new = A_old + dt * dA_dt
            Q_new[i] = Q_old[i] + dt * dQ_dt

            # 转换回水深
            h_new[i] = A_new / self.B

        # 边界条件
        h_new[0] = h_new[1]  # 上游水深外推
        Q_new[0] = Q_upstream  # 上游流量固定

        h_new[-1] = h_downstream  # 下游水深固定
        Q_new[-1] = Q_new[-2]  # 下游流量外推

        return h_new, Q_new

    def _compute_gate_flux_interface(self, U_L, U_R, gate_structure,
                                     h_upstream, h_downstream):
        """
        计算闸门界面通量

        使用闸门方程：Q = Cd * a * B * sqrt(2*g*Δh)

        Args:
            U_L: 左侧守恒变量 [A, Q]
            U_R: 右侧守恒变量 [A, Q]
            gate_structure: 闸门对象
            h_upstream: 闸门上游水深
            h_downstream: 闸门下游水深

        Returns:
            F: 通量 [F_mass, F_momentum]
        """
        # 获取闸门参数
        a = gate_structure.get_opening()  # 闸门开度（使用方法调用）
        Cd = gate_structure.Cd  # 流量系数

        # 计算闸门流量
        delta_h = h_upstream - h_downstream

        if h_upstream > a:
            # 淹没出流
            if delta_h > 0:
                Q_gate = Cd * a * self.B * np.sqrt(2 * self.g * delta_h)
            else:
                Q_gate = 0.0
        else:
            # 自由出流
            Q_gate = Cd * a * self.B * np.sqrt(2 * self.g * h_upstream)

        # 质量通量
        F_mass = Q_gate

        # 动量通量：Q*u + 压力项
        # 使用闸门处的平均状态
        A_L, Q_L = U_L
        A_R, Q_R = U_R
        A_avg = 0.5 * (A_L + A_R)
        h_avg = 0.5 * (h_upstream + h_downstream)

        u_gate = Q_gate / A_avg if A_avg > 1e-10 else 0.0

        F_momentum = Q_gate * u_gate + 0.5 * self.g * A_avg * h_avg

        return np.array([F_mass, F_momentum])

    def _apply_internal_bc(self, t: float = 0.0, max_iter: int = 10,
                          tol: float = 0.01, relax: float = 0.5,
                          adaptive_relax: bool = False):
        """
        覆盖父类的内部边界条件应用

        在FVM守恒格式中，闸门通过通量处理，不需要额外的平滑
        """
        # 在改进版本中，闸门已经通过通量方程处理
        # 这里可以留空或做极小的调整

        if not self.structure_indices or not self.use_gate_flux:
            # 如果没有使用闸门通量，回退到父类方法
            super()._apply_internal_bc(t, max_iter, tol, relax, adaptive_relax)
            return

        # 否则，闸门已经在step_fvm_conservative中处理，无需额外操作
        pass

    def step(self, dt: float, Q_upstream: float, h_downstream: float,
             t: float = 0.0, adaptive_relax: bool = False):
        """
        覆盖父类的step方法，使用改进的FVM守恒格式

        Args:
            dt: 时间步长
            Q_upstream: 上游流量
            h_downstream: 下游水深
            t: 当前时间（用于时变参数）
            adaptive_relax: 自适应松弛（在FVM格式中不使用）
        """
        # 使用严格守恒的FVM格式
        self.h, self.Q = self.step_fvm_conservative(dt, Q_upstream, h_downstream)

        # 记录历史
        self.h_history.append(self.h.copy())
        self.Q_history.append(self.Q.copy())
        self.t_history.append(t + dt)
