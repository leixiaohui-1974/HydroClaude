#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
带Ghost Cells的边求解器

Phase 2核心: Ghost Cell方法
- 不修改边界条件
- 通过ghost cells传递信息
- 保持FVM守恒性

作者: HydroClaude Team
日期: 2025-10-27
"""

import numpy as np
from typing import Tuple, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class EdgeWithGhostCells:
    """
    带Ghost Cells的边
    
    结构:
        [ghost_left] + [interior cells] + [ghost_right]
         ↑             ↑                  ↑
         [0]          [1] to [n_cells]   [n_cells+1]
    
    核心思想:
    - ghost cells不由边界条件设置
    - ghost cells由邻居边状态设置
    - 保持FVM的严格守恒性
    """
    
    def __init__(
        self,
        width: float,
        length: float,
        n_cells: int,
        manning_n: float,
        slope: float,
        cfl: float = 0.5,
        g: float = 9.81
    ):
        """
        初始化带ghost cells的边
        
        Args:
            width: 渠道宽度(m)
            length: 长度(m)
            n_cells: 内部单元数
            manning_n: 曼宁系数
            slope: 底坡
            cfl: CFL数
            g: 重力加速度
        """
        self.width = width
        self.B = width  # 别名
        self.length = length
        self.L = length  # 别名
        self.n_cells = n_cells
        self.n = manning_n
        self.S0 = slope
        self.cfl = cfl
        self.g = g
        
        # 总单元数 = 内部 + 2个ghost
        self.n_total = n_cells + 2
        
        # 空间步长
        self.dx = length / n_cells
        
        # 状态向量（包括ghost cells）
        self.h = np.zeros(self.n_total)
        self.Q = np.zeros(self.n_total)
        
        # 时间
        self.t = 0.0
        self.dt = 0.0
        self.step_count = 0
        
        # 初始质量
        self.initial_mass = 0.0
        
        print(f"EdgeWithGhostCells初始化:")
        print(f"  内部单元: {n_cells}")
        print(f"  总单元（含ghost）: {self.n_total}")
        print(f"  dx = {self.dx:.3f} m")
    
    def initialize(self, h_init: float, Q_init: float):
        """
        初始化（仅内部单元）
        
        Args:
            h_init: 初始水深
            Q_init: 初始流量
        """
        # 内部单元 [1] to [n_cells]
        self.h[1:-1] = h_init
        self.Q[1:-1] = Q_init
        
        # ghost cells初始化为内部值
        self.h[0] = h_init
        self.Q[0] = Q_init
        self.h[-1] = h_init
        self.Q[-1] = Q_init
        
        # 计算初始质量（仅内部）
        self.initial_mass = np.sum(self.h[1:-1] * self.B * self.dx)
        
        print(f"  初始化完成，初始质量: {self.initial_mass:.2f} m³")
    
    def set_left_ghost(self, h: float, Q: float):
        """设置左ghost cell"""
        self.h[0] = h
        self.Q[0] = Q
    
    def set_right_ghost(self, h: float, Q: float):
        """设置右ghost cell"""
        self.h[-1] = h
        self.Q[-1] = Q
    
    def get_left_interior_state(self) -> Tuple[float, float]:
        """获取左边界内部单元状态"""
        return self.h[1], self.Q[1]
    
    def get_right_interior_state(self) -> Tuple[float, float]:
        """获取右边界内部单元状态"""
        return self.h[-2], self.Q[-2]
    
    def compute_dt(self) -> float:
        """计算时间步长（基于CFL条件）"""
        # 仅考虑内部单元
        h_interior = self.h[1:-1]
        Q_interior = self.Q[1:-1]
        
        v = Q_interior / (self.B * h_interior + 1e-10)
        c = np.sqrt(self.g * h_interior)
        lambda_max = np.max(np.abs(v) + c)
        
        if lambda_max < 1e-10:
            lambda_max = 1.0
        
        dt = self.cfl * self.dx / lambda_max
        return dt
    
    def hll_flux(self, h_L: float, Q_L: float, h_R: float, Q_R: float) -> np.ndarray:
        """
        HLL Riemann求解器
        
        Args:
            h_L, Q_L: 左状态
            h_R, Q_R: 右状态
        
        Returns:
            F: 通量 [F_h, F_Q]
        """
        # 左右状态
        u_L = Q_L / (self.B * h_L + 1e-10)
        u_R = Q_R / (self.B * h_R + 1e-10)
        
        c_L = np.sqrt(self.g * h_L)
        c_R = np.sqrt(self.g * h_R)
        
        # 波速估计
        s_L = min(u_L - c_L, u_R - c_R)
        s_R = max(u_L + c_L, u_R + c_R)
        
        # 物理通量
        F_L = np.array([Q_L, Q_L * u_L + 0.5 * self.g * self.B * h_L**2])
        F_R = np.array([Q_R, Q_R * u_R + 0.5 * self.g * self.B * h_R**2])
        
        # HLL通量
        if s_L >= 0:
            return F_L
        elif s_R <= 0:
            return F_R
        else:
            U_L = np.array([self.B * h_L, Q_L])
            U_R = np.array([self.B * h_R, Q_R])
            return (s_R * F_L - s_L * F_R + s_L * s_R * (U_R - U_L)) / (s_R - s_L)
    
    def compute_source(self, i: int) -> np.ndarray:
        """
        计算源项
        
        Args:
            i: 单元索引
        
        Returns:
            S: 源项 [S_h, S_Q]
        """
        h = self.h[i]
        Q = self.Q[i]
        
        if h < 1e-6:
            return np.array([0.0, 0.0])
        
        # 摩擦项（Manning公式）
        v = Q / (self.B * h)
        R_h = h  # 水力半径（矩形渠道）
        S_f = (self.n * abs(v) * v) / (R_h**(4/3))
        
        # 底坡项
        S_h = 0.0
        S_Q = self.g * self.B * h * (self.S0 - S_f)
        
        return np.array([S_h, S_Q])
    
    def step(self, dt: Optional[float] = None):
        """
        推进一步（Euler，暂不用TVD-RK2以简化调试）
        
        注意: 仅更新内部单元，ghost cells由外部设置
        
        Args:
            dt: 时间步长（如果None则自动计算）
        """
        if dt is None:
            dt = self.compute_dt()
        
        self.dt = dt
        
        # 简单Euler（调试用）
        self._update_interior_euler(dt)
        
        self.t += dt
        self.step_count += 1
    
    def _update_interior_euler(self, dt: float):
        """Euler更新"""
        # 保存旧值
        h_old = self.h.copy()
        Q_old = self.Q.copy()
        
        # 计算所有界面通量
        fluxes_h = []
        fluxes_Q = []
        
        for i in range(self.n_total - 1):
            F = self.hll_flux(h_old[i], Q_old[i], h_old[i+1], Q_old[i+1])
            fluxes_h.append(F[0])
            fluxes_Q.append(F[1])
        
        fluxes_h = np.array(fluxes_h)
        fluxes_Q = np.array(fluxes_Q)
        
        # 更新内部单元 [1] to [n_cells]
        for i in range(1, self.n_cells + 1):
            # 通量差
            dF_h = fluxes_h[i] - fluxes_h[i-1]
            dF_Q = fluxes_Q[i] - fluxes_Q[i-1]
            
            # 源项
            S = self.compute_source(i)
            
            # 更新（标准FVM）
            self.h[i] = h_old[i] - dt / self.dx * dF_h + dt * S[0]
            self.Q[i] = Q_old[i] - dt / self.dx * dF_Q + dt * S[1]
            
            # 干床保护
            if self.h[i] < 0.001:
                self.h[i] = 0.001
                self.Q[i] = 0.0
    
    def get_mass_error(self) -> float:
        """计算质量守恒误差%（仅内部单元）"""
        current_mass = np.sum(self.h[1:-1] * self.B * self.dx)
        if self.initial_mass > 1e-10:
            return (current_mass - self.initial_mass) / self.initial_mass * 100.0
        return 0.0
    
    def get_state(self) -> dict:
        """获取状态（仅内部单元）"""
        return {
            't': self.t,
            'step': self.step_count,
            'h': self.h[1:-1].copy(),
            'Q': self.Q[1:-1].copy(),
            'x': np.linspace(self.dx/2, self.length - self.dx/2, self.n_cells),
            'mass_error': self.get_mass_error()
        }


if __name__ == '__main__':
    print("=" * 80)
    print("Ghost Cell边求解器测试")
    print("=" * 80)
    
    # 创建边
    edge = EdgeWithGhostCells(
        width=10.0, length=1000.0, n_cells=50,
        manning_n=0.025, slope=0.001,
        cfl=0.5
    )
    
    # 初始化
    edge.initialize(h_init=2.0, Q_init=50.0)
    
    # 设置ghost cells（模拟边界条件）
    edge.set_left_ghost(h=2.0, Q=50.0)
    edge.set_right_ghost(h=2.0, Q=50.0)
    
    # 推进
    print("\n推进500步...")
    for i in range(500):
        edge.step()
        
        if (i + 1) % 100 == 0:
            state = edge.get_state()
            print(f"  步数{i+1:3d}, t={state['t']:6.1f}s, 质量误差={state['mass_error']:+.4f}%")
    
    # 最终结果
    state = edge.get_state()
    print(f"\n最终结果:")
    print(f"  质量误差: {state['mass_error']:.4f}%")
    print(f"  平均水深: {np.mean(state['h']):.3f}m")
    print(f"  平均流量: {np.mean(state['Q']):.3f}m³/s")
    
    if abs(state['mass_error']) < 1.0:
        print("\n✅ Ghost Cell方法有效！")
    else:
        print("\n⚠️ 需要调试")
    
    print("=" * 80)
