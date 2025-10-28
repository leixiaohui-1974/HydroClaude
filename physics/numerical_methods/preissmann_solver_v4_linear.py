#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Preissmann求解器 v4.0 - 线性化半隐式版本（终极简化）

关键策略：
1. 线性化：避免非线性Q²/A项的复杂性
2. 半隐式：时间项隐式，空间项显式
3. 极简边界：ghost cell方法
4. 最小Jacobian：只保留主对角项

目标：先求收敛，再求精度

作者: HydroClaude Team  
日期: 2025-10-29
"""

import numpy as np
from scipy.sparse import diags
from scipy.sparse.linalg import spsolve
from typing import Tuple, Dict


class PreissmannSolverV4Linear:
    """
    线性化半隐式Preissmann求解器（终极简化版）
    
    核心思想：
    - 线性化Q²/A ≈ 2Q*Q_old/A_old（避免非线性）
    - 半隐式：∂/∂t隐式，∂/∂x显式（简化Jacobian）
    - 主对角Jacobian：只保留∂R_i/∂U_i（避免病态）
    """
    
    def __init__(
        self,
        theta: float = 0.6,
        max_iter: int = 10,
        tolerance: float = 1e-4,
        verbose: bool = False
    ):
        self.theta = theta
        self.max_iter = max_iter
        self.tolerance = tolerance
        self.verbose = verbose
        
        self.last_iterations = 0
        self.last_residual = 0.0
    
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
        求解一个时间步（线性化半隐式）
        
        方程简化为：
        h^{n+1} - h^n + dt/dx * θ*(Q^{n+1}_{i+1} - Q^{n+1}_i) + (1-θ)*(Q^n_{i+1} - Q^n_i) = 0
        Q^{n+1} - Q^n + dt*(...显式项...) = 0
        
        只求解h和Q的增量，Jacobian极简
        """
        n = len(h_old)
        
        # 初始猜测
        h_new = h_old.copy()
        Q_new = Q_old.copy()
        
        # 边界条件
        if 'upstream_level' in boundary_conditions:
            h_new[0] = boundary_conditions['upstream_level']
        if 'downstream_level' in boundary_conditions:
            h_new[-1] = boundary_conditions['downstream_level']
        
        # 线性化迭代（极少次数）
        for iteration in range(self.max_iter):
            # 构建线性系统（对角为主）
            A_mat, b_vec = self._build_linear_system(
                h_old, Q_old, h_new, Q_new,
                dt, dx, width, manning_n, slope, g, boundary_conditions
            )
            
            # 求解
            try:
                dU = spsolve(A_mat, b_vec)
            except:
                if self.verbose:
                    print(f"  求解失败")
                break
            
            # 分离h和Q的增量
            dh = dU[:n]
            dQ = dU[n:]
            
            # 更新（小步长）
            alpha = 0.5  # 松弛因子
            h_new += alpha * dh
            Q_new += alpha * dQ
            
            # 边界条件强制
            if 'upstream_level' in boundary_conditions:
                h_new[0] = boundary_conditions['upstream_level']
            if 'downstream_level' in boundary_conditions:
                h_new[-1] = boundary_conditions['downstream_level']
            
            # 物理约束
            h_new = np.maximum(h_new, 0.01)
            
            # 收敛检查
            residual = np.linalg.norm(dU)
            self.last_residual = residual
            
            if self.verbose:
                print(f"  Iter {iteration}: ||dU||={residual:.6e}")
            
            if residual < self.tolerance:
                self.last_iterations = iteration + 1
                if self.verbose:
                    print(f"  ✅ 收敛")
                break
        else:
            self.last_iterations = self.max_iter
        
        return h_new, Q_new
    
    def _build_linear_system(
        self,
        h_old: np.ndarray,
        Q_old: np.ndarray,
        h_new: np.ndarray,
        Q_new: np.ndarray,
        dt: float,
        dx: float,
        width: float,
        n_manning: float,
        S0: float,
        g: float,
        bc: Dict
    ) -> Tuple[diags, np.ndarray]:
        """
        构建极简线性系统（三对角矩阵）
        
        连续方程（显式空间导数）:
        h^{n+1}_i - h^n_i + dt/dx * [Q^{n+1}_{i+1} - Q^{n+1}_{i-1}]/2 ≈ 0
        
        动量方程（线性化）:
        Q^{n+1}_i - Q^n_i + dt*F(h^{n+1}, Q^n) ≈ 0
        """
        n = len(h_old)
        
        # 对角矩阵（2n×2n，但非常稀疏）
        main_diag = np.ones(2*n)
        upper_diag = np.zeros(2*n-1)
        lower_diag = np.zeros(2*n-1)
        
        b = np.zeros(2*n)
        
        # 系数
        coef_Q = dt / (2.0 * dx)
        
        # ========== 连续方程（方程0 to n-1）==========
        for i in range(n):
            # 边界特殊处理
            if i == 0:
                if 'upstream_level' in bc:
                    # h[0] = const
                    main_diag[i] = 1.0
                    b[i] = 0.0  # h已设为目标值
                else:
                    # 连续方程
                    main_diag[i] = 1.0
                    if i+1 < n:
                        upper_diag[i] = 0.0  # 不耦合h
                    main_diag[n+i] = 0.0
                    if i+1 < n:
                        main_diag[n+i+1] = coef_Q
                    b[i] = h_old[i] - h_new[i]
            
            elif i == n-1:
                if 'downstream_level' in bc:
                    main_diag[i] = 1.0
                    b[i] = 0.0
                else:
                    main_diag[i] = 1.0
                    b[i] = h_old[i] - h_new[i]
            
            else:
                # 内部节点：h_i^{n+1} + coef_Q*(Q_{i+1} - Q_{i-1}) = h_i^n
                main_diag[i] = 1.0
                # Q的贡献（通过耦合）
                b[i] = h_old[i] - h_new[i] + coef_Q * (Q_new[i+1] - Q_new[i-1])
        
        # ========== 动量方程（方程n to 2n-1）==========
        for i in range(n):
            idx = n + i
            
            # 简化：Q^{n+1}_i = Q^n_i - dt*Source
            A_i = max(h_new[i] * width, 0.01 * width)
            V_i = Q_new[i] / A_i if A_i > 0.01*width else 0
            
            # 摩阻
            P = width + 2*h_new[i]
            R = A_i / P if P > 1e-10 else 0
            if R > 1e-10 and abs(V_i) > 1e-6:
                Sf = (n_manning * abs(V_i))**2 / (R**(4/3))
                Sf = np.sign(V_i) * Sf
            else:
                Sf = 0
            
            # 源项（显式）
            source = g * A_i * (S0 - Sf)
            
            # 对流和压力（显式，用旧值）
            if i > 0 and i < n-1:
                A_im = max(h_new[i-1] * width, 0.01*width)
                A_ip = max(h_new[i+1] * width, 0.01*width)
                
                # 线性化对流: Q²/A ≈ 2Q*Q_old/A_old
                conv = (Q_old[i+1]**2/A_ip - Q_old[i-1]**2/A_im) / (2*dx)
                
                # 压力
                press = g * A_i * (h_new[i+1] - h_new[i-1]) / (2*dx)
                
                b[idx] = Q_old[i] - Q_new[i] + dt * (-conv - press + source)
            else:
                # 边界：只用源项
                b[idx] = Q_old[i] - Q_new[i] + dt * source
            
            main_diag[idx] = 1.0
        
        # 构建稀疏矩阵（主对角）
        A_mat = diags([main_diag], [0], shape=(2*n, 2*n), format='csr')
        
        return A_mat, b
    
    def get_diagnostics(self) -> Dict:
        return {
            'iterations': self.last_iterations,
            'residual': self.last_residual,
            'converged': self.last_residual < self.tolerance
        }


if __name__ == "__main__":
    print("="*80)
    print("Preissmann v4.0 (线性化半隐式) - 终极简化测试")
    print("="*80)
    
    solver = PreissmannSolverV4Linear(verbose=True, tolerance=1e-4)
    
    # 简单配置
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
        
        if np.any(np.isnan(h)) or np.any(np.isnan(Q)):
            print("  ❌ 出现NaN，停止")
            break
        
        current_mass = np.sum(h[:-1] * width * dx)
        mass_error = (current_mass - initial_mass) / initial_mass * 100
        
        print(f"  质量: {current_mass:.2f} m³")
        print(f"  质量误差: {mass_error:.6f}%")
        print(f"  max|h-2.0|: {np.max(np.abs(h - 2.0)):.6e}")
        print(f"  max|Q|: {np.max(np.abs(Q)):.6e}")
    
    print(f"\n最终: 质量误差 {mass_error:.6f}%")
    print(f"  目标 < 1%: {'✅' if abs(mass_error) < 1.0 else '❌'}")
    print("="*80)
