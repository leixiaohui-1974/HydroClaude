#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Godunov有限体积法求解器（标准守恒格式）

核心：
1. ✅ 有限体积法（FVM）- 真正守恒
2. ✅ HLL Riemann求解器 - 计算界面通量
3. ✅ TVD-RK2 时间积分 - 高精度+稳定
4. ✅ Minmod限制器 - 二阶精度+单调性

这是国际标准的1D水动力学求解器实现！

参考: Toro (2009) "Riemann Solvers and Numerical Methods for Fluid Dynamics"

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
from typing import Tuple, Dict, Optional

# 导入特征线边界条件
from .boundary_conditions import CharacteristicBC

# 尝试导入Numba加速函数
try:
    from .riemann_numba import (
        hll_flux_numba,
        muscl_reconstruction_numba,
        compute_all_fluxes_numba,
        compute_spatial_derivatives_numba
    )
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False


class GodunvFVMSolver:
    """
    Godunov有限体积法求解器
    
    求解Saint-Venant方程守恒律形式:
    ∂U/∂t + ∂F/∂x = S
    
    其中:
    U = [h, Q]^T  (守恒变量)
    F = [Q, Q²/A + 0.5*g*h²*B]^T  (通量)
    S = [0, g*A*(S0 - Sf)]^T  (源项)
    
    离散（有限体积）:
    dU_i/dt = -1/dx * (F_{i+1/2} - F_{i-1/2}) + S_i
    
    其中 F_{i+1/2} 用HLL Riemann求解器计算
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
        order: int = 2,
        riemann_solver: str = 'hll',
        well_balanced: bool = False,
        use_numba: bool = True,
        source_term_method: str = 'standard'
    ):
        """
        初始化

        Args:
            width: 渠宽 (m)
            length: 渠长 (m)
            n_cells: 单元数
            manning_n: Manning系数
            slope: 坡度 (可以是标量或数组)
            g: 重力加速度
            cfl: CFL数 (建议0.5-0.8)
            eps_dry: 干床阈值
            order: 空间精度 (1=一阶, 2=二阶MUSCL)
            riemann_solver: Riemann求解器类型 ('hll' 或 'hllc')
                          默认'hll'（更稳定）
                          'hllc'在短时间激波捕捉上更精确，但长时间积分稳定性需改进
            well_balanced: 是否使用well-balanced格式 (默认False)
                          True时使用hydrostatic reconstruction，提高稳定性
            use_numba: 是否使用Numba JIT加速 (默认True)
                      True时使用编译版本，速度提升10-50倍
            source_term_method: 源项计算方法 ('standard' 或 'interface')
                              'standard': 点值法 S = g*A*(S0 - Sf)
                              'interface': 界面法（Zhou's Surface Gradient Method启发）
                                         底坡源项从界面值计算，更精确平衡
        """
        self.B = width
        self.L = length
        self.n_cells = n_cells
        self.dx = length / n_cells
        self.n = manning_n

        # 支持标量或数组形式的坡度
        if isinstance(slope, (int, float)):
            self.S0 = np.ones(n_cells) * slope
        else:
            self.S0 = np.asarray(slope)
            if len(self.S0) != n_cells:
                raise ValueError(f"slope数组长度({len(self.S0)})必须等于单元数({n_cells})")

        self.g = g
        self.cfl = cfl
        self.eps_dry = eps_dry
        self.order = order
        self.riemann_solver = riemann_solver.lower()
        self.well_balanced = well_balanced
        self.source_term_method = source_term_method.lower()

        # 验证source_term_method参数
        if self.source_term_method not in ['standard', 'interface']:
            raise ValueError(f"source_term_method必须是'standard'或'interface'，当前值: {source_term_method}")

        # ⚠️ Interface方法当前禁用（2025-10-29测试失败）
        if self.source_term_method == 'interface':
            raise NotImplementedError(
                "\n" + "="*80 + "\n"
                "❌ Interface Source Method当前禁用\n"
                "="*80 + "\n"
                "原因: 简单的界面法实现导致质量守恒恶化（61% → 114%）\n"
                "\n"
                "测试结果（MacDonald场景）:\n"
                "  - Standard方法: 质量误差 61.41%\n"
                "  - Interface方法: 质量误差 114.17% ❌ 恶化52.76%\n"
                "\n"
                "问题根源:\n"
                "  Zhou's Surface Gradient Method需要完整实现:\n"
                "  1. 重构水面高程 η = h + z_b (NOT IMPLEMENTED)\n"
                "  2. 从η还原界面水深 h_L, h_R (NOT IMPLEMENTED)\n"
                "  3. 底坡源项自动平衡 (INCORRECTLY IMPLEMENTED)\n"
                "\n"
                "当前实现只做了第3步，导致通量和源项不一致，破坏守恒性。\n"
                "\n"
                "正确实现需要:\n"
                "  - 修改_compute_rhs的reconstruction逻辑\n"
                "  - 添加η重构分支\n"
                "  - 完整测试验证\n"
                "\n"
                "临时方案: 使用 source_term_method='standard'\n"
                "长期修复: 完整实现Zhou's SGM或使用其他方法\n"
                "\n"
                "参考文档:\n"
                "  - docs/INTERFACE_SOURCE_METHOD_FAILURE_ANALYSIS.md\n"
                "  - Zhou et al. (2001) JCP 168(1):1-25\n"
                "="*80
            )

        # Numba加速
        self.use_numba = use_numba and NUMBA_AVAILABLE
        if use_numba and not NUMBA_AVAILABLE:
            print("  ⚠️  Numba未安装，回退到纯Python版本")

        if self.riemann_solver not in ['hll', 'hllc']:
            raise ValueError(f"Riemann求解器必须是'hll'或'hllc'，当前值: {riemann_solver}")

        # CRITICAL: HLLC求解器在Lake at Rest测试中失败
        # 测试结果显示长时间积分时产生NaN，质量守恒完全崩溃
        # 详见: LAKE_AT_REST_TEST_REPORT.md
        if self.riemann_solver == 'hllc':
            raise NotImplementedError(
                "\n" + "="*80 + "\n"
                "❌ HLLC求解器已临时禁用\n"
                "="*80 + "\n"
                "原因: Lake at Rest P0测试发现HLLC在长时间积分时产生NaN\n"
                "      质量守恒计算失败，求解器完全崩溃\n"
                "\n"
                "测试结果:\n"
                "  - 模拟时间: 100秒\n"
                "  - 总步数: 112步（提前终止）\n"
                "  - 质量误差: NaN (完全失败)\n"
                "  - 状态: 🔴 P0 BLOCKING FAILURE\n"
                "\n"
                "临时方案: 请使用 riemann_solver='hll' 代替\n"
                "长期修复: Issue #XXX - 修复或重写HLLC求解器\n"
                "\n"
                "参考文档:\n"
                "  - LAKE_AT_REST_TEST_REPORT.md (测试结果详细分析)\n"
                "  - DEVELOPMENT_STANDARDS.md (P0测试定义)\n"
                "="*80
            )

        # 单元中心守恒变量
        self.h = np.zeros(n_cells)  # 水深
        self.Q = np.zeros(n_cells)  # 流量

        # 单元中心坐标
        self.x = np.linspace(0.5*self.dx, length - 0.5*self.dx, n_cells)

        # 计算单元中心底高程（用于well-balanced格式）
        # 从下游（x=0）开始积分：z_b(x) = z_0 - ∫S0(ξ)dξ
        # 这里假设下游底高程为0
        self.z_b = np.zeros(n_cells)
        for i in range(n_cells):
            if i == 0:
                self.z_b[i] = self.S0[i] * self.x[i]  # 从x=0到x[0]
            else:
                # 使用梯形积分
                self.z_b[i] = self.z_b[i-1] + 0.5 * (self.S0[i-1] + self.S0[i]) * self.dx

        # 检查是否有变化的底高程
        z_b_range = np.max(self.z_b) - np.min(self.z_b)
        has_variable_bottom = z_b_range > 1e-10  # 底高程变化 > 0.1mm

        # WARNING: 变底高程但未启用well-balanced格式
        if has_variable_bottom and not self.well_balanced:
            import warnings
            warnings.warn(
                "\n" + "="*80 + "\n"
                "⚠️  检测到变化的底高程，但未启用Well-Balanced格式！\n"
                "="*80 + "\n"
                f"底高程变化范围: {np.min(self.z_b):.2f} ~ {np.max(self.z_b):.2f} m "
                f"(总变化 {z_b_range:.2f} m)\n"
                "当前设置: well_balanced=False\n"
                "\n"
                "Lake at Rest P0测试结果显示:\n"
                "  - 变底高程（2m凸起）: 水面扰动 3.99 m ❌\n"
                "  - 陡峭底坡（5m台阶）: 水面扰动 11.35 m ❌\n"
                "  - 质量守恒误差: 0.01% ~ 2%\n"
                "\n"
                "这意味着当前求解器可能产生:\n"
                "  1. 虚假的水流（静水状态下出现流速）\n"
                "  2. 非物理的水面扰动（米级误差）\n"
                "  3. 质量守恒恶化\n"
                "\n"
                "建议操作:\n"
                "  1. 如果是静水或缓流问题，设置 well_balanced=True\n"
                "     （需要先实现Hydrostatic Reconstruction - 开发中）\n"
                "  2. 如果底坡很小（< 0.001），可以忽略此警告\n"
                "  3. 如果是激波/溃坝问题，当前格式可能适用\n"
                "\n"
                "参考文档:\n"
                "  - LAKE_AT_REST_TEST_REPORT.md (详细测试结果)\n"
                "  - DEVELOPMENT_STANDARDS.md (质量标准)\n"
                "="*80,
                UserWarning,
                stacklevel=2
            )

        # 时间
        self.t = 0.0
        self.dt = 0.0

        # 边界条件
        self.bc_left = None
        self.bc_right = None

        # 特征线边界条件处理器
        self.characteristic_bc = CharacteristicBC(g=g)

        # 统计
        self.initial_mass = 0.0
        self.step_count = 0
        
        print(f"Godunov-FVM求解器初始化:")
        print(f"  单元数: {n_cells}")
        print(f"  dx = {self.dx:.3f} m")
        print(f"  空间精度: {order}阶")
        print(f"  时间积分: TVD-RK2")
        print(f"  Riemann求解器: {self.riemann_solver.upper()}")
        if self.well_balanced:
            print(f"  Well-Balanced: 启用 (Hydrostatic Reconstruction)")
        if self.use_numba:
            print(f"  🚀 Numba JIT: 启用 (高性能模式)")
    
    def initialize(
        self,
        h_init: np.ndarray,
        Q_init: np.ndarray,
        bc_left: Dict,
        bc_right: Dict
    ):
        """初始化（单元平均值）"""
        self.h = h_init.copy()
        self.Q = Q_init.copy()
        self.bc_left = bc_left
        self.bc_right = bc_right

        # 计算初始质量
        self.initial_mass = self._compute_total_mass(exclude_boundary_cells=False)

        print(f"  初始质量: {self.initial_mass:.2f} m³")
    
    def compute_dt(self) -> float:
        """CFL条件计算时间步长"""
        h_safe = np.maximum(self.h, self.eps_dry)
        A = h_safe * self.B
        u = self.Q / A
        c = np.sqrt(self.g * h_safe)
        
        lambda_max = np.max(np.abs(u) + c)
        
        if lambda_max > 1e-10:
            dt = self.cfl * self.dx / lambda_max
        else:
            dt = 1.0
        
        return dt
    
    def step(self, dt: Optional[float] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        TVD-RK2时间步进
        
        RK2 (Heun's method):
        1. U* = U^n + dt * L(U^n)
        2. U^{n+1} = 0.5*(U^n + U*) + 0.5*dt*L(U*)
        
        其中 L(U) = -1/dx*(F_{i+1/2} - F_{i-1/2}) + S
        """
        if dt is None:
            dt = self.compute_dt()
        
        self.dt = dt
        
        # 保存初值
        h_n = self.h.copy()
        Q_n = self.Q.copy()
        
        # === 第1步：前向欧拉 ===
        dh_dt, dQ_dt = self._compute_rhs(h_n, Q_n)
        h_star = h_n + dt * dh_dt
        Q_star = Q_n + dt * dQ_dt

        # 不在中间步骤强制边界条件（避免质量泄漏）
        # h_star, Q_star = self._apply_bc(h_star, Q_star)

        # 干床处理
        h_star = np.maximum(h_star, 0.0)

        # === 第2步：梯形修正 ===
        dh_dt_star, dQ_dt_star = self._compute_rhs(h_star, Q_star)
        self.h = 0.5 * (h_n + h_star) + 0.5 * dt * dh_dt_star
        self.Q = 0.5 * (Q_n + Q_star) + 0.5 * dt * dQ_dt_star

        # 只在最后强制边界条件
        self.h, self.Q = self._apply_bc(self.h, self.Q)
        
        # 干床
        self.h = np.maximum(self.h, 0.0)
        
        self.t += dt
        self.step_count += 1
        
        return self.h.copy(), self.Q.copy()
    
    def _compute_rhs(self, h: np.ndarray, Q: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        计算右端项（空间导数+源项）
        
        dU/dt = L(U) = -1/dx*(F_{i+1/2} - F_{i-1/2}) + S
        
        Returns:
            dh/dt, dQ/dt
        """
        n = len(h)
        
        # 初始化
        dh_dt = np.zeros(n)
        dQ_dt = np.zeros(n)
        
        # 扩展数组（ghost cells）
        h_ext, Q_ext = self._extend_with_ghosts(h, Q)

        # Well-balanced: 重构水面高程 η = h + z_b
        if self.well_balanced:
            # 计算水面高程（cell centers）
            eta = h + self.z_b

            # 扩展eta到ghost cells
            eta_ext = np.zeros(n + 2)
            eta_ext[1:n+1] = eta

            # 左ghost：外推eta（而非重构 h_bc + z_b_ghost）
            # 关键：对于Lake at Rest，eta应该恒定，所以ghost的eta应该从内部外推
            if self.bc_left['type'] == 'h':
                # 🔧 BUG修复：不能用 eta = h_bc + z_b_ghost（z_b_ghost≠z_b_boundary）
                # 正确做法：外推eta从边界单元
                # 边界单元eta = h_bc + z_b[0]，ghost应该保持这个eta
                value = self.bc_left['value']
                h_bc = value if not callable(value) else value(self.t)
                eta_bc = h_bc + self.z_b[0]  # 边界单元的水面高程
                # 对于Lake at Rest：保持eta恒定
                eta_ext[0] = eta_bc
            else:  # Q boundary
                # 使用内部eta外推
                eta_ext[0] = eta[0]

            # 右ghost：同样外推eta
            if self.bc_right['type'] == 'h':
                value = self.bc_right['value']
                h_bc = value if not callable(value) else value(self.t)
                eta_bc = h_bc + self.z_b[n-1]  # 边界单元的水面高程
                # 对于Lake at Rest：保持eta恒定
                eta_ext[n+1] = eta_bc
            else:  # Q boundary
                eta_ext[n+1] = eta[n-1]

            # 重构水面高程
            if self.order == 2:
                eta_L, eta_R = self._muscl_reconstruction(eta_ext)
            else:
                eta_L = eta_ext[:-1]
                eta_R = eta_ext[1:]

            # 获取界面底高程（使用单元中心值）
            # 注意：z_b不需要边界条件，直接外推
            z_b_ext = np.zeros(n + 2)
            z_b_ext[1:n+1] = self.z_b
            # 左ghost: 外推（假设坡度连续）
            z_b_ext[0] = self.z_b[0] - (self.z_b[1] - self.z_b[0]) if n > 1 else self.z_b[0]
            # 右ghost: 外推
            z_b_ext[n+1] = self.z_b[n-1] + (self.z_b[n-1] - self.z_b[n-2]) if n > 1 else self.z_b[n-1]

            # 界面底高程：取左右单元的最大值（保守）
            z_b_interface = np.maximum(z_b_ext[:-1], z_b_ext[1:])

            # 应用hydrostatic reconstruction
            h_L = np.maximum(0.0, eta_L - z_b_interface)
            h_R = np.maximum(0.0, eta_R - z_b_interface)

            # 重构流量（不变）
            if self.order == 2:
                Q_L, Q_R = self._muscl_reconstruction(Q_ext)
            else:
                Q_L = Q_ext[:-1]
                Q_R = Q_ext[1:]
        else:
            # 标准格式：直接重构h和Q
            # 使用Numba加速版本（如果启用且只支持HLL求解器）
            if self.use_numba and self.riemann_solver == 'hll':
                # 🚀 Numba加速路径
                if self.order == 2:
                    h_L, h_R = muscl_reconstruction_numba(h_ext)
                    Q_L, Q_R = muscl_reconstruction_numba(Q_ext)
                else:
                    h_L = h_ext[:-1]
                    h_R = h_ext[1:]
                    Q_L = Q_ext[:-1]
                    Q_R = Q_ext[1:]

                # 计算所有通量（Numba版本）
                F_h, F_Q = compute_all_fluxes_numba(
                    h_L, h_R, Q_L, Q_R, self.B, self.g, self.eps_dry
                )

                # 计算空间导数+源项（Numba版本）
                dh_dt, dQ_dt = compute_spatial_derivatives_numba(
                    F_h, F_Q, self.S0, h, Q, self.B, self.g, self.n, self.eps_dry, self.dx
                )

                # 注释掉边界通量强制 - 让Riemann求解器基于ghost cells计算
                # self._enforce_boundary_fluxes(F_h, F_Q, h, Q)
                # dh_dt[0] = -(F_h[1] - F_h[0]) / self.dx
                # dQ_dt[0] = -(F_Q[1] - F_Q[0]) / self.dx + self._compute_source_term(h[0], Q[0], 0)
                # n = len(h)
                # dh_dt[n-1] = -(F_h[n] - F_h[n-1]) / self.dx
                # dQ_dt[n-1] = -(F_Q[n] - F_Q[n-1]) / self.dx + self._compute_source_term(h[n-1], Q[n-1], n-1)

                return dh_dt, dQ_dt
            else:
                # 标准Python版本
                if self.order == 2:
                    h_L, h_R = self._muscl_reconstruction(h_ext)
                    Q_L, Q_R = self._muscl_reconstruction(Q_ext)
                else:
                    h_L = h_ext[:-1]
                    h_R = h_ext[1:]
                    Q_L = Q_ext[:-1]
                    Q_R = Q_ext[1:]

        # 计算所有界面通量（Python版本）
        F_h = np.zeros(n + 1)
        F_Q = np.zeros(n + 1)

        # DEBUG: Print interface states for Lake at Rest diagnosis
        DEBUG = False  # Set to True to enable diagnostics
        if DEBUG and self.well_balanced and self.t < 1e-6:  # Only at t=0
            print(f"\n[DEBUG] Interface states at t={self.t:.2e}:")
            print(f"  h_L: {h_L}")
            print(f"  h_R: {h_R}")
            print(f"  Q_L: {Q_L}")
            print(f"  Q_R: {Q_R}")

        for i in range(n + 1):
            # 界面i位于单元i-1和单元i之间
            # 计算通量（h_L, h_R已经通过hydrostatic reconstruction调整）
            if self.riemann_solver == 'hllc':
                F_h[i], F_Q[i] = self._hllc_flux(
                    h_L[i], Q_L[i], h_R[i], Q_R[i]
                )
            else:  # hll
                F_h[i], F_Q[i] = self._hll_flux(
                    h_L[i], Q_L[i], h_R[i], Q_R[i]
                )

        # 注释掉边界通量强制 - 让Riemann求解器基于ghost cells计算
        # self._enforce_boundary_fluxes(F_h, F_Q, h, Q)

        # DEBUG: Print computed fluxes
        if DEBUG and self.well_balanced and self.t < 1e-6:
            print(f"[DEBUG] Computed fluxes:")
            print(f"  F_h: {F_h}")
            print(f"  F_Q: {F_Q}")

        # 如果使用界面法源项，预计算z_b界面值
        z_b_interface_for_source = None
        if self.source_term_method == 'interface' and not self.well_balanced:
            z_b_ext = np.zeros(n + 2)
            z_b_ext[1:n+1] = self.z_b
            # 左ghost: 外推（假设坡度连续）
            z_b_ext[0] = self.z_b[0] - (self.z_b[1] - self.z_b[0]) if n > 1 else self.z_b[0]
            # 右ghost: 外推
            z_b_ext[n+1] = self.z_b[n-1] + (self.z_b[n-1] - self.z_b[n-2]) if n > 1 else self.z_b[n-1]
            # 界面底高程：平均值
            z_b_interface_for_source = 0.5 * (z_b_ext[:-1] + z_b_ext[1:])

        # 计算每个单元的空间导数（Python版本）
        for i in range(n):
            # 单元i的通量差
            dh_dt[i] = -(F_h[i+1] - F_h[i]) / self.dx
            dQ_dt[i] = -(F_Q[i+1] - F_Q[i]) / self.dx

            # Well-balanced几何源项修正（Audusse et al. 2004）
            if self.well_balanced:
                # 关键：hydrostatic reconstruction调整了h*，但通量中缺少了
                # 从z_b到z_interface之间的压力贡献，需要作为源项补偿
                #
                # 几何源项需要考虑界面处的调整后水深
                # 使用界面处的平均h*来计算

                # 左界面处的调整后水深（平均）
                h_star_left = 0.5 * (h_L[i] + h_R[i])
                # 右界面处的调整后水深（平均）
                h_star_right = 0.5 * (h_L[i+1] + h_R[i+1])

                # 计算两侧界面处的底高程差异
                dz_interface = z_b_interface[i+1] - z_b_interface[i]

                # 几何源项（使用界面处的平均h*）
                h_star_avg = 0.5 * (h_star_left + h_star_right)
                S_geo = -self.g * h_star_avg * self.B * dz_interface / self.dx
                dQ_dt[i] += S_geo

            # 界面法源项（Zhou's Surface Gradient Method启发）
            # 当source_term_method='interface'时，底坡源项从界面值计算
            if self.source_term_method == 'interface' and not self.well_balanced:
                # 从界面计算底坡源项（Zhou方法）
                # S_bed = -g * h * B * ∂z_b/∂x
                # 离散: S_bed = -g * h * B * (z_b[i+1/2] - z_b[i-1/2]) / dx
                dz = z_b_interface_for_source[i+1] - z_b_interface_for_source[i]
                h_for_source = h[i]  # 使用单元中心水深
                S_bed_interface = -self.g * h_for_source * self.B * dz / self.dx

                # 摩阻源项仍用点值法
                S_friction = self._compute_friction_source_term(h[i], Q[i], i)

                # 总源项
                dQ_dt[i] += S_bed_interface + S_friction

            # 标准法源项（点值法）
            elif self.source_term_method == 'standard' and not self.well_balanced:
                dQ_dt[i] += self._compute_source_term(h[i], Q[i], i)

            # Well-balanced模式下，摩阻源项单独添加
            elif self.well_balanced:
                dQ_dt[i] += self._compute_source_term(h[i], Q[i], i)

        return dh_dt, dQ_dt
    
    def _muscl_reconstruction(self, phi: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        MUSCL重构（二阶精度+TVD）
        
        从单元平均值phi_i重构界面左右值phi_{i-1/2}^R 和 phi_{i+1/2}^L
        
        Args:
            phi: 扩展变量数组 [n+2] (包含ghost cells)
        
        Returns:
            phi_L: 所有界面的左值 [n+1]
            phi_R: 所有界面的右值 [n+1]
        """
        n = len(phi) - 2  # 内部单元数
        
        phi_L = np.zeros(n + 1)
        phi_R = np.zeros(n + 1)
        
        # Minmod斜率限制器
        def minmod(a, b):
            if a * b <= 0:
                return 0.0
            elif abs(a) < abs(b):
                return a
            else:
                return b
        
        for i in range(n + 1):
            # 界面i位于单元i-1和i之间
            # 左单元: i-1+1 = i (扩展数组索引)
            # 右单元: i+1 (扩展数组索引)
            
            # 左单元i的重构（右界面值）
            if i > 0:
                slope_L = minmod(
                    phi[i+1] - phi[i],
                    phi[i] - phi[i-1]
                )
                phi_L[i] = phi[i] + 0.5 * slope_L
            else:
                phi_L[i] = phi[i]
            
            # 右单元i+1的重构（左界面值）
            if i < n:
                slope_R = minmod(
                    phi[i+2] - phi[i+1],
                    phi[i+1] - phi[i]
                )
                phi_R[i] = phi[i+1] - 0.5 * slope_R
            else:
                phi_R[i] = phi[i+1]
        
        return phi_L, phi_R

    def _hydrostatic_reconstruction(
        self,
        h_L: float,
        h_R: float,
        z_b_L: float,
        z_b_R: float
    ) -> Tuple[float, float]:
        """
        Hydrostatic Reconstruction (Audusse et al. 2004)

        核心思想：重构水面高程η=h+z_b而不是水深h
        确保水静止时(Q=0, ∂η/∂x=0)通量为0

        方法：
        1. 定义界面底高程 z*= max(z_b_L, z_b_R)
        2. 调整水深：h*_L = max(0, η_L - z*), h*_R = max(0, η_R - z*)
        3. 使用h*计算通量

        Args:
            h_L: 左侧水深
            h_R: 右侧水深
            z_b_L: 左侧底高程
            z_b_R: 右侧底高程

        Returns:
            h*_L, h*_R: 调整后的水深
        """
        # 计算水面高程
        eta_L = h_L + z_b_L
        eta_R = h_R + z_b_R

        # 界面底高程取max（保守处理）
        z_interface = max(z_b_L, z_b_R)

        # 调整水深（确保非负）
        h_star_L = max(0.0, eta_L - z_interface)
        h_star_R = max(0.0, eta_R - z_interface)

        return h_star_L, h_star_R

    def _hllc_flux(
        self,
        h_L: float,
        Q_L: float,
        h_R: float,
        Q_R: float
    ) -> Tuple[float, float]:
        """
        HLLC Riemann求解器（界面通量）

        HLLC = HLL with Contact wave
        相比HLL，能分辨接触间断，提高激波捕捉精度

        参考: Toro (2009) "Riemann Solvers", Chapter 10
        """
        # 干床检测
        if h_L < self.eps_dry and h_R < self.eps_dry:
            return 0.0, 0.0

        # 均匀流检测（特殊情况，直接返回）
        if abs(h_L - h_R) < 1e-10 and abs(Q_L - Q_R) < 1e-10:
            # 均匀流：F_h = Q, F_Q = Q²/A + P
            A = max(h_L, self.eps_dry) * self.B
            F_h = Q_L
            F_Q = Q_L**2 / A + 0.5 * self.g * h_L**2 * self.B
            return F_h, F_Q

        # 左状态
        h_L = max(h_L, self.eps_dry)
        A_L = h_L * self.B
        u_L = Q_L / A_L
        c_L = np.sqrt(self.g * h_L)
        P_L = 0.5 * self.g * h_L * h_L * self.B  # 压力项

        # 右状态
        h_R = max(h_R, self.eps_dry)
        A_R = h_R * self.B
        u_R = Q_R / A_R
        c_R = np.sqrt(self.g * h_R)
        P_R = 0.5 * self.g * h_R * h_R * self.B

        # 波速估计（Davis估计）
        S_L = min(u_L - c_L, u_R - c_R)
        S_R = max(u_L + c_L, u_R + c_R)

        # 通量（左右）
        F_h_L = Q_L
        F_Q_L = Q_L**2 / A_L + P_L

        F_h_R = Q_R
        F_Q_R = Q_R**2 / A_R + P_R

        # 守恒变量
        U_h_L = h_L
        U_Q_L = Q_L
        U_h_R = h_R
        U_Q_R = Q_R

        # HLLC通量选择
        if S_L >= 0:
            # 区域L（超音速向右）
            return F_h_L, F_Q_L
        elif S_R <= 0:
            # 区域R（超音速向左）
            return F_h_R, F_Q_R
        else:
            # 跨音速：计算接触波速度S*
            # S* = (P_R - P_L + Q_L*(S_L - u_L) - Q_R*(S_R - u_R)) / (h_L*(S_L - u_L) - h_R*(S_R - u_R))
            numerator = P_R - P_L + Q_L * (S_L - u_L) - Q_R * (S_R - u_R)
            denominator = h_L * (S_L - u_L) - h_R * (S_R - u_R)

            if abs(denominator) < 1e-10:
                # 退化为HLL
                F_h = (S_R * F_h_L - S_L * F_h_R + S_L * S_R * (U_h_R - U_h_L)) / (S_R - S_L)
                F_Q = (S_R * F_Q_L - S_L * F_Q_R + S_L * S_R * (U_Q_R - U_Q_L)) / (S_R - S_L)
                return F_h, F_Q

            S_star = numerator / denominator

            if S_star >= 0:
                # 区域L*（左侧中间状态）
                # U*_L = [(S_L - u_L)/(S_L - S*)] * [h_L, Q_L + (S* - u_L)*h_L]
                factor = (S_L - u_L) / (S_L - S_star)
                U_h_star = factor * h_L
                U_Q_star = factor * (Q_L + (S_star - u_L) * h_L)

                # F*_L = F_L + S_L*(U*_L - U_L)
                F_h = F_h_L + S_L * (U_h_star - U_h_L)
                F_Q = F_Q_L + S_L * (U_Q_star - U_Q_L)
                return F_h, F_Q
            else:
                # 区域R*（右侧中间状态）
                factor = (S_R - u_R) / (S_R - S_star)
                U_h_star = factor * h_R
                U_Q_star = factor * (Q_R + (S_star - u_R) * h_R)

                # F*_R = F_R + S_R*(U*_R - U_R)
                F_h = F_h_R + S_R * (U_h_star - U_h_R)
                F_Q = F_Q_R + S_R * (U_Q_star - U_Q_R)
                return F_h, F_Q

    def _hll_flux(
        self,
        h_L: float,
        Q_L: float,
        h_R: float,
        Q_R: float
    ) -> Tuple[float, float]:
        """
        HLL Riemann求解器（界面通量）

        保证：
        1. 守恒性
        2. 熵条件
        3. 干床稳定性
        """
        # 干床检测
        if h_L < self.eps_dry and h_R < self.eps_dry:
            return 0.0, 0.0

        # 左状态
        A_L = max(h_L * self.B, self.eps_dry * self.B)
        u_L = Q_L / A_L
        c_L = np.sqrt(self.g * max(h_L, 0.0))

        # 右状态
        A_R = max(h_R * self.B, self.eps_dry * self.B)
        u_R = Q_R / A_R
        c_R = np.sqrt(self.g * max(h_R, 0.0))

        # 波速估计（Davis估计）
        S_L = min(u_L - c_L, u_R - c_R)
        S_R = max(u_L + c_L, u_R + c_R)

        # 通量（左右）
        F_h_L = Q_L
        F_Q_L = Q_L**2 / A_L + 0.5 * self.g * h_L**2 * self.B

        F_h_R = Q_R
        F_Q_R = Q_R**2 / A_R + 0.5 * self.g * h_R**2 * self.B

        # HLL通量
        if S_L >= 0:
            # 超音速向右
            return F_h_L, F_Q_L
        elif S_R <= 0:
            # 超音速向左
            return F_h_R, F_Q_R
        else:
            # 跨音速（HLL平均）
            U_h_L = h_L
            U_h_R = h_R
            U_Q_L = Q_L
            U_Q_R = Q_R

            F_h = (S_R * F_h_L - S_L * F_h_R + S_L * S_R * (U_h_R - U_h_L)) / (S_R - S_L)
            F_Q = (S_R * F_Q_L - S_L * F_Q_R + S_L * S_R * (U_Q_R - U_Q_L)) / (S_R - S_L)

            return F_h, F_Q
    
    def _compute_friction_source_term(self, h: float, Q: float, cell_idx: int) -> float:
        """
        仅计算摩阻源项（用于interface方法）

        Args:
            h: 水深 (m)
            Q: 流量 (m³/s)
            cell_idx: 单元索引

        Returns:
            摩阻源项值
        """
        A = max(h * self.B, self.eps_dry * self.B)
        P = self.B + 2.0 * h
        R = A / P if P > 1e-10 else 0.0

        # 摩阻坡度
        if R > 1e-10 and abs(Q) > 1e-6:
            Sf = self.n**2 * Q**2 / (A**2 * R**(4.0/3.0))
            Sf = np.sign(Q) * Sf
        else:
            Sf = 0.0

        # 返回摩阻源项
        return -self.g * A * Sf

    def _compute_source_term(self, h: float, Q: float, cell_idx: int) -> float:
        """
        源项（重力+摩阻）

        标准格式：S_Q = g*A*(S0 - Sf)
        Well-balanced格式：S_Q = -g*A*Sf （底坡项已在通量中处理）

        Args:
            h: 水深 (m)
            Q: 流量 (m³/s)
            cell_idx: 单元索引

        Returns:
            源项值
        """
        A = max(h * self.B, self.eps_dry * self.B)
        P = self.B + 2.0 * h
        R = A / P if P > 1e-10 else 0.0

        # 摩阻坡度
        if R > 1e-10 and abs(Q) > 1e-6:
            Sf = self.n**2 * Q**2 / (A**2 * R**(4.0/3.0))
            Sf = np.sign(Q) * Sf
        else:
            Sf = 0.0

        # Well-balanced格式：底坡源项已通过hydrostatic reconstruction处理
        # 只需要添加摩阻项
        if self.well_balanced:
            return -self.g * A * Sf
        else:
            # 标准格式：包含底坡和摩阻
            return self.g * A * (self.S0[cell_idx] - Sf)
    
    def _extend_with_ghosts(
        self,
        h: np.ndarray,
        Q: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """扩展数组（ghost cells）"""
        n = len(h)
        h_ext = np.zeros(n + 2)
        Q_ext = np.zeros(n + 2)

        # 内部
        h_ext[1:n+1] = h
        Q_ext[1:n+1] = Q

        # 左ghost（外推）
        if self.bc_left['type'] == 'h':
            value = self.bc_left['value']
            h_ext[0] = value if not callable(value) else value(self.t)
            Q_ext[0] = Q[0]  # 外推
        elif self.bc_left['type'] == 'Q':
            h_ext[0] = h[0]
            value = self.bc_left['value']
            Q_ext[0] = value if not callable(value) else value(self.t)
        elif self.bc_left['type'] == 'critical':
            # 临界流边界条件：仅指定h_c，Q通过内部值外推
            if self.bc_right['type'] == 'Q':
                # 使用对侧固定Q边界值计算临界水深
                Q_boundary = self.bc_right['value'] if not callable(self.bc_right['value']) else self.bc_right['value'](self.t)
            else:
                # 使用内部流量估算
                Q_boundary = np.mean(Q[:min(10, n)])
            h_c, u_c = self.characteristic_bc.apply_critical_depth_bc(Q=Q_boundary, B=self.B)
            # 只设置h，Q从内部外推
            h_ext[0] = h_c
            Q_ext[0] = Q[0]  # 外推流量
        elif self.bc_left['type'] == 'supercritical':
            # 急流入口：同时指定h和Q
            h_bc_value = self.bc_left['h']
            Q_bc_value = self.bc_left['Q']
            h_bc, u_bc = self.characteristic_bc.apply_supercritical_inlet(
                h_bc_value=h_bc_value, Q_bc_value=Q_bc_value, B=self.B
            )
            h_ext[0] = h_bc
            Q_ext[0] = Q_bc_value

        # 右ghost
        if self.bc_right['type'] == 'h':
            value = self.bc_right['value']
            h_ext[n+1] = value if not callable(value) else value(self.t)
            Q_ext[n+1] = Q[n-1]
        elif self.bc_right['type'] == 'Q':
            h_ext[n+1] = h[n-1]
            value = self.bc_right['value']
            Q_ext[n+1] = value if not callable(value) else value(self.t)
        elif self.bc_right['type'] == 'critical':
            # 临界流边界条件：仅指定h_c，Q通过内部值外推
            if self.bc_left['type'] == 'Q':
                # 使用对侧固定Q边界值计算临界水深
                Q_boundary = self.bc_left['value'] if not callable(self.bc_left['value']) else self.bc_left['value'](self.t)
            else:
                # 使用内部流量估算
                Q_boundary = np.mean(Q[-min(10, n):])
            h_c, u_c = self.characteristic_bc.apply_critical_depth_bc(Q=Q_boundary, B=self.B)
            # 只设置h，Q从内部外推（避免over-constrain）
            h_ext[n+1] = h_c
            Q_ext[n+1] = Q[n-1]  # 外推流量
        elif self.bc_right['type'] == 'supercritical':
            # 急流出口：完全外推（所有特征线向外）
            h_bc, u_bc = self.characteristic_bc.apply_supercritical_outlet(
                h_interior=h[n-1], u_interior=Q[n-1]/(h[n-1]*self.B) if h[n-1] > self.eps_dry else 0.0
            )
            h_ext[n+1] = h_bc
            Q_ext[n+1] = u_bc * h_bc * self.B

        return h_ext, Q_ext
    
    def _apply_bc(
        self,
        h: np.ndarray,
        Q: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        强制边界条件

        注意：对于使用强制通量的边界类型（supercritical），我们不强制边界单元的值，
        而是让它们根据通量平衡自然演化。这避免了通量与状态不一致导致的质量泄漏。
        """
        # 左
        if self.bc_left['type'] == 'h':
            value = self.bc_left['value']
            h[0] = value if not callable(value) else value(self.t)
        elif self.bc_left['type'] == 'Q':
            value = self.bc_left['value']
            Q[0] = value if not callable(value) else value(self.t)
        elif self.bc_left['type'] == 'critical':
            # 临界流边界条件：仅指定h_c，不强制Q
            if self.bc_right['type'] == 'Q':
                Q_boundary = self.bc_right['value'] if not callable(self.bc_right['value']) else self.bc_right['value'](self.t)
            else:
                Q_boundary = np.mean(Q[:min(10, len(Q))])
            h_c, u_c = self.characteristic_bc.apply_critical_depth_bc(Q=Q_boundary, B=self.B)
            # 只强制h，不强制Q
            h[0] = h_c
        elif self.bc_left['type'] == 'supercritical':
            # 急流入口：强制h和Q（所有特征线向内）
            h_bc_value = self.bc_left['h']
            Q_bc_value = self.bc_left['Q']
            h_bc, u_bc = self.characteristic_bc.apply_supercritical_inlet(
                h_bc_value=h_bc_value, Q_bc_value=Q_bc_value, B=self.B
            )
            h[0] = h_bc
            Q[0] = Q_bc_value

        # 右
        if self.bc_right['type'] == 'h':
            value = self.bc_right['value']
            h[-1] = value if not callable(value) else value(self.t)
        elif self.bc_right['type'] == 'Q':
            value = self.bc_right['value']
            Q[-1] = value if not callable(value) else value(self.t)
        elif self.bc_right['type'] == 'critical':
            # 临界流边界条件：仅指定h_c，不强制Q
            if self.bc_left['type'] == 'Q':
                Q_boundary = self.bc_left['value'] if not callable(self.bc_left['value']) else self.bc_left['value'](self.t)
            else:
                Q_boundary = np.mean(Q[-min(10, len(Q)):])
            h_c, u_c = self.characteristic_bc.apply_critical_depth_bc(Q=Q_boundary, B=self.B)
            # 只强制h，不强制Q（让流量自然调整）
            h[-1] = h_c
        elif self.bc_right['type'] == 'supercritical':
            # 急流出口：完全外推（所有特征线向外）
            h_bc, u_bc = self.characteristic_bc.apply_supercritical_outlet(
                h_interior=h[-2] if len(h) > 1 else h[-1],
                u_interior=Q[-2]/(h[-2]*self.B) if len(h) > 1 and h[-2] > self.eps_dry else 0.0
            )
            h[-1] = h_bc
            Q[-1] = u_bc * h_bc * self.B

        return h, Q

    def _enforce_boundary_fluxes(
        self,
        F_h: np.ndarray,
        F_Q: np.ndarray,
        h: np.ndarray,
        Q: np.ndarray
    ):
        """
        强制边界通量与边界条件一致

        关键思路：边界通量应该由边界条件决定，而不是由Riemann求解器计算。
        这解决了边界单元与相邻单元通量不一致导致的质量守恒问题。

        Args:
            F_h: 质量通量数组 [n+1]（会被修改）
            F_Q: 动量通量数组 [n+1]（会被修改）
            h: 当前水深数组 [n]
            Q: 当前流量数组 [n]
        """
        n = len(h)

        # 左边界通量（界面0，位于ghost cell和单元0之间）
        if self.bc_left['type'] == 'Q':
            # Q边界：流量固定
            Q_bc = self.bc_left['value'] if not callable(self.bc_left['value']) else self.bc_left['value'](self.t)
            h_bc = h[0]  # 水深从内部单元获取

            # 计算通量
            if h_bc > self.eps_dry:
                u_bc = Q_bc / (self.B * h_bc)
                F_h[0] = Q_bc
                F_Q[0] = Q_bc * u_bc + 0.5 * self.g * h_bc * h_bc * self.B
            else:
                F_h[0] = 0.0
                F_Q[0] = 0.0

        elif self.bc_left['type'] == 'h':
            # h边界：水深固定，流量从内部外推
            h_bc = self.bc_left['value'] if not callable(self.bc_left['value']) else self.bc_left['value'](self.t)
            Q_bc = Q[0]  # 流量从内部单元外推

            if h_bc > self.eps_dry:
                u_bc = Q_bc / (self.B * h_bc)
                F_h[0] = Q_bc
                F_Q[0] = Q_bc * u_bc + 0.5 * self.g * h_bc * h_bc * self.B
            else:
                F_h[0] = 0.0
                F_Q[0] = 0.0

        elif self.bc_left['type'] == 'supercritical':
            # 急流边界：h和Q都固定（所有特征线向内）
            h_bc = self.bc_left['h']
            Q_bc = self.bc_left['Q']

            if h_bc > self.eps_dry:
                u_bc = Q_bc / (self.B * h_bc)
                F_h[0] = Q_bc
                F_Q[0] = Q_bc * u_bc + 0.5 * self.g * h_bc * h_bc * self.B
            else:
                F_h[0] = 0.0
                F_Q[0] = 0.0

        elif self.bc_left['type'] == 'critical':
            # 临界流边界：根据流量计算临界水深
            if self.bc_right['type'] == 'Q':
                Q_bc = self.bc_right['value'] if not callable(self.bc_right['value']) else self.bc_right['value'](self.t)
            else:
                Q_bc = Q[0]

            h_c, u_c = self.characteristic_bc.apply_critical_depth_bc(Q=Q_bc, B=self.B)

            if h_c > self.eps_dry:
                F_h[0] = Q_bc
                F_Q[0] = Q_bc * u_c + 0.5 * self.g * h_c * h_c * self.B
            else:
                F_h[0] = 0.0
                F_Q[0] = 0.0

        # 右边界通量（界面n，位于单元n-1和ghost cell之间）
        if self.bc_right['type'] == 'Q':
            # Q边界：流量固定
            Q_bc = self.bc_right['value'] if not callable(self.bc_right['value']) else self.bc_right['value'](self.t)
            h_bc = h[n-1]

            if h_bc > self.eps_dry:
                u_bc = Q_bc / (self.B * h_bc)
                F_h[n] = Q_bc
                F_Q[n] = Q_bc * u_bc + 0.5 * self.g * h_bc * h_bc * self.B
            else:
                F_h[n] = 0.0
                F_Q[n] = 0.0

        elif self.bc_right['type'] == 'h':
            # h边界：水深固定，流量外推
            h_bc = self.bc_right['value'] if not callable(self.bc_right['value']) else self.bc_right['value'](self.t)
            Q_bc = Q[n-1]

            if h_bc > self.eps_dry:
                u_bc = Q_bc / (self.B * h_bc)
                F_h[n] = Q_bc
                F_Q[n] = Q_bc * u_bc + 0.5 * self.g * h_bc * h_bc * self.B
            else:
                F_h[n] = 0.0
                F_Q[n] = 0.0

        elif self.bc_right['type'] == 'supercritical':
            # 急流出口：完全外推（所有特征线向外）
            h_bc = h[n-1]
            Q_bc = Q[n-1]

            if h_bc > self.eps_dry:
                u_bc = Q_bc / (self.B * h_bc)
                F_h[n] = Q_bc
                F_Q[n] = Q_bc * u_bc + 0.5 * self.g * h_bc * h_bc * self.B
            else:
                F_h[n] = 0.0
                F_Q[n] = 0.0

        elif self.bc_right['type'] == 'critical':
            # 临界流边界
            if self.bc_left['type'] == 'Q':
                Q_bc = self.bc_left['value'] if not callable(self.bc_left['value']) else self.bc_left['value'](self.t)
            else:
                Q_bc = Q[n-1]

            h_c, u_c = self.characteristic_bc.apply_critical_depth_bc(Q=Q_bc, B=self.B)

            if h_c > self.eps_dry:
                F_h[n] = Q_bc
                F_Q[n] = Q_bc * u_c + 0.5 * self.g * h_c * h_c * self.B
            else:
                F_h[n] = 0.0
                F_Q[n] = 0.0

    def _compute_total_mass(self, exclude_boundary_cells=False) -> float:
        """
        计算总质量

        Args:
            exclude_boundary_cells: 是否排除边界单元
                - True: 只计算内部单元质量（适用于强制边界）
                - False: 计算所有单元质量（默认）
        """
        if exclude_boundary_cells:
            # 判断哪些边界被强制
            exclude_left = self.bc_left['type'] in ['supercritical', 'h', 'Q', 'critical']
            exclude_right = self.bc_right['type'] in ['supercritical', 'h', 'Q', 'critical']

            # 确定计算域范围
            start_idx = 1 if exclude_left else 0
            end_idx = len(self.h) - 1 if exclude_right else len(self.h)

            # 只计算内部单元
            return np.sum(self.h[start_idx:end_idx] * self.B * self.dx)
        else:
            # 计算所有单元
            return np.sum(self.h * self.B * self.dx)
    
    def get_mass_conservation_error(self, exclude_boundary_cells=False) -> float:
        """
        质量守恒误差 (%)

        Args:
            exclude_boundary_cells: 是否排除边界单元（默认False）
                - True: 只检查内部计算域的质量守恒
                - False: 检查包括边界在内的所有单元
        """
        current_mass = self._compute_total_mass(exclude_boundary_cells=exclude_boundary_cells)
        if self.initial_mass > 1e-10:
            return (current_mass - self.initial_mass) / self.initial_mass * 100.0
        return 0.0
    
    def get_state(self) -> Dict:
        """获取当前状态"""
        return {
            'x': self.x.copy(),
            'h': self.h.copy(),
            'Q': self.Q.copy(),
            't': self.t,
            'dt': self.dt,
            'step': self.step_count,
            'mass_error': self.get_mass_conservation_error()
        }


if __name__ == "__main__":
    print("="*80)
    print("Godunov-FVM求解器 - 快速测试")
    print("="*80)
    
    # 测试：静止水体
    print("\n测试1: 静止水体（质量守恒）")
    print("-"*80)
    
    solver = GodunvFVMSolver(
        width=10.0,
        length=1000.0,
        n_cells=50,
        manning_n=0.025,
        slope=0.001,
        cfl=0.5,
        order=2
    )
    
    h_init = np.ones(50) * 2.0
    Q_init = np.zeros(50)
    bc_left = {'type': 'h', 'value': 2.0}
    bc_right = {'type': 'h', 'value': 2.0}
    
    solver.initialize(h_init, Q_init, bc_left, bc_right)
    
    # 推进100步
    for _ in range(100):
        solver.step()
    
    state = solver.get_state()
    print(f"\n结果 (100步):")
    print(f"  质量误差: {state['mass_error']:.6f}%")
    print(f"  max|h-2.0|: {np.max(np.abs(state['h'] - 2.0)):.6e} m")
    print(f"  max|Q|: {np.max(np.abs(state['Q'])):.6e} m³/s")
    print(f"  目标<0.5%: {'✅' if abs(state['mass_error']) < 0.5 else '❌'}")
    
    print("\n" + "="*80)
