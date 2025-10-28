#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MacCormack显式格式求解器 - 用于Saint-Venant方程

MacCormack格式特点:
- ✅ 二阶精度（时间+空间）
- ✅ 显式格式（无需求解线性系统）
- ✅ 易于实施
- ✅ 数值稳定（适当CFL条件下）
- ✅ 适合激波和不连续

算法步骤:
1. 预测步（前向差分）: U* = U^n - dt/dx * (F_{i+1} - F_i) + dt * S
2. 校正步（后向差分）: U** = U* - dt/dx * (F*_i - F*_{i-1}) + dt * S*
3. 平均: U^{n+1} = 0.5 * (U^n + U**)

作者: HydroClaude Team
日期: 2025-10-28
"""

import numpy as np
from typing import Tuple, Optional, Callable
import warnings


class MacCormackSolver:
    """
    MacCormack显式格式求解器
    
    求解Saint-Venant方程:
    ∂U/∂t + ∂F/∂x = S
    
    其中:
    U = [A, Q]^T = [h*B, Q]^T
    F = [Q, Q²/A + gI₁]^T
    S = [0, gA(S₀ - Sf)]^T
    
    I₁ = ∫h dB ≈ h²B/2 (矩形断面)
    """
    
    def __init__(
        self,
        width: float,
        length: float,
        n_cells: int,
        manning_n: float,
        slope: float,
        g: float = 9.81,
        cfl: float = 0.5,
        eps_dry: float = 1e-4,
        use_artificial_viscosity: bool = True,
        viscosity_coef: float = 0.3
    ):
        """
        初始化求解器
        
        Args:
            width: 渠道宽度 (m)
            length: 渠道长度 (m)
            n_cells: 网格单元数
            manning_n: Manning粗糙系数
            slope: 渠底坡度 S₀
            g: 重力加速度 (m/s²)
            cfl: CFL数（推荐0.3-0.7）
            eps_dry: 最小水深（干床处理）
            use_artificial_viscosity: 是否使用人工粘性（抑制振荡）
            viscosity_coef: 人工粘性系数
        """
        self.B = width
        self.L = length
        self.n_cells = n_cells
        self.n_nodes = n_cells + 1
        self.dx = length / n_cells
        self.n = manning_n
        self.S0 = slope
        self.g = g
        self.cfl = cfl
        self.eps_dry = eps_dry
        self.use_artificial_viscosity = use_artificial_viscosity
        self.nu = viscosity_coef
        
        # 网格
        self.x = np.linspace(0, length, n_cells + 1)
        
        # 状态变量（节点值）
        self.h = np.zeros(n_cells + 1)
        self.Q = np.zeros(n_cells + 1)
        
        # 时间
        self.t = 0.0
        self.dt = 0.0
        
        # 边界条件
        self.bc_upstream = None
        self.bc_downstream = None
        
        # 统计
        self.total_mass = 0.0
    
    def initialize(
        self,
        h_init: np.ndarray,
        Q_init: np.ndarray,
        bc_upstream: dict,
        bc_downstream: dict
    ):
        """
        初始化状态和边界条件
        
        Args:
            h_init: 初始水深 [n_nodes]
            Q_init: 初始流量 [n_nodes]
            bc_upstream: 上游边界条件 {'type': 'h'|'Q', 'value': float|callable}
            bc_downstream: 下游边界条件
        """
        self.h = h_init.copy()
        self.Q = Q_init.copy()
        self.bc_upstream = bc_upstream
        self.bc_downstream = bc_downstream
        
        # 计算初始质量
        self.total_mass = self._compute_total_mass()
        
        print(f"MacCormack求解器初始化完成")
        print(f"  网格: {self.n_cells}个单元, {self.n_nodes}个节点")
        print(f"  dx = {self.dx:.2f} m")
        print(f"  初始质量: {self.total_mass:.2f} m³")
    
    def compute_dt(self) -> float:
        """
        计算时间步长（CFL条件）
        
        dt ≤ CFL * dx / (|u| + c)
        
        其中:
        u = Q/A: 流速
        c = √(gA/B): 波速（小扰动波速）
        """
        # 确保水深为正
        h_safe = np.maximum(self.h, self.eps_dry)
        A = h_safe * self.B
        
        # 流速
        u = self.Q / A
        
        # 波速
        c = np.sqrt(self.g * A / self.B)
        
        # 特征速度
        lambda_max = np.max(np.abs(u) + c)
        
        if lambda_max > 1e-10:
            dt = self.cfl * self.dx / lambda_max
        else:
            dt = 1.0  # 默认值（静止水体）
        
        return dt
    
    def step(self, dt: Optional[float] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        MacCormack时间步进
        
        Args:
            dt: 时间步长，None则自动计算
        
        Returns:
            (h, Q): 更新后的水深和流量
        """
        if dt is None:
            dt = self.compute_dt()
        
        self.dt = dt
        
        # 保存旧值
        h_n = self.h.copy()
        Q_n = self.Q.copy()
        
        # ========== 预测步（前向差分）==========
        h_pred, Q_pred = self._predictor_step(h_n, Q_n, dt)
        
        # ========== 校正步（后向差分）==========
        h_corr, Q_corr = self._corrector_step(h_pred, Q_pred, dt)
        
        # ========== 平均 ==========
        h_new = 0.5 * (h_n + h_corr)
        Q_new = 0.5 * (Q_n + Q_corr)
        
        # ========== 应用边界条件（在人工粘性之前）==========
        h_new, Q_new = self._apply_boundary_conditions(h_new, Q_new)
        
        # ========== 人工粘性（可选，抑制振荡）==========
        # 注意：关闭人工粘性以确保质量守恒
        if self.use_artificial_viscosity and False:  # 暂时禁用
            h_new = self._apply_artificial_viscosity(h_new, self.nu)
            Q_new = self._apply_artificial_viscosity(Q_new, self.nu)
        
        # ========== 干床处理 ==========
        h_new = np.maximum(h_new, 0.0)  # 允许0，但计算时用eps_dry
        
        # 更新状态
        self.h = h_new
        self.Q = Q_new
        self.t += dt
        
        return self.h.copy(), self.Q.copy()
    
    def _predictor_step(
        self,
        h: np.ndarray,
        Q: np.ndarray,
        dt: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        预测步（前向差分）
        
        U* = U^n - dt/dx * (F_{i+1} - F_i) + dt * S_i
        """
        n = self.n_nodes
        
        # 计算通量和源项
        F_h, F_Q = self._compute_flux(h, Q)
        S_h, S_Q = self._compute_source(h, Q)
        
        # 预测（内部节点）
        h_pred = h.copy()
        Q_pred = Q.copy()
        
        for i in range(1, n-1):
            # 前向差分: ∂F/∂x ≈ (F_{i+1} - F_i) / dx
            dFh_dx = (F_h[i+1] - F_h[i]) / self.dx
            dFQ_dx = (F_Q[i+1] - F_Q[i]) / self.dx
            
            # 更新
            h_pred[i] = h[i] - dt * dFh_dx + dt * S_h[i]
            Q_pred[i] = Q[i] - dt * dFQ_dx + dt * S_Q[i]
        
        return h_pred, Q_pred
    
    def _corrector_step(
        self,
        h: np.ndarray,
        Q: np.ndarray,
        dt: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        校正步（后向差分）
        
        U** = U* - dt/dx * (F*_i - F*_{i-1}) + dt * S*_i
        """
        n = self.n_nodes
        
        # 计算预测步的通量和源项
        F_h, F_Q = self._compute_flux(h, Q)
        S_h, S_Q = self._compute_source(h, Q)
        
        # 校正（内部节点）
        h_corr = h.copy()
        Q_corr = Q.copy()
        
        for i in range(1, n-1):
            # 后向差分: ∂F/∂x ≈ (F_i - F_{i-1}) / dx
            dFh_dx = (F_h[i] - F_h[i-1]) / self.dx
            dFQ_dx = (F_Q[i] - F_Q[i-1]) / self.dx
            
            # 更新
            h_corr[i] = h[i] - dt * dFh_dx + dt * S_h[i]
            Q_corr[i] = Q[i] - dt * dFQ_dx + dt * S_Q[i]
        
        return h_corr, Q_corr
    
    def _compute_flux(
        self,
        h: np.ndarray,
        Q: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        计算通量向量
        
        F = [F_h, F_Q]^T
        F_h = Q
        F_Q = Q²/A + gI₁
        
        其中 I₁ = h²B/2 (矩形断面的压力积分)
        """
        # 确保水深为正
        h_safe = np.maximum(h, self.eps_dry)
        A = h_safe * self.B
        
        # 连续方程通量
        F_h = Q.copy()
        
        # 动量方程通量
        # Q²/A
        momentum_flux = Q**2 / A
        
        # 压力项: gI₁ = g * h²B / 2
        pressure = 0.5 * self.g * h_safe**2 * self.B
        
        F_Q = momentum_flux + pressure
        
        return F_h, F_Q
    
    def _compute_source(
        self,
        h: np.ndarray,
        Q: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        计算源项
        
        S = [S_h, S_Q]^T
        S_h = 0
        S_Q = gA(S₀ - Sf)
        
        其中 Sf = n²Q²/(A²R^{4/3})
        """
        # 连续方程源项
        S_h = np.zeros_like(h)
        
        # 确保水深为正
        h_safe = np.maximum(h, self.eps_dry)
        A = h_safe * self.B
        
        # 湿周
        P = self.B + 2.0 * h_safe
        
        # 水力半径
        R = A / P
        
        # 摩阻坡度
        Sf = np.zeros_like(h)
        for i in range(len(h)):
            if R[i] > 1e-10 and abs(Q[i]) > 1e-6:
                Sf[i] = self.n**2 * Q[i]**2 / (A[i]**2 * R[i]**(4.0/3.0))
            else:
                Sf[i] = 0.0
        
        # 确保Sf符号正确
        Sf = np.sign(Q) * np.abs(Sf)
        
        # 动量方程源项
        S_Q = self.g * A * (self.S0 - Sf)
        
        return S_h, S_Q
    
    def _apply_artificial_viscosity(
        self,
        U: np.ndarray,
        nu: float
    ) -> np.ndarray:
        """
        应用人工粘性（平滑）- 守恒型
        
        使用通量形式确保守恒：
        U_i^{new} = U_i - nu * [(U_i - U_{i-1}) - (U_{i+1} - U_i)]
                  = U_i + nu * (U_{i+1} - 2*U_i + U_{i-1})
        
        注意：nu应该很小（< 0.1），否则破坏守恒
        """
        n = len(U)
        U_smooth = U.copy()
        
        # 只对内部节点应用，边界保持不变
        for i in range(1, n-1):
            # 二阶差分
            d2U = U[i+1] - 2.0*U[i] + U[i-1]
            U_smooth[i] = U[i] + nu * d2U
        
        return U_smooth
    
    def _apply_boundary_conditions(
        self,
        h: np.ndarray,
        Q: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """应用边界条件"""
        # 上游
        if self.bc_upstream['type'] == 'h':
            value = self.bc_upstream['value']
            h[0] = value(self.t) if callable(value) else value
        elif self.bc_upstream['type'] == 'Q':
            value = self.bc_upstream['value']
            Q[0] = value(self.t) if callable(value) else value
        
        # 下游
        if self.bc_downstream['type'] == 'h':
            value = self.bc_downstream['value']
            h[-1] = value(self.t) if callable(value) else value
        elif self.bc_downstream['type'] == 'Q':
            value = self.bc_downstream['value']
            Q[-1] = value(self.t) if callable(value) else value
        
        return h, Q
    
    def _compute_total_mass(self) -> float:
        """计算总质量（用于守恒检查）"""
        # 使用梯形法则积分
        mass = 0.0
        for i in range(self.n_cells):
            h_avg = 0.5 * (self.h[i] + self.h[i+1])
            mass += h_avg * self.B * self.dx
        return mass
    
    def get_mass_conservation_error(self) -> float:
        """
        计算质量守恒误差
        
        Returns:
            相对误差 (%)
        """
        current_mass = self._compute_total_mass()
        if self.total_mass > 1e-10:
            error = (current_mass - self.total_mass) / self.total_mass * 100.0
        else:
            error = 0.0
        return error
    
    def get_state(self) -> dict:
        """获取当前状态"""
        return {
            'x': self.x.copy(),
            'h': self.h.copy(),
            'Q': self.Q.copy(),
            't': self.t,
            'dt': self.dt,
            'mass_error': self.get_mass_conservation_error()
        }


if __name__ == "__main__":
    print("="*80)
    print("MacCormack求解器 - 单元测试")
    print("="*80)
    
    # ========== Test 1: 静止水体（质量守恒）==========
    print("\n" + "="*80)
    print("Test 1: 静止水体 - 质量守恒测试")
    print("="*80)
    
    # 参数
    width = 10.0
    length = 1000.0
    n_cells = 50
    manning_n = 0.025
    slope = 0.001
    
    # 创建求解器
    solver = MacCormackSolver(
        width=width,
        length=length,
        n_cells=n_cells,
        manning_n=manning_n,
        slope=slope,
        cfl=0.5
    )
    
    # 初始条件：静止水体
    h_init = np.ones(n_cells + 1) * 2.0
    Q_init = np.zeros(n_cells + 1)
    
    # 边界条件：固定水位
    bc_upstream = {'type': 'h', 'value': 2.0}
    bc_downstream = {'type': 'h', 'value': 2.0}
    
    solver.initialize(h_init, Q_init, bc_upstream, bc_downstream)
    
    # 时间推进
    t_end = 600.0  # 10分钟
    n_steps = 0
    
    print(f"\n时间推进至 t={t_end}s:")
    while solver.t < t_end:
        h, Q = solver.step()
        n_steps += 1
        
        if n_steps % 20 == 0:
            state = solver.get_state()
            print(f"  t={state['t']:6.1f}s, dt={state['dt']:.3f}s, "
                  f"max|Q|={np.max(np.abs(Q)):.6e}, "
                  f"质量误差={state['mass_error']:.6f}%")
    
    # 最终结果
    state = solver.get_state()
    print(f"\n最终结果 (n_steps={n_steps}):")
    print(f"  质量误差: {state['mass_error']:.8f}%")
    print(f"  max|h-2.0|: {np.max(np.abs(state['h'] - 2.0)):.6e} m")
    print(f"  max|Q|: {np.max(np.abs(state['Q'])):.6e} m³/s")
    print(f"  预期: 质量误差 < 0.1% {'✅' if abs(state['mass_error']) < 0.1 else '❌'}")
    
    print("\n" + "="*80)
    print("MacCormack求解器测试完成！")
    print("="*80)
