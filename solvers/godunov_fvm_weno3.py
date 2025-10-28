#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Godunov有限体积法求解器 - WENO-3重构（3阶精度）

核心：
1. ✅ 有限体积法（FVM）- 守恒
2. ✅ WENO-3重构 - 3阶精度+无振荡
3. ✅ HLL Riemann求解器
4. ✅ TVD-RK2 时间积分

Phase 2 - 精度提升！

参考:
- Jiang & Shu (1996) "Efficient implementation of weighted ENO schemes"
- Toro (2009) "Riemann Solvers and Numerical Methods"

作者: HydroClaude Team
日期: 2025-10-27
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from typing import Tuple, Dict, Optional
from solvers.godunov_fvm_solver import GodunvFVMSolver


class GodunvFVMWENO3(GodunvFVMSolver):
    """
    Godunov-FVM求解器 + WENO-3重构
    
    继承Phase 1的GodunvFVMSolver，替换MUSCL重构为WENO-3
    
    WENO-3特性：
    - 3阶空间精度
    - 2个模板（stencils）
    - 自动识别间断
    - 无振荡
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
        eps_dry: float = 1e-6,
        weno_epsilon: float = 1e-5
    ):
        """
        初始化
        
        Args:
            (与父类相同)
            weno_epsilon: WENO小量参数（防止除零）
        """
        # 调用父类初始化，但强制order=3
        super().__init__(
            width=width,
            length=length,
            n_cells=n_cells,
            manning_n=manning_n,
            slope=slope,
            g=g,
            cfl=cfl,
            eps_dry=eps_dry,
            order=3  # 标记为3阶
        )
        
        self.weno_eps = weno_epsilon
        
        print(f"  WENO-3重构已启用")
        print(f"  空间精度: 3阶")
        print(f"  epsilon: {self.weno_eps}")
    
    def _compute_rhs(self, h: np.ndarray, Q: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        计算右端项（空间导数+源项）
        
        覆盖父类方法，使用WENO-3重构替代MUSCL
        
        dU/dt = L(U) = -1/dx*(F_{i+1/2} - F_{i-1/2}) + S
        """
        n = len(h)
        
        # 初始化
        dh_dt = np.zeros(n)
        dQ_dt = np.zeros(n)
        
        # 扩展数组（ghost cells）
        h_ext, Q_ext = self._extend_with_ghosts(h, Q)
        
        # ===== WENO-3重构（核心修改）=====
        h_L, h_R = self._weno3_reconstruction(h_ext)
        Q_L, Q_R = self._weno3_reconstruction(Q_ext)
        
        # 计算所有界面通量（HLL Riemann求解器，复用父类）
        F_h = np.zeros(n + 1)
        F_Q = np.zeros(n + 1)
        
        for i in range(n + 1):
            F_h[i], F_Q[i] = self._hll_flux(
                h_L[i], Q_L[i], h_R[i], Q_R[i]
            )
        
        # 计算每个单元的空间导数
        for i in range(n):
            # 单元i的通量差
            dh_dt[i] = -(F_h[i+1] - F_h[i]) / self.dx
            dQ_dt[i] = -(F_Q[i+1] - F_Q[i]) / self.dx
            
            # 加上源项
            dQ_dt[i] += self._compute_source_term(h[i], Q[i])
        
        return dh_dt, dQ_dt
    
    def _weno3_reconstruction(self, phi: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        WENO-3重构（3阶精度+无振荡）
        
        从单元平均值phi_i重构界面左右值
        
        Args:
            phi: 扩展变量数组 [n+2] (包含ghost cells)
        
        Returns:
            phi_L: 所有界面的左值 [n+1] (从左侧重构)
            phi_R: 所有界面的右值 [n+1] (从右侧重构)
        
        WENO-3算法：
        ----------------
        两个模板：
            Stencil 1 (左偏): phi_{i-1}, phi_i
            Stencil 2 (右偏): phi_i, phi_{i+1}
        
        模板重构值：
            phi^(1) = 3/2*phi_i - 1/2*phi_{i-1}
            phi^(2) = 1/2*phi_i + 1/2*phi_{i+1}
        
        光滑性指标：
            beta_1 = (phi_i - phi_{i-1})^2
            beta_2 = (phi_{i+1} - phi_i)^2
        
        理想权重：
            d_1 = 1/3, d_2 = 2/3
        
        非线性权重：
            alpha_k = d_k / (epsilon + beta_k)^2
            omega_k = alpha_k / sum(alpha_k)
        
        WENO重构：
            phi_{i+1/2}^- = omega_1*phi^(1) + omega_2*phi^(2)
        """
        n = len(phi) - 2  # 内部单元数
        
        phi_L = np.zeros(n + 1)
        phi_R = np.zeros(n + 1)
        
        eps = self.weno_eps
        
        # 理想权重
        d1 = 1.0 / 3.0
        d2 = 2.0 / 3.0
        
        # ===== 对每个界面进行重构 =====
        for i in range(n + 1):
            # 界面i位于单元i-1和i之间
            # phi扩展数组: [ghost_left | 0, 1, ..., n-1 | ghost_right]
            # 界面i对应扩展索引i（ghost_left=0, 第一个内部单元=1）
            
            # ----- 左侧重构 phi_{i+1/2}^- (从左侧单元i向右) -----
            # 使用扩展数组索引: i-1, i, i+1
            
            # 模板1（左偏）: phi_{i-1}, phi_i
            if i > 0:
                phi1_L = 1.5 * phi[i] - 0.5 * phi[i-1]
            else:
                # 左边界
                phi1_L = phi[i]
            
            # 模板2（右偏）: phi_i, phi_{i+1}
            if i < n:
                phi2_L = 0.5 * phi[i] + 0.5 * phi[i+1]
            else:
                # 右边界
                phi2_L = phi[i]
            
            # 光滑性指标
            if i > 0:
                beta1_L = (phi[i] - phi[i-1])**2
            else:
                beta1_L = 0.0
            
            if i < n:
                beta2_L = (phi[i+1] - phi[i])**2
            else:
                beta2_L = 0.0
            
            # 非线性权重（数值稳定版本）
            # 防止beta过大导致alpha溢出
            beta1_L_safe = min(beta1_L, 1e10)
            beta2_L_safe = min(beta2_L, 1e10)
            
            alpha1_L = d1 / (eps + beta1_L_safe)**2
            alpha2_L = d2 / (eps + beta2_L_safe)**2
            
            sum_alpha_L = alpha1_L + alpha2_L
            
            # 防止除零
            if sum_alpha_L > 1e-20:
                omega1_L = alpha1_L / sum_alpha_L
                omega2_L = alpha2_L / sum_alpha_L
            else:
                # 退化为理想权重
                omega1_L = d1
                omega2_L = d2
            
            # WENO重构（左侧）
            phi_L[i] = omega1_L * phi1_L + omega2_L * phi2_L
            
            # ----- 右侧重构 phi_{i+1/2}^+ (从右侧单元i+1向左) -----
            # 镜像过程
            
            # 模板1（右偏）: phi_{i+1}, phi_{i+2}
            if i < n - 1:
                phi1_R = 1.5 * phi[i+1] - 0.5 * phi[i+2]
            else:
                phi1_R = phi[i+1]
            
            # 模板2（左偏）: phi_i, phi_{i+1}
            if i < n:
                phi2_R = 0.5 * phi[i+1] + 0.5 * phi[i]
            else:
                phi2_R = phi[i+1]
            
            # 光滑性指标
            if i < n - 1:
                beta1_R = (phi[i+1] - phi[i+2])**2
            else:
                beta1_R = 0.0
            
            if i < n:
                beta2_R = (phi[i] - phi[i+1])**2
            else:
                beta2_R = 0.0
            
            # 非线性权重（数值稳定版本）
            beta1_R_safe = min(beta1_R, 1e10)
            beta2_R_safe = min(beta2_R, 1e10)
            
            alpha1_R = d1 / (eps + beta1_R_safe)**2
            alpha2_R = d2 / (eps + beta2_R_safe)**2
            
            sum_alpha_R = alpha1_R + alpha2_R
            
            # 防止除零
            if sum_alpha_R > 1e-20:
                omega1_R = alpha1_R / sum_alpha_R
                omega2_R = alpha2_R / sum_alpha_R
            else:
                # 退化为理想权重
                omega1_R = d1
                omega2_R = d2
            
            # WENO重构（右侧）
            phi_R[i] = omega1_R * phi1_R + omega2_R * phi2_R
        
        return phi_L, phi_R
    
    def get_diagnostics(self) -> Dict:
        """
        获取诊断信息
        
        Returns:
            诊断字典，增加WENO特性
        """
        # 计算基本诊断信息
        mass_current = self._compute_total_mass()
        mass_error = (mass_current - self.initial_mass) / self.initial_mass * 100
        
        h_safe = np.maximum(self.h, self.eps_dry)
        A = h_safe * self.B
        u = self.Q / A
        c = np.sqrt(self.g * h_safe)
        Fr = np.abs(u) / c
        
        diag = {
            't': self.t,
            'step_count': self.step_count,
            'dt': self.dt,
            'h_mean': np.mean(self.h),
            'h_max': np.max(self.h),
            'h_min': np.min(self.h),
            'Q_mean': np.mean(self.Q),
            'Q_max': np.max(self.Q),
            'Q_min': np.min(self.Q),
            'Fr_mean': np.mean(Fr),
            'Fr_max': np.max(Fr),
            'mass_error': mass_error,
            'mass_current': mass_current,
            'mass_initial': self.initial_mass,
            # WENO特性
            'spatial_order': 3,
            'reconstruction': 'WENO-3',
            'weno_epsilon': self.weno_eps
        }
        
        return diag


# ===== 简单测试 =====
if __name__ == '__main__':
    print("="*70)
    print("WENO-3求解器测试")
    print("="*70)
    
    # 创建求解器
    solver = GodunvFVMWENO3(
        width=10.0,
        length=1000.0,
        n_cells=100,
        manning_n=0.025,
        slope=0.001,
        cfl=0.5
    )
    
    # 初始化（均匀流）
    h_init = np.ones(100) * 2.0
    Q_init = np.ones(100) * 20.0
    
    bc_left = {'type': 'fixed_Q', 'Q': 20.0}
    bc_right = {'type': 'fixed_h', 'h': 2.0}
    
    solver.initialize(h_init, Q_init, bc_left, bc_right)
    
    # 运行10步
    print("\n运行10步测试:")
    for step in range(10):
        solver.step()
        
        if (step + 1) % 5 == 0:
            diag = solver.get_diagnostics()
            print(f"  步 {step+1}: h_avg={diag['h_mean']:.3f}m, "
                  f"Q_avg={diag['Q_mean']:.2f}m³/s, "
                  f"mass_error={diag['mass_error']:.6f}%")
    
    print("\n✅ WENO-3求解器测试完成!")
    print(f"  空间精度: 3阶")
    print(f"  重构方法: WENO-3")
    print(f"  时间积分: TVD-RK2")
    
    # 最终诊断
    final_diag = solver.get_diagnostics()
    print(f"\n最终状态:")
    print(f"  质量误差: {final_diag['mass_error']:.6f}%")
    print(f"  平均水深: {final_diag['h_mean']:.3f} m")
    print(f"  平均流量: {final_diag['Q_mean']:.2f} m³/s")
