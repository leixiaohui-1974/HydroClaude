#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Preissmann求解器 v3.0 - 矩阵缩放版本
关键改进：变量缩放解决数值病态问题

核心思想：
- h和Q的量纲不同（m vs m³/s），导致Jacobian病态
- 解决方案：对变量进行无量纲化

缩放策略：
h_scaled = h / h_scale  (h_scale = 典型水深，如2m)
Q_scaled = Q / Q_scale  (Q_scale = 典型流量，如10 m³/s)

作者: HydroClaude Team
日期: 2025-10-28
"""

import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve, gmres
from typing import Tuple, Dict
import warnings


class PreissmannSolverV3Scaled:
    """
    Preissmann四点隐式格式求解器 v3.0
    
    关键改进：
    1.  变量缩放（解决矩阵病态）
    2.  正确的方程结构
    3.  GMRES求解器（更鲁棒）
    4.  简化的边界条件
    """
    
    def __init__(
        self,
        theta: float = 0.6,
        max_iter: int = 20,
        tolerance: float = 1e-6,
        h_scale: float = 2.0,    # 典型水深
        Q_scale: float = 10.0,   # 典型流量
        verbose: bool = False
    ):
        """
        初始化求解器
        
        Args:
            theta: 时间加权因子
            max_iter: 最大Newton迭代次数
            tolerance: 收敛容差
            h_scale: 水深缩放因子
            Q_scale: 流量缩放因子
            verbose: 是否输出调试信息
        """
        self.theta = theta
        self.max_iter = max_iter
        self.tolerance = tolerance
        self.h_scale = h_scale
        self.Q_scale = Q_scale
        self.verbose = verbose
        
        self.last_iterations = 0
        self.last_residual = 0.0
        
        if verbose:
            print(f"Preissmann v3.0初始化:")
            print(f"  h缩放因子: {h_scale} m")
            print(f"  Q缩放因子: {Q_scale} m³/s")
    
    def solve_canal_step(
        self,
        h_old: np.ndarray,
        Q_old: np.ndarray,
        dt: float,
        dx: float,
        width: float,
        manning_n: float,
        slope: float,
        boundary_conditions: Dict,
        g: float = 9.81
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        求解一个时间步（使用缩放变量）
        
        内部求解: h_scaled, Q_scaled
        输入输出: h, Q (物理变量)
        """
        n_nodes = len(h_old)
        
        # ========== 缩放到无量纲变量 ==========
        h_old_scaled = h_old / self.h_scale
        Q_old_scaled = Q_old / self.Q_scale
        
        h_new_scaled = h_old_scaled.copy()
        Q_new_scaled = Q_old_scaled.copy()
        
        # 边界条件也需要缩放
        bc_scaled = self._scale_boundary_conditions(boundary_conditions)
        
        # 应用边界条件初值
        h_new_scaled, Q_new_scaled = self._apply_boundary_values(
            h_new_scaled, Q_new_scaled, bc_scaled
        )
        
        # ========== Newton迭代（缩放空间）==========
        for iteration in range(self.max_iter):
            # 构建系统（缩放变量）
            J, R = self._build_system_scaled(
                h_old_scaled, Q_old_scaled,
                h_new_scaled, Q_new_scaled,
                dt, dx, width, manning_n, slope, g, bc_scaled
            )
            
            # 求解线性系统（尝试GMRES）
            try:
                # 先尝试直接求解
                dx_vector = spsolve(J.tocsr(), -R)
            except:
                try:
                    # 失败则用GMRES
                    dx_vector, info = gmres(J.tocsr(), -R, tol=1e-6, restart=20)
                    if info != 0:
                        if self.verbose:
                            print(f"  GMRES未收敛: info={info}")
                except Exception as e:
                    if self.verbose:
                        print(f"  求解失败: {e}")
                    break
            
            n = len(h_old)
            dh_scaled = dx_vector[:n]
            dQ_scaled = dx_vector[n:]
            
            # 限制步长
            max_dh = np.max(np.abs(dh_scaled))
            max_dQ = np.max(np.abs(dQ_scaled))
            
            scale = 1.0
            if max_dh > 0.5:
                scale = min(scale, 0.5 / max_dh)
            if max_dQ > 0.5:
                scale = min(scale, 0.5 / max_dQ)
            
            if scale < 1.0:
                dh_scaled *= scale
                dQ_scaled *= scale
            
            # 更新
            h_new_scaled += dh_scaled
            Q_new_scaled += dQ_scaled
            
            # 物理约束（在缩放空间）
            h_new_scaled = np.maximum(h_new_scaled, 0.01 / self.h_scale)
            
            # 收敛检查
            residual_norm = np.linalg.norm(R)
            self.last_residual = residual_norm
            
            if self.verbose:
                print(f"  Iter {iteration}: ||R||={residual_norm:.6e}")
            
            if residual_norm < self.tolerance:
                self.last_iterations = iteration + 1
                if self.verbose:
                    print(f"   收敛")
                break
        else:
            self.last_iterations = self.max_iter
            if self.verbose:
                print(f"  ️ 未收敛，残差={residual_norm:.6e}")
        
        # ========== 还原到物理变量 ==========
        h_new = h_new_scaled * self.h_scale
        Q_new = Q_new_scaled * self.Q_scale
        
        return h_new, Q_new
    
    def _build_system_scaled(
        self,
        h_old_s: np.ndarray,
        Q_old_s: np.ndarray,
        h_new_s: np.ndarray,
        Q_new_s: np.ndarray,
        dt: float,
        dx: float,
        width: float,
        n_manning: float,
        S0: float,
        g: float,
        bc: Dict
    ) -> Tuple[lil_matrix, np.ndarray]:
        """
        构建缩放后的线性系统
        
        关键：正确处理缩放因子在方程中的传播
        
        原方程: ∂A/∂t + ∂Q/∂x = 0
        缩放后: h_scale*B/dt * ∂h_s/∂t + Q_scale/dx * ∂Q_s/∂x = 0
        
        除以 (h_scale*B/dt) 归一化:
        ∂h_s/∂t + (Q_scale*dt)/(h_scale*B*dx) * ∂Q_s/∂x = 0
        """
        n = len(h_old_s)
        n_cells = n - 1
        theta = self.theta
        
        J = lil_matrix((2*n, 2*n))
        R = np.zeros(2*n)
        
        # 缩放系数
        alpha = (self.Q_scale * dt) / (self.h_scale * width * dx)  # 连续方程
        beta = (self.Q_scale * dt) / (self.h_scale * width * dx)   # 动量方程
        
        # ========== 边界和内部方程 ==========
        
        # 上游边界
        if 'upstream_level' in bc:
            J[0, 0] = 1.0
            R[0] = h_new_s[0] - bc['upstream_level']
        else:
            # 使用连续方程
            self._add_continuity_eq_scaled(J, R, 0, 0, h_old_s, Q_old_s, h_new_s, Q_new_s, alpha, theta, n)
        
        # 内部连续方程
        for i in range(1, n_cells):
            self._add_continuity_eq_scaled(J, R, i, i, h_old_s, Q_old_s, h_new_s, Q_new_s, alpha, theta, n)
        
        # 下游边界
        if 'downstream_level' in bc:
            J[n_cells, n_cells] = 1.0
            R[n_cells] = h_new_s[n_cells] - bc['downstream_level']
        else:
            self._add_continuity_eq_scaled(J, R, n_cells, n_cells-1, h_old_s, Q_old_s, h_new_s, Q_new_s, alpha, theta, n)
        
        # 上游Q边界
        if 'upstream_flow' in bc:
            J[n, n] = 1.0
            R[n] = Q_new_s[0] - bc['upstream_flow']
        else:
            self._add_momentum_eq_scaled(J, R, n, 0, h_old_s, Q_old_s, h_new_s, Q_new_s, dt, dx, width, n_manning, S0, g, theta, n)
        
        # 内部动量方程
        for i in range(1, n_cells):
            self._add_momentum_eq_scaled(J, R, n+i, i, h_old_s, Q_old_s, h_new_s, Q_new_s, dt, dx, width, n_manning, S0, g, theta, n)
        
        # 下游Q边界
        if 'downstream_flow' in bc:
            J[2*n-1, 2*n-1] = 1.0
            R[2*n-1] = Q_new_s[n_cells] - bc['downstream_flow']
        else:
            self._add_momentum_eq_scaled(J, R, 2*n-1, n_cells-1, h_old_s, Q_old_s, h_new_s, Q_new_s, dt, dx, width, n_manning, S0, g, theta, n)
        
        return J, R
    
    def _add_continuity_eq_scaled(
        self,
        J: lil_matrix,
        R: np.ndarray,
        eq_idx: int,
        cell_idx: int,
        h_old_s: np.ndarray,
        Q_old_s: np.ndarray,
        h_new_s: np.ndarray,
        Q_new_s: np.ndarray,
        alpha: float,
        theta: float,
        n: int
    ):
        """
        连续方程（缩放空间，简化版）
        
        ∂h_s/∂t + alpha * ∂Q_s/∂x = 0
        """
        i = cell_idx
        
        # 简化：只用中点
        h_mid_old = 0.5 * (h_old_s[i] + h_old_s[i+1])
        h_mid_new = 0.5 * (h_new_s[i] + h_new_s[i+1])
        
        # 残差
        R[eq_idx] = (h_mid_new - h_mid_old) + alpha * theta * (Q_new_s[i+1] - Q_new_s[i]) + alpha * (1-theta) * (Q_old_s[i+1] - Q_old_s[i])
        
        # Jacobian
        J[eq_idx, i] = 0.5
        J[eq_idx, i+1] = 0.5
        J[eq_idx, n+i] = -alpha * theta
        J[eq_idx, n+i+1] = alpha * theta
    
    def _add_momentum_eq_scaled(
        self,
        J: lil_matrix,
        R: np.ndarray,
        eq_idx: int,
        cell_idx: int,
        h_old_s: np.ndarray,
        Q_old_s: np.ndarray,
        h_new_s: np.ndarray,
        Q_new_s: np.ndarray,
        dt: float,
        dx: float,
        width: float,
        n_manning: float,
        S0: float,
        g: float,
        theta: float,
        n: int
    ):
        """
        动量方程（缩放空间，简化版）
        """
        i = cell_idx
        
        # 还原到物理空间计算（简化）
        h_mid = 0.5 * (h_new_s[i] + h_new_s[i+1]) * self.h_scale
        Q_mid = 0.5 * (Q_new_s[i] + Q_new_s[i+1]) * self.Q_scale
        
        h_mid_old = 0.5 * (h_old_s[i] + h_old_s[i+1]) * self.h_scale
        Q_mid_old = 0.5 * (Q_old_s[i] + Q_old_s[i+1]) * self.Q_scale
        
        A = max(h_mid * width, 1e-4 * width)
        
        # 时间导数
        dQ_dt = (Q_mid - Q_mid_old) / dt
        
        # 对流项（简化）
        Q_new_phys = Q_new_s * self.Q_scale
        h_new_phys = h_new_s * self.h_scale
        A_i = max(h_new_phys[i] * width, 1e-4 * width)
        A_i1 = max(h_new_phys[i+1] * width, 1e-4 * width)
        d_Q2A = theta * (Q_new_phys[i+1]**2/A_i1 - Q_new_phys[i]**2/A_i) / dx
        
        # 压力项
        dh_dx = theta * (h_new_phys[i+1] - h_new_phys[i]) / dx
        pressure = g * A * dh_dx
        
        # 摩阻（简化）
        V = Q_mid / A if A > 1e-4 * width else 0
        P = width + 2*h_mid
        R_h = A / P if P > 1e-10 else 0
        if R_h > 1e-10 and abs(V) > 1e-6:
            Sf = (n_manning * abs(V))**2 / (R_h**(4/3))
            Sf = np.sign(V) * Sf
        else:
            Sf = 0
        
        source = g * A * (S0 - Sf)
        
        # 残差（归一化）
        R[eq_idx] = (dQ_dt + d_Q2A + pressure - source) * dt / self.Q_scale
        
        # Jacobian（简化）
        J[eq_idx, i] = 0.5 * width * self.h_scale / self.Q_scale
        J[eq_idx, i+1] = 0.5 * width * self.h_scale / self.Q_scale
        J[eq_idx, n+i] = 0.5
        J[eq_idx, n+i+1] = 0.5
    
    def _scale_boundary_conditions(self, bc: Dict) -> Dict:
        """缩放边界条件"""
        bc_scaled = {}
        if 'upstream_level' in bc:
            bc_scaled['upstream_level'] = bc['upstream_level'] / self.h_scale
        if 'upstream_flow' in bc:
            bc_scaled['upstream_flow'] = bc['upstream_flow'] / self.Q_scale
        if 'downstream_level' in bc:
            bc_scaled['downstream_level'] = bc['downstream_level'] / self.h_scale
        if 'downstream_flow' in bc:
            bc_scaled['downstream_flow'] = bc['downstream_flow'] / self.Q_scale
        return bc_scaled
    
    def _apply_boundary_values(self, h_s, Q_s, bc_scaled):
        """应用边界条件初值（缩放空间）"""
        if 'upstream_level' in bc_scaled:
            h_s[0] = bc_scaled['upstream_level']
        if 'upstream_flow' in bc_scaled:
            Q_s[0] = bc_scaled['upstream_flow']
        if 'downstream_level' in bc_scaled:
            h_s[-1] = bc_scaled['downstream_level']
        if 'downstream_flow' in bc_scaled:
            Q_s[-1] = bc_scaled['downstream_flow']
        return h_s, Q_s


