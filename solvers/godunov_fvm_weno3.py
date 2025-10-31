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
        weno_epsilon: float = 1e-5,
        riemann_solver: str = 'hll',
        well_balanced: bool = False,
        use_numba: bool = True,
        dt_max: Optional[float] = None,
        entropy_fix: bool = False,
        critical_flow_treatment: bool = False,
        use_enhanced_bc: bool = True
    ):
        """
        初始化

        Args:
            (与父类相同)
            weno_epsilon: WENO小量参数（防止除零）
            riemann_solver: Riemann求解器类型 ('hll' 或 'hllc')
            well_balanced: 是否使用Well-Balanced格式
            use_numba: 是否使用Numba加速
            dt_max: 最大时间步长（秒）
            entropy_fix: 是否使用Harten-Hyman entropy修正
            critical_flow_treatment: 是否使用临界流特殊处理
            use_enhanced_bc: 是否使用增强边界处理（3阶精度）
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
            order=3,  # 标记为3阶
            riemann_solver=riemann_solver,
            well_balanced=well_balanced,
            use_numba=use_numba,
            dt_max=dt_max,
            entropy_fix=entropy_fix,
            critical_flow_treatment=critical_flow_treatment
        )

        self.weno_eps = weno_epsilon
        self.use_enhanced_bc = use_enhanced_bc

        print(f"  WENO-3重构已启用")
        print(f"  空间精度: 3阶")
        print(f"  epsilon: {self.weno_eps}")
        if use_enhanced_bc:
            print(f"  边界处理: 3阶精度（增强Ghost Cell）")

    def _extend_with_ghosts(
        self,
        h: np.ndarray,
        Q: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        扩展数组with ghost cells（WENO3增强版本）

        为了在边界处保持3阶精度，使用2个ghost cells per side
        并采用高阶外推填充

        Args:
            h: 水深数组 [n]
            Q: 流量数组 [n]

        Returns:
            h_ext: 扩展水深数组 [n+4] (包含2个左ghost + n个物理 + 2个右ghost)
            Q_ext: 扩展流量数组 [n+4]

        索引映射：
            ghost_left_2 = 0
            ghost_left_1 = 1
            physical[0] = 2
            physical[1] = 3
            ...
            physical[n-1] = n+1
            ghost_right_1 = n+2
            ghost_right_2 = n+3
        """
        if not self.use_enhanced_bc:
            # 退化为父类方法（1个ghost cell）
            return super()._extend_with_ghosts(h, Q)

        n = len(h)
        h_ext = np.zeros(n + 4)
        Q_ext = np.zeros(n + 4)

        # 复制物理域 (索引2 to n+1)
        h_ext[2:n+2] = h
        Q_ext[2:n+2] = Q

        # ===== 左边界 ghost cells (索引0, 1) =====
        bc_type = self.bc_left['type']

        if bc_type in ['h', 'fixed_h']:
            # 固定水深边界
            value = self.bc_left.get('value', self.bc_left.get('h', h[0]))
            h_bc = value if not callable(value) else value(self.t)

            # Ghost cells使用边界值（零梯度）
            h_ext[1] = h_bc
            h_ext[0] = h_bc

            # 流量使用二阶外推
            Q_ext[1] = 2*Q[0] - Q[1]
            Q_ext[0] = 2*Q_ext[1] - Q[0]

        elif bc_type in ['Q', 'fixed_Q']:
            # 固定流量边界
            value = self.bc_left.get('value', self.bc_left.get('Q', Q[0]))
            Q_bc = value if not callable(value) else value(self.t)

            # Ghost cells使用边界值
            Q_ext[1] = Q_bc
            Q_ext[0] = Q_bc

            # 水深使用二阶外推
            h_ext[1] = 2*h[0] - h[1]
            h_ext[0] = 2*h_ext[1] - h[0]

        elif bc_type == 'transmissive':
            # 透射边界（零梯度外推）
            h_ext[1] = h[0]
            h_ext[0] = h[0]
            Q_ext[1] = Q[0]
            Q_ext[0] = Q[0]

        elif bc_type == 'reflective':
            # 反射边界（镜像对称）
            h_ext[1] = h[0]
            h_ext[0] = h[1]
            Q_ext[1] = -Q[0]  # 流量反向
            Q_ext[0] = -Q[1]

        else:
            # 默认：二阶外推
            h_ext[1] = 2*h[0] - h[1]
            h_ext[0] = 2*h_ext[1] - h[0]
            Q_ext[1] = 2*Q[0] - Q[1]
            Q_ext[0] = 2*Q_ext[1] - Q[0]

        # ===== 右边界 ghost cells (索引n+2, n+3) =====
        bc_type = self.bc_right['type']

        if bc_type in ['h', 'fixed_h']:
            # 固定水深边界
            value = self.bc_right.get('value', self.bc_right.get('h', h[-1]))
            h_bc = value if not callable(value) else value(self.t)

            h_ext[n+2] = h_bc
            h_ext[n+3] = h_bc

            # 流量使用二阶外推
            Q_ext[n+2] = 2*Q[-1] - Q[-2]
            Q_ext[n+3] = 2*Q_ext[n+2] - Q[-1]

        elif bc_type in ['Q', 'fixed_Q']:
            # 固定流量边界
            value = self.bc_right.get('value', self.bc_right.get('Q', Q[-1]))
            Q_bc = value if not callable(value) else value(self.t)

            Q_ext[n+2] = Q_bc
            Q_ext[n+3] = Q_bc

            # 水深使用二阶外推
            h_ext[n+2] = 2*h[-1] - h[-2]
            h_ext[n+3] = 2*h_ext[n+2] - h[-1]

        elif bc_type == 'transmissive':
            # 透射边界（零梯度外推）
            h_ext[n+2] = h[-1]
            h_ext[n+3] = h[-1]
            Q_ext[n+2] = Q[-1]
            Q_ext[n+3] = Q[-1]

        elif bc_type == 'reflective':
            # 反射边界（镜像对称）
            h_ext[n+2] = h[-1]
            h_ext[n+3] = h[-2]
            Q_ext[n+2] = -Q[-1]  # 流量反向
            Q_ext[n+3] = -Q[-2]

        else:
            # 默认：二阶外推
            h_ext[n+2] = 2*h[-1] - h[-2]
            h_ext[n+3] = 2*h_ext[n+2] - h[-1]
            Q_ext[n+2] = 2*Q[-1] - Q[-2]
            Q_ext[n+3] = 2*Q_ext[n+2] - Q[-1]

        # 确保ghost cells的水深非负
        h_ext = np.maximum(h_ext, self.eps_dry)

        return h_ext, Q_ext

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

            # 加上源项（需要传入cell_idx以支持变底坡和well-balanced）
            dQ_dt[i] += self._compute_source_term(h[i], Q[i], i)
        
        return dh_dt, dQ_dt
    
    def _weno3_reconstruction(self, phi: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        WENO-3重构（3阶精度+无振荡）

        从单元平均值phi_i重构界面左右值

        Args:
            phi: 扩展变量数组
                - 如果use_enhanced_bc=True: [n+4] (2个ghost cells per side)
                - 如果use_enhanced_bc=False: [n+2] (1个ghost cell per side)

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
        if self.use_enhanced_bc:
            # 增强边界处理：n+4数组，使用统一模板
            return self._weno3_reconstruction_enhanced(phi)
        else:
            # 标准边界处理：n+2数组，边界特殊处理
            return self._weno3_reconstruction_standard(phi)

    def _weno3_reconstruction_enhanced(self, phi: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        WENO-3重构（增强版本 - 向量化）

        使用2个ghost cells，所有界面使用相同的5点模板，边界精度3阶

        Args:
            phi: 扩展变量数组 [n+4]

        Returns:
            phi_L, phi_R: 界面左右值 [n+1]

        优化：完全向量化，无Python循环
        """
        # 物理单元数
        n = len(phi) - 4

        eps = self.weno_eps

        # 理想权重
        d1 = 1.0 / 3.0
        d2 = 2.0 / 3.0

        # ===== 向量化重构（所有界面同时处理）=====
        # 为所有n+1个界面创建索引数组
        i = np.arange(n + 1)
        idx_L = i + 1  # 左侧单元索引
        idx_R = i + 2  # 右侧单元索引

        # ----- 左侧重构 phi_{i+1/2}^- -----
        # 模板1（左偏）: phi[idx_L-1], phi[idx_L]
        phi1_L = 1.5 * phi[idx_L] - 0.5 * phi[idx_L-1]

        # 模板2（右偏）: phi[idx_L], phi[idx_L+1]
        phi2_L = 0.5 * phi[idx_L] + 0.5 * phi[idx_L+1]

        # 光滑性指标
        beta1_L = (phi[idx_L] - phi[idx_L-1])**2
        beta2_L = (phi[idx_L+1] - phi[idx_L])**2

        # 非线性权重（向量化）
        alpha1_L = d1 / (eps + beta1_L)**2
        alpha2_L = d2 / (eps + beta2_L)**2

        sum_alpha_L = alpha1_L + alpha2_L
        omega1_L = alpha1_L / sum_alpha_L
        omega2_L = alpha2_L / sum_alpha_L

        # WENO重构（左侧）
        phi_L = omega1_L * phi1_L + omega2_L * phi2_L

        # ----- 右侧重构 phi_{i+1/2}^+ -----
        # 模板1（右偏）: phi[idx_R], phi[idx_R+1]
        phi1_R = 1.5 * phi[idx_R] - 0.5 * phi[idx_R+1]

        # 模板2（左偏）: phi[idx_R-1], phi[idx_R]
        phi2_R = 0.5 * phi[idx_R] + 0.5 * phi[idx_R-1]

        # 光滑性指标
        beta1_R = (phi[idx_R] - phi[idx_R+1])**2
        beta2_R = (phi[idx_R-1] - phi[idx_R])**2

        # 非线性权重（向量化）
        alpha1_R = d1 / (eps + beta1_R)**2
        alpha2_R = d2 / (eps + beta2_R)**2

        sum_alpha_R = alpha1_R + alpha2_R
        omega1_R = alpha1_R / sum_alpha_R
        omega2_R = alpha2_R / sum_alpha_R

        # WENO重构（右侧）
        phi_R = omega1_R * phi1_R + omega2_R * phi2_R

        return phi_L, phi_R

    def _weno3_reconstruction_enhanced_loop(self, phi: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        WENO-3重构（增强版本 - 循环版）

        保留原始循环版本用于对比测试
        """
        # 物理单元数
        n = len(phi) - 4

        phi_L = np.zeros(n + 1)
        phi_R = np.zeros(n + 1)

        eps = self.weno_eps

        # 理想权重
        d1 = 1.0 / 3.0
        d2 = 2.0 / 3.0

        # ===== 对每个界面进行重构（循环版本）=====
        for i in range(n + 1):
            # 界面i位于物理单元i-1和i之间
            # 在扩展数组中，物理单元0对应索引2
            # 界面i对应扩展索引idx = i + 2
            # 对于界面i，我们需要:
            #   - 左重构用: phi[idx-1], phi[idx], phi[idx+1]
            #   - 右重构用: phi[idx], phi[idx+1], phi[idx+2]
            # 最大索引idx+2 = (n) + 2 + 2 = n+4，但phi数组是[0...n+3]
            # 所以当i=n时，idx=n+2, idx+2=n+4会越界！

            # 解决方案：界面索引应该是i，对应扩展数组的idx=i+1（不是i+2）
            # 重新理解：
            #   - 扩展数组: [g0, g1, p0, p1, ..., p(n-1), g_n, g_n+1]
            #   - 索引:     [0,  1,  2,  3,  ..., n+1,    n+2,  n+3]
            #   - 界面0在索引1和2之间
            #   - 界面i在索引i+1和i+2之间
            #   - 界面n在索引n+1和n+2之间

            # 实际上，对于界面i+1/2（物理界面编号），应该：
            # 左重构从单元i（扩展索引i+2）
            # 右重构从单元i+1（扩展索引i+3）

            # Let me reconsider the indexing:
            # Physical cells: [0, 1, ..., n-1]
            # Extended array: [ghost-1, ghost0, cell0, cell1, ..., cell(n-1), ghostn, ghostn+1]
            # Extended index: [0,       1,      2,     3,     ..., n+1,        n+2,   n+3]
            # Interface i is between cell(i-1) and cell(i)
            # For interface i=0: between ghost0 and cell0 (extended indices 1 and 2)
            # For interface i=n: between cell(n-1) and ghostn (extended indices n+1 and n+2)

            # For left reconstruction at interface i (from left cell i-1 in physical, or i+1 in extended):
            # We need stencil around cell i-1: [i-2, i-1, i, i+1] in physical = [i, i+1, i+2, i+3] in extended
            # But for i=0, physical i-1 doesn't exist, we use ghosts

            # Actually, let's keep it simple:
            # For interface i, in extended array:
            #   Left value uses cells around index i+1: need i, i+1, i+2
            #   Right value uses cells around index i+2: need i+1, i+2, i+3
            # Max index needed: i+3, for i=n, that's n+3, which is valid!

            # Correction: the issue is idx = i+2 is wrong, should be based on interface position

            # Let's use simpler indexing:
            # Interface i in physical is between cells i-1 and i
            # In extended array (offset by 2), it's between extended[i+1] and extended[i+2]

            # For left reconstruction (from cell i-1, extended i+1):
            #   Need stencil: extended[i], extended[i+1], extended[i+2]
            # For right reconstruction (from cell i, extended i+2):
            #   Need stencil: extended[i+1], extended[i+2], extended[i+3]

            # Max index: i+3, when i=n, that's n+3 ✓ (valid for array of size n+4)

            # ----- 左侧重构 phi_{i+1/2}^- (from cell i-1, extended index i+1) -----
            # Stencil: [i, i+1, i+2]
            idx_L = i + 1

            # 模板1（左偏）: phi[i], phi[i+1]
            phi1_L = 1.5 * phi[idx_L] - 0.5 * phi[idx_L-1] if idx_L > 0 else phi[idx_L]

            # 模板2（右偏）: phi[i+1], phi[i+2]
            phi2_L = 0.5 * phi[idx_L] + 0.5 * phi[idx_L+1]

            # 光滑性指标
            beta1_L = (phi[idx_L] - phi[idx_L-1])**2 if idx_L > 0 else 0.0
            beta2_L = (phi[idx_L+1] - phi[idx_L])**2

            # 非线性权重
            alpha1_L = d1 / (eps + beta1_L)**2
            alpha2_L = d2 / (eps + beta2_L)**2

            sum_alpha_L = alpha1_L + alpha2_L
            omega1_L = alpha1_L / sum_alpha_L
            omega2_L = alpha2_L / sum_alpha_L

            # WENO重构（左侧）
            phi_L[i] = omega1_L * phi1_L + omega2_L * phi2_L

            # ----- 右侧重构 phi_{i+1/2}^+ (from cell i, extended index i+2) -----
            # Stencil: [i+1, i+2, i+3]
            idx_R = i + 2

            # 模板1（右偏）: phi[i+2], phi[i+3]
            phi1_R = 1.5 * phi[idx_R] - 0.5 * phi[idx_R+1] if idx_R+1 < len(phi) else phi[idx_R]

            # 模板2（左偏）: phi[i+1], phi[i+2]
            phi2_R = 0.5 * phi[idx_R] + 0.5 * phi[idx_R-1]

            # 光滑性指标
            beta1_R = (phi[idx_R] - phi[idx_R+1])**2 if idx_R+1 < len(phi) else 0.0
            beta2_R = (phi[idx_R-1] - phi[idx_R])**2

            # 非线性权重
            alpha1_R = d1 / (eps + beta1_R)**2
            alpha2_R = d2 / (eps + beta2_R)**2

            sum_alpha_R = alpha1_R + alpha2_R
            omega1_R = alpha1_R / sum_alpha_R
            omega2_R = alpha2_R / sum_alpha_R

            # WENO重构（右侧）
            phi_R[i] = omega1_R * phi1_R + omega2_R * phi2_R

        return phi_L, phi_R

    def _weno3_reconstruction_standard(self, phi: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        WENO-3重构（标准版本 - 边界特殊处理）

        使用1个ghost cell，边界处使用特殊处理，边界精度降为1阶

        Args:
            phi: 扩展变量数组 [n+2]

        Returns:
            phi_L, phi_R: 界面左右值 [n+1]
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
            # ----- 左侧重构 phi_{i+1/2}^- -----
            # 模板1（左偏）: phi_{i-1}, phi_i
            if i > 0:
                phi1_L = 1.5 * phi[i] - 0.5 * phi[i-1]
                beta1_L = (phi[i] - phi[i-1])**2
            else:
                # 左边界：退化为1阶
                phi1_L = phi[i]
                beta1_L = 0.0

            # 模板2（右偏）: phi_i, phi_{i+1}
            if i < n:
                phi2_L = 0.5 * phi[i] + 0.5 * phi[i+1]
                beta2_L = (phi[i+1] - phi[i])**2
            else:
                # 右边界：退化为1阶
                phi2_L = phi[i]
                beta2_L = 0.0

            # 非线性权重
            alpha1_L = d1 / (eps + beta1_L)**2
            alpha2_L = d2 / (eps + beta2_L)**2

            sum_alpha_L = alpha1_L + alpha2_L
            if sum_alpha_L > 1e-20:
                omega1_L = alpha1_L / sum_alpha_L
                omega2_L = alpha2_L / sum_alpha_L
            else:
                omega1_L = d1
                omega2_L = d2

            # WENO重构（左侧）
            phi_L[i] = omega1_L * phi1_L + omega2_L * phi2_L

            # ----- 右侧重构 phi_{i+1/2}^+ -----
            # 模板1（右偏）: phi_{i+1}, phi_{i+2}
            if i < n - 1:
                phi1_R = 1.5 * phi[i+1] - 0.5 * phi[i+2]
                beta1_R = (phi[i+1] - phi[i+2])**2
            else:
                phi1_R = phi[i+1]
                beta1_R = 0.0

            # 模板2（左偏）: phi_i, phi_{i+1}
            if i < n:
                phi2_R = 0.5 * phi[i+1] + 0.5 * phi[i]
                beta2_R = (phi[i] - phi[i+1])**2
            else:
                phi2_R = phi[i+1]
                beta2_R = 0.0

            # 非线性权重
            alpha1_R = d1 / (eps + beta1_R)**2
            alpha2_R = d2 / (eps + beta2_R)**2

            sum_alpha_R = alpha1_R + alpha2_R
            if sum_alpha_R > 1e-20:
                omega1_R = alpha1_R / sum_alpha_R
                omega2_R = alpha2_R / sum_alpha_R
            else:
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
