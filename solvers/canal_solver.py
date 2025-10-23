#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
明渠非恒定流求解器

支持三种数值方法求解Saint-Venant方程：
- EXPLICIT: 显式有限差分法（混合迎风-中心格式）
- PREISSMANN: 四点隐式格式
- HLL: HLL Riemann求解器（有限体积法）

作者: Claude
日期: 2025-10-21
"""

import numpy as np
from scipy.signal import savgol_filter
import sys
import os

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.canal_utils import compute_steady_uniform_flow, compute_manning_friction_slope


class CanalSolver:
    """
    明渠非恒定流求解器

    求解Saint-Venant方程组：
        ∂A/∂t + ∂Q/∂x = 0                       (连续性方程)
        ∂Q/∂t + ∂(Q²/A)/∂x + gA·∂h/∂x = gA(S₀-Sf) (动量方程)

    其中：
        h: 水深 (m)
        Q: 流量 (m³/s)
        A = B*h: 断面面积 (m²)
        Sf: 摩阻坡度 (Manning公式)
        S₀: 渠底坡度
        g: 重力加速度 (m/s²)
    """

    def __init__(self, length: float = 1000.0, nx: int = 201,
                 B: float = 10.0, S0: float = 0.001, n: float = 0.025,
                 g: float = 9.81, method: str = 'preissmann',
                 internal_structures: list = None,
                 x_grid: np.ndarray = None,
                 smooth_weight: float = 0.1):
        """
        初始化求解器

        Args:
            length: 渠道长度 (m)
            nx: 空间离散点数（如果x_grid=None时使用）
            B: 渠道宽度 (m)
            S0: 渠底坡度 (无量纲)
            n: Manning糙率系数 (s/m^(1/3))
            g: 重力加速度 (m/s²)
            method: 数值方法 ('explicit', 'preissmann', 'hll')
            internal_structures: 内部水工建筑物列表 [(position, structure_obj), ...]
            x_grid: 自定义网格点坐标数组（可选，用于非均匀网格）
            smooth_weight: 闸门附近节点平滑权重 (0-1, 默认0.1)
        """
        self.length = length
        self.B = B
        self.S0 = S0
        self.n = n
        self.g = g
        self.method = method.lower()
        self.smooth_weight = smooth_weight  # 闸门附近节点平滑权重

        # 空间离散
        if x_grid is not None:
            # 使用自定义网格（非均匀）
            self.x = x_grid
            self.nx = len(x_grid)
            self.is_uniform_grid = False
            # 计算局部网格间距
            self.dx_local = np.diff(x_grid)
            # 为了兼容性，保留平均dx
            self.dx = np.mean(self.dx_local)
        else:
            # 使用均匀网格
            self.nx = nx
            self.dx = length / (nx - 1)
            self.x = np.linspace(0, length, nx)
            self.is_uniform_grid = True
            # 对于均匀网格，所有局部dx相同
            self.dx_local = np.ones(nx-1) * self.dx

        # 初始化状态变量
        self.h = np.ones(nx) * 1.0  # 初始水深 (m)
        self.Q = np.ones(nx) * 5.0  # 初始流量 (m³/s)

        # Savitzky-Golay滤波参数（用于抑制高频振荡）
        self.filter_window = 11  # 滤波窗口大小（必须为奇数）
        self.filter_order = 3    # 多项式阶数

        # Preissmann格式参数
        self.theta = 0.6   # 时间加权系数 (0.5-1.0)
        self.omega = 0.95  # 松弛因子 (0.5-1.0)

        # 内部边界条件（水工建筑物）
        self.internal_structures = internal_structures or []
        self._setup_internal_structures()

        # 历史记录
        self.h_history = []
        self.Q_history = []
        self.t_history = []

    def _setup_internal_structures(self):
        """设置内部水工建筑物的节点索引"""
        self.structure_indices = []
        self.structure_objects = []

        for position, structure in self.internal_structures:
            # 找到最接近的节点索引
            idx = np.argmin(np.abs(self.x - position))
            self.structure_indices.append(idx)
            self.structure_objects.append(structure)

    def _apply_internal_bc(self, t: float = 0.0, max_iter: int = 10,
                          tol: float = 0.01, relax: float = 0.5,
                          adaptive_relax: bool = False):
        """
        应用内部边界条件（闸门等水工建筑物）

        在闸门位置强制流量满足闸门关系：Q_gate = f(h_upstream, h_downstream, t)
        使用迭代松弛确保数值稳定性

        Args:
            t: 当前时间 (s)，用于时变参数
            max_iter: 最大迭代次数
            tol: 收敛容差 (m³/s)
            relax: 初始松弛因子 (0-1)，较小值更稳定但收敛慢
            adaptive_relax: 是否使用自适应松弛因子
        """
        if not self.structure_indices:
            return

        # 自适应松弛因子参数
        if adaptive_relax:
            relax_current = max(relax, 0.5)  # 提高初始松弛因子
            relax_min = 0.1
            relax_max = 0.95
            residual_prev = None
            residual_prev2 = None  # 用于Aitken加速
            relax_history = [relax_current]

        for iter_count in range(max_iter):
            converged = True
            total_residual = 0.0
            n_structures = 0

            for idx, structure in zip(self.structure_indices, self.structure_objects):
                # 更新结构的当前时间
                structure.update_time(t)

                # 获取闸门上下游水深
                # 注意：idx是闸门所在节点，我们使用idx-1作为上游，idx+1作为下游
                if idx <=0 or idx >= self.nx - 1:
                    continue  # 跳过边界处的结构

                h_up = self.h[idx - 1]
                h_down = self.h[idx + 1]

                # 计算闸门流量（支持时变参数）
                Q_gate_target, _ = structure.calculate_discharge(h_up, h_down, t)

                # 当前闸门位置的流量
                Q_gate_current = self.Q[idx]

                # 计算残差
                residual = Q_gate_target - Q_gate_current
                total_residual += abs(residual)
                n_structures += 1

                # 检查收敛
                if abs(residual) > tol:
                    converged = False

                    # 使用当前松弛因子更新
                    if adaptive_relax:
                        Q_gate_new = Q_gate_current + relax_current * residual
                    else:
                        Q_gate_new = Q_gate_current * (1 - relax) + Q_gate_target * relax

                    # 更新闸门节点流量
                    self.Q[idx] = Q_gate_new

                    # ⚠️  温和的邻近节点平滑（权重降低以减少守恒性破坏）
                    # 使用可配置权重，在稳定性和守恒性之间平衡
                    if idx > 1:
                        Q_neighbor_target = 0.5 * (self.Q[idx - 2] + Q_gate_new)
                        self.Q[idx - 1] = self.Q[idx - 1] * (1 - self.smooth_weight) + Q_neighbor_target * self.smooth_weight
                    if idx < self.nx - 2:
                        Q_neighbor_target = 0.5 * (Q_gate_new + self.Q[idx + 2])
                        self.Q[idx + 1] = self.Q[idx + 1] * (1 - self.smooth_weight) + Q_neighbor_target * self.smooth_weight

            # 自适应调整松弛因子
            if adaptive_relax and n_structures > 0:
                avg_residual = total_residual / n_structures

                if iter_count >= 2 and residual_prev is not None and residual_prev2 is not None:
                    # Aitken加速法: 基于连续三次残差估算最优松弛因子
                    r0, r1, r2 = residual_prev2, residual_prev, avg_residual

                    # 避免除零
                    if abs(r2 - r1) > 1e-10 and abs(r1 - r0) > 1e-10:
                        # Aitken公式: ω_optimal = ω * (1 - (Δr_{n+1} / Δr_n))
                        ratio = (r2 - r1) / (r1 - r0)

                        if 0 < ratio < 1:
                            # 收敛加速
                            relax_new = relax_current / (1 - ratio)
                            relax_current = np.clip(relax_new, relax_min, relax_max)
                        elif ratio < 0:
                            # 振荡检测 -> 降低松弛因子
                            relax_current = max(relax_current * 0.6, relax_min)
                        elif ratio > 1:
                            # 发散趋势 -> 显著降低松弛因子
                            relax_current = max(relax_current * 0.5, relax_min)

                elif residual_prev is not None:
                    # 简单自适应策略（前两次迭代）
                    if avg_residual < residual_prev * 0.7:
                        # 快速收敛 -> 增大松弛因子
                        relax_current = min(relax_current * 1.3, relax_max)
                    elif avg_residual > residual_prev * 1.2:
                        # 发散 -> 减小松弛因子
                        relax_current = max(relax_current * 0.6, relax_min)

                # 更新历史
                residual_prev2 = residual_prev
                residual_prev = avg_residual
                relax_history.append(relax_current)

            if converged:
                break

    def reset_with_steady_state(self, Q0: float) -> float:
        """
        使用恒定均匀流作为初值

        Args:
            Q0: 初始流量 (m³/s)

        Returns:
            恒定均匀流水深 (m)
        """
        h_uniform = compute_steady_uniform_flow(Q0, self.B, self.S0, self.n, self.g)
        self.h[:] = h_uniform
        self.Q[:] = Q0

        # 清空历史记录
        self.h_history = []
        self.Q_history = []
        self.t_history = []

        return h_uniform

    def apply_spatial_filter(self, field: np.ndarray) -> np.ndarray:
        """
        应用Savitzky-Golay空间滤波器

        用于抑制高频空间振荡，同时保持边界条件不变
        **重要**：跳过结构附近的节点，避免平滑真实的物理间断

        Args:
            field: 待滤波的场变量

        Returns:
            滤波后的场变量
        """
        if len(field) < self.filter_window:
            return field

        filtered = savgol_filter(field, self.filter_window,
                                self.filter_order, mode='nearest')

        # 保持边界条件
        filtered[0] = field[0]
        filtered[-1] = field[-1]

        # ✅ 关键改进：保持结构附近的真实物理间断，不要平滑
        # 在结构±3个节点范围内保持原始值
        if self.structure_indices:
            protection_radius = 3  # 保护半径（节点数）
            for idx in self.structure_indices:
                i_start = max(0, idx - protection_radius)
                i_end = min(len(field), idx + protection_radius + 1)
                filtered[i_start:i_end] = field[i_start:i_end]

        return filtered

    def compute_friction_slope(self, h: np.ndarray, Q: np.ndarray) -> np.ndarray:
        """
        计算Manning摩阻坡度

        Args:
            h: 水深数组 (m)
            Q: 流量数组 (m³/s)

        Returns:
            摩阻坡度数组 Sf (无量纲)
        """
        return compute_manning_friction_slope(h, Q, self.B, self.n)

    def step_explicit(self, dt: float, Q_upstream: float,
                     h_downstream: float) -> tuple:
        """
        显式有限差分法（混合迎风-中心格式）

        采用30%迎风 + 70%中心的混合格式以提高稳定性

        Args:
            dt: 时间步长 (s)
            Q_upstream: 上游边界流量 (m³/s)
            h_downstream: 下游边界水深 (m)

        Returns:
            (h_new, Q_new): 更新后的水深和流量数组
        """
        h_old = self.h.copy()
        Q_old = self.Q.copy()
        h_new = h_old.copy()
        Q_new = Q_old.copy()

        Sf = self.compute_friction_slope(h_old, Q_old)

        # 混合格式参数
        upwind_ratio = 0.3  # 迎风格式权重
        central_ratio = 1.0 - upwind_ratio  # 中心格式权重

        # 内部节点更新
        for i in range(1, self.nx - 1):
            if h_old[i] > 1e-6:
                A = self.B * h_old[i]
                V = Q_old[i] / A

                # === 连续性方程 ===
                # 注：使用平均dx以确保数值稳定性
                # 非均匀网格的局部dx需要结构特定的守恒格式（Phase 2工作）
                dQ_dx_central = (Q_old[i+1] - Q_old[i-1]) / (2 * self.dx)

                # 迎风差分
                if Q_old[i] >= 0:
                    dQ_dx_upwind = (Q_old[i] - Q_old[i-1]) / self.dx
                else:
                    dQ_dx_upwind = (Q_old[i+1] - Q_old[i]) / self.dx

                # 混合格式
                dQ_dx = upwind_ratio * dQ_dx_upwind + central_ratio * dQ_dx_central

                # 更新水深
                dh_dt = -dQ_dx / self.B
                h_new[i] = h_old[i] + dt * dh_dt

                # === 动量方程 ===
                # 中心差分
                dh_dx_central = (h_old[i+1] - h_old[i-1]) / (2 * self.dx)

                # 迎风差分
                if Q_old[i] >= 0:
                    dh_dx_upwind = (h_old[i] - h_old[i-1]) / self.dx
                else:
                    dh_dx_upwind = (h_old[i+1] - h_old[i]) / self.dx

                # 混合格式
                dh_dx = upwind_ratio * dh_dx_upwind + central_ratio * dh_dx_central

                # 对流项使用迎风
                if Q_old[i] >= 0:
                    dQ_dx_mom = (Q_old[i] - Q_old[i-1]) / self.dx
                else:
                    dQ_dx_mom = (Q_old[i+1] - Q_old[i]) / self.dx

                # 更新流量
                dQ_dt = (-V * dQ_dx_mom -
                        self.g * A * dh_dx +
                        self.g * A * (self.S0 - Sf[i]))
                Q_new[i] = Q_old[i] + dt * dQ_dt

        # 边界条件
        h_new[0] = h_new[1]           # 上游水深外推
        Q_new[0] = Q_upstream         # 上游流量指定
        h_new[-1] = h_downstream      # 下游水深指定
        Q_new[-1] = Q_new[-2]         # 下游流量外推

        # 应用空间滤波器（抑制振荡）
        h_new = self.apply_spatial_filter(h_new)
        Q_new = self.apply_spatial_filter(Q_new)

        self.h = h_new
        self.Q = Q_new

        return h_new, Q_new

    def step_preissmann(self, dt: float, Q_upstream: float,
                       h_downstream: float) -> tuple:
        """
        Preissmann四点隐式格式

        使用显式预估 + θ加权校正的半隐式方法

        Args:
            dt: 时间步长 (s)
            Q_upstream: 上游边界流量 (m³/s)
            h_downstream: 下游边界水深 (m)

        Returns:
            (h_new, Q_new): 更新后的水深和流量数组
        """
        h_old = self.h.copy()
        Q_old = self.Q.copy()

        # 步骤1: 显式预估
        h_pred, Q_pred = self.step_explicit(dt, Q_upstream, h_downstream)

        # 步骤2: θ加权校正
        # h^(n+1) = ω * [(1-θ)*h^n + θ*h^pred] + (1-ω)*h^n
        self.h = (self.omega * ((1 - self.theta) * h_old + self.theta * h_pred) +
                 (1 - self.omega) * h_old)
        self.Q = (self.omega * ((1 - self.theta) * Q_old + self.theta * Q_pred) +
                 (1 - self.omega) * Q_old)

        # 应用空间滤波器
        self.h = self.apply_spatial_filter(self.h)
        self.Q = self.apply_spatial_filter(self.Q)

        return self.h, self.Q

    def step_hll(self, dt: float, Q_upstream: float,
                h_downstream: float) -> tuple:
        """
        HLL (Harten-Lax-van Leer) 有限体积法

        使用HLL Riemann求解器计算界面通量

        Args:
            dt: 时间步长 (s)
            Q_upstream: 上游边界流量 (m³/s)
            h_downstream: 下游边界水深 (m)

        Returns:
            (h_new, Q_new): 更新后的水深和流量数组
        """
        h_old = self.h.copy()
        Q_old = self.Q.copy()
        h_new = h_old.copy()
        Q_new = Q_old.copy()

        Sf = self.compute_friction_slope(h_old, Q_old)

        # 内部节点更新
        for i in range(1, self.nx - 1):
            # 单元i和i+1的状态
            h_L = h_old[i]
            h_R = h_old[i+1]
            Q_L = Q_old[i]
            Q_R = Q_old[i+1]

            if h_L > 1e-6 and h_R > 1e-6:
                A_L = self.B * h_L
                A_R = self.B * h_R
                V_L = Q_L / A_L
                V_R = Q_R / A_R
                c_L = np.sqrt(self.g * h_L)  # 左侧波速
                c_R = np.sqrt(self.g * h_R)  # 右侧波速

                # HLL波速估计
                S_L = min(V_L - c_L, V_R - c_R)
                S_R = max(V_L + c_L, V_R + c_R)

                # 通量计算
                F1_L = Q_L
                F1_R = Q_R
                F2_L = Q_L * V_L + 0.5 * self.g * self.B * h_L**2
                F2_R = Q_R * V_R + 0.5 * self.g * self.B * h_R**2

                # HLL通量
                if S_L >= 0:
                    F1 = F1_L
                    F2 = F2_L
                elif S_R <= 0:
                    F1 = F1_R
                    F2 = F2_R
                else:
                    F1 = (S_R * F1_L - S_L * F1_R + S_L * S_R * (A_R - A_L)) / (S_R - S_L)
                    F2 = (S_R * F2_L - S_L * F2_R + S_L * S_R * (Q_R - Q_L)) / (S_R - S_L)

                # 更新守恒变量
                # 注：目前使用平均dx以确保稳定性
                if i > 0:
                    A_Lm = self.B * h_old[i-1]
                    dh_dt = -(F1 - Q_old[i-1]) / self.dx / self.B
                    dQ_dt = -(F2 - (Q_old[i-1]**2/A_Lm + 0.5*self.g*self.B*h_old[i-1]**2)) / self.dx
                    dQ_dt += self.g * A_L * (self.S0 - Sf[i])

                    h_new[i] = h_old[i] + dt * dh_dt
                    Q_new[i] = Q_old[i] + dt * dQ_dt

        # 边界条件
        h_new[0] = h_new[1]
        Q_new[0] = Q_upstream
        h_new[-1] = h_downstream
        Q_new[-1] = Q_new[-2]

        # 应用空间滤波器
        h_new = self.apply_spatial_filter(h_new)
        Q_new = self.apply_spatial_filter(Q_new)

        self.h = h_new
        self.Q = Q_new

        return h_new, Q_new

    def step(self, dt: float, Q_upstream: float, h_downstream: float,
             t: float = 0.0, adaptive_relax: bool = False) -> tuple:
        """
        执行一个时间步（统一接口）

        包含内部边界条件（闸门等）的处理

        Args:
            dt: 时间步长 (s)
            Q_upstream: 上游边界流量 (m³/s)
            h_downstream: 下游边界水深 (m)
            t: 当前时间 (s)，用于时变参数
            adaptive_relax: 是否使用自适应松弛因子

        Returns:
            (h, Q): 更新后的水深和流量数组

        Raises:
            ValueError: 如果数值方法未知
        """
        # 步骤1: 标准时间步进
        if self.method == 'explicit':
            h, Q = self.step_explicit(dt, Q_upstream, h_downstream)
        elif self.method == 'preissmann':
            h, Q = self.step_preissmann(dt, Q_upstream, h_downstream)
        elif self.method == 'hll':
            h, Q = self.step_hll(dt, Q_upstream, h_downstream)
        else:
            raise ValueError(f"Unknown numerical method: {self.method}. "
                           f"Available methods: 'explicit', 'preissmann', 'hll'")

        # 步骤2: 应用内部边界条件（闸门等）
        # 关键：在时间步后修正闸门位置的流量，使其满足闸门关系
        if self.internal_structures:
            self._apply_internal_bc(t=t, max_iter=20, tol=0.001, relax=0.3,
                                   adaptive_relax=adaptive_relax)

        return self.h, self.Q

    def save_state(self, t: float):
        """
        保存当前状态到历史记录

        Args:
            t: 当前时间 (s)
        """
        self.h_history.append(self.h.copy())
        self.Q_history.append(self.Q.copy())
        self.t_history.append(t)

    def clear_history(self):
        """清空历史记录"""
        self.h_history = []
        self.Q_history = []
        self.t_history = []

    def get_history(self) -> dict:
        """
        获取历史记录

        Returns:
            包含时间、水深和流量历史的字典
        """
        return {
            'time': np.array(self.t_history),
            'h_history': self.h_history,
            'Q_history': self.Q_history,
            'x': self.x
        }


if __name__ == '__main__':
    # 测试求解器
    print("=== 明渠求解器测试 ===\n")

    # 创建求解器
    solver = CanalSolver(length=1000.0, nx=201, B=10.0, S0=0.001,
                        n=0.025, method='preissmann')

    # 设置初值
    Q0 = 8.0
    h_uniform = solver.reset_with_steady_state(Q0)
    print(f"初始恒定均匀流:")
    print(f"  流量 Q = {Q0} m³/s")
    print(f"  水深 h = {h_uniform:.6f} m")

    # 边界条件
    Q_upstream = Q0
    h_downstream = h_uniform

    # 时间步长
    dt = 0.5
    n_steps = 10

    # 运行模拟
    print(f"\n运行 {n_steps} 步模拟 (dt = {dt} s)...")
    for i in range(n_steps):
        h, Q = solver.step(dt, Q_upstream, h_downstream)
        solver.save_state((i+1) * dt)

        if i % 2 == 0:
            print(f"  Step {i+1}: h_avg = {np.mean(h):.6f} m, Q_avg = {np.mean(Q):.6f} m³/s")

    print("\n✅ 求解器测试完成")