if __name__ == "__main__":
    print("="*80)
    print("Preissmann v3.0 (缩放版) - 测试")
    print("="*80)
    
    # 简单测试
    solver = PreissmannSolverV3Scaled(
        h_scale=2.0,
        Q_scale=0.1,  # 静止水体，Q很小
        verbose=True
    )
    
    n_cells = 10
    length = 1000.0
    dx = length / n_cells
    width = 10.0
    manning_n = 0.025
    slope = 0.001
    dt = 60.0
    
    h_init = np.ones(n_cells + 1) * 2.0
    Q_init = np.zeros(n_cells + 1)
    
    bc = {
        'upstream_level': 2.0,
        'downstream_level': 2.0
    }
    
    initial_mass = np.sum(h_init[:-1] * width * dx)
    print(f"\n初始质量: {initial_mass:.2f} m³")
    
    h = h_init.copy()
    Q = Q_init.copy()
    
    print(f"\n时间推进 5步:")
    for step in range(5):
        print(f"\n步骤 {step+1}:")
        h, Q = solver.solve_canal_step(
            h, Q, dt, dx, width, manning_n, slope, bc
        )
        
        current_mass = np.sum(h[:-1] * width * dx)
        mass_error = (current_mass - initial_mass) / initial_mass * 100
        
        print(f"  质量: {current_mass:.2f} m³")
        print(f"  质量误差: {mass_error:.6f}%")
        print(f"  max|Q|: {np.max(np.abs(Q)):.6e}")
    
    print(f"\n最终: 质量误差 {mass_error:.6f}% {'' if abs(mass_error)<0.1 else ''}")
    print("="*80)
