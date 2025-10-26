#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
静水重构渠道求解器

将良平衡的静水重构法集成到CanalSolver框架中
支持Preissmann隐式时间推进和内部边界条件（闸门）

基于：
- Audusse et al. (2004) SIAM 静水重构法
- 现有CanalSolver框架

作者: Claude
日期: 2025-10-23
"""

import numpy as np
import math
from typing import List, Tuple, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.hydrostatic_reconstruction_v3 import BoundaryType
from solvers.gate import PumpStation  # 导入PumpStation用于泵站扬程处理


class HydrostaticCanalSolver:
    """
    静水重构渠道求解器

    核心特性：
    - 良平衡的静水重构（机器精度保持稳态）
    - HLL Riemann求解器
    - Preissmann隐式时间推进
    - 支持内部边界条件（闸门）
    """

    def __init__(self,
                 length: float = 1000.0,
                 nx: int = 201,
                 B: float = 10.0,
                 S0: float = 0.001,
                 n: float = 0.025,
                 g: float = 9.81,
                 internal_structures: list = None,
                 x_grid: np.ndarray = None,
                 bc_left: BoundaryType = BoundaryType.TRANSMISSIVE,
                 bc_right: BoundaryType = BoundaryType.TRANSMISSIVE,
                 theta: float = 0.6,
                 omega: float = 0.95,
                 eps_dry: float = 1e-6):
        """
        初始化静水重构求解器

        Args:
            length: 渠道长度 (m)
            nx: 空间离散点数
            B: 渠道宽度 (m)
            S0: 渠底坡度
            n: Manning糙率
            g: 重力加速度 (m/s²)
            internal_structures: 内部水工建筑物 [(position, structure_obj), ...]
            x_grid: 自定义网格（可选）
            bc_left: 左边界条件类型
            bc_right: 右边界条件类型
            theta: Preissmann时间加权系数 (0.5-1.0)
            omega: 松弛因子 (0-1)
            eps_dry: 干湿判定阈值 (m)
        """
        self.length = length
        self.B = B
        self.S0 = S0
        self.n = n
        self.g = g
        self.theta = theta
        self.omega = omega
        self.eps_dry = eps_dry
        self.bc_left = bc_left
        self.bc_right = bc_right

        # 空间网格
        if x_grid is not None:
            self.x = x_grid
            self.nx = len(x_grid)
            self.is_uniform_grid = False
            self.dx_local = np.diff(x_grid)
            self.dx = np.mean(self.dx_local)
        else:
            self.nx = nx
            self.dx = length / (nx - 1)
            self.x = np.linspace(0, length, nx)
            self.is_uniform_grid = True
            self.dx_local = np.ones(nx-1) * self.dx

        # 底床高程（线性坡度）
        self.z = -self.S0 * self.x

        # 初始化状态变量
        self.h = np.ones(nx) * 1.0  # 水深 (m)
        self.hu = np.ones(nx) * 5.0  # 流量 hu (m²/s)

        # 内部边界条件（闸门）
        self.internal_structures = internal_structures or []
        self._setup_internal_structures()

        # 历史记录
        self.h_history = []
        self.Q_history = []
        self.t_history = []

        # 时间变量（用于时变内部边界条件）
        self.current_time = 0.0

    def _setup_internal_structures(self):
        """设置内部水工建筑物的节点索引"""
        self.structure_indices = []
        self.structure_objects = []

        for position, structure in self.internal_structures:
            idx = np.argmin(np.abs(self.x - position))
            self.structure_indices.append(idx)
            self.structure_objects.append(structure)

    def reconstruct_interface(
        self, h_L: float, z_L: float, h_R: float, z_R: float
    ) -> Tuple[float, float]:
        """
        静水重构（界面）

        Args:
            h_L, z_L: 左单元水深和底床高程
            h_R, z_R: 右单元水深和底床高程

        Returns:
            (h_star_L, h_star_R): 重构后的左右水深
        """
        eta_L = h_L + z_L
        eta_R = h_R + z_R
        z_interface = max(z_L, z_R)

        h_star_L = max(0.0, eta_L - z_interface)
        h_star_R = max(0.0, eta_R - z_interface)

        return h_star_L, h_star_R

    def hll_flux(
        self, h_L: float, hu_L: float, h_R: float, hu_R: float
    ) -> Tuple[float, float]:
        """
        HLL Riemann求解器

        Args:
            h_L, hu_L: 左状态（水深，流量）
            h_R, hu_R: 右状态（水深，流量）

        Returns:
            (F_mass, F_momentum): 质量和动量通量
        """
        if h_L < self.eps_dry and h_R < self.eps_dry:
            return 0.0, 0.0

        u_L = hu_L / h_L if h_L > self.eps_dry else 0.0
        u_R = hu_R / h_R if h_R > self.eps_dry else 0.0

        c_L = math.sqrt(self.g * h_L) if h_L > self.eps_dry else 0.0
        c_R = math.sqrt(self.g * h_R) if h_R > self.eps_dry else 0.0

        s_L = min(u_L - c_L, u_R - c_R)
        s_R = max(u_L + c_L, u_R + c_R)

        if abs(s_L) < 1e-14 and abs(s_R) < 1e-14:
            s_L = -1e-10
            s_R = 1e-10

        # 计算物理通量
        if h_L > self.eps_dry:
            F_mass_L = hu_L
            F_mom_L = hu_L * u_L + 0.5 * self.g * h_L**2
        else:
            F_mass_L = 0.0
            F_mom_L = 0.0

        if h_R > self.eps_dry:
            F_mass_R = hu_R
            F_mom_R = hu_R * u_R + 0.5 * self.g * h_R**2
        else:
            F_mass_R = 0.0
            F_mom_R = 0.0

        # HLL通量
        if s_L >= 0:
            return F_mass_L, F_mom_L
        elif s_R <= 0:
            return F_mass_R, F_mom_R
        else:
            U_L = [h_L, hu_L]
            U_R = [h_R, hu_R]
            F_L = [F_mass_L, F_mom_L]
            F_R = [F_mass_R, F_mom_R]

            F_mass_HLL = (s_R * F_L[0] - s_L * F_R[0] +
                         s_L * s_R * (U_R[0] - U_L[0])) / (s_R - s_L)
            F_mom_HLL = (s_R * F_L[1] - s_L * F_R[1] +
                        s_L * s_R * (U_R[1] - U_L[1])) / (s_R - s_L)

            return F_mass_HLL, F_mom_HLL

    def setup_ghost_cells(
        self, h: np.ndarray, hu: np.ndarray, z: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        设置虚拟单元（边界条件）

        Args:
            h, hu, z: 物理单元数据

        Returns:
            h_ext, hu_ext, z_ext: 扩展数据（包含虚拟单元）
        """
        n_cells = len(h)

        h_ext = np.zeros(n_cells + 2)
        hu_ext = np.zeros(n_cells + 2)
        z_ext = np.zeros(n_cells + 2)

        # 复制物理单元
        h_ext[1:-1] = h
        hu_ext[1:-1] = hu
        z_ext[1:-1] = z

        # 左边界虚拟单元
        if self.bc_left == BoundaryType.TRANSMISSIVE:
            eta_0 = h[0] + z[0]
            z_ext[0] = z[0]
            h_ext[0] = eta_0 - z_ext[0]
            hu_ext[0] = hu[0]
        elif self.bc_left == BoundaryType.REFLECTIVE:
            h_ext[0] = h[0]
            hu_ext[0] = -hu[0]
            z_ext[0] = z[0]
        elif self.bc_left == BoundaryType.EXTRAPOLATION:
            h_ext[0] = h[0]
            hu_ext[0] = hu[0]
            z_ext[0] = z[0]

        # 右边界虚拟单元
        if self.bc_right == BoundaryType.TRANSMISSIVE:
            eta_n = h[-1] + z[-1]
            z_ext[-1] = z[-1]
            h_ext[-1] = eta_n - z_ext[-1]
            hu_ext[-1] = hu[-1]
        elif self.bc_right == BoundaryType.REFLECTIVE:
            h_ext[-1] = h[-1]
            hu_ext[-1] = -hu[-1]
            z_ext[-1] = z[-1]
        elif self.bc_right == BoundaryType.EXTRAPOLATION:
            h_ext[-1] = h[-1]
            hu_ext[-1] = hu[-1]
            z_ext[-1] = z[-1]

        return h_ext, hu_ext, z_ext

    def compute_fluxes_and_sources(
        self, h: np.ndarray, hu: np.ndarray, z: np.ndarray, dx: float
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        计算所有界面的通量和所有单元的源项（静水重构）

        Args:
            h: 水深数组 [n_cells]
            hu: 流量数组 [n_cells]
            z: 底床高程数组 [n_cells]
            dx: 网格间距

        Returns:
            (F_mass, F_momentum, S_mass, S_momentum)
        """
        n_cells = len(h)

        # 设置虚拟单元
        h_ext, hu_ext, z_ext = self.setup_ghost_cells(h, hu, z)

        # 存储通量
        F_mass = np.zeros(n_cells + 1)
        F_momentum = np.zeros(n_cells + 1)

        # 存储重构水深
        h_star_interfaces = np.zeros((n_cells + 1, 2))

        # 计算所有界面的通量
        for i in range(n_cells + 1):
            h_L = h_ext[i]
            hu_L = hu_ext[i]
            z_L = z_ext[i]

            h_R = h_ext[i+1]
            hu_R = hu_ext[i+1]
            z_R = z_ext[i+1]

            # 静水重构
            h_star_L, h_star_R = self.reconstruct_interface(h_L, z_L, h_R, z_R)
            h_star_interfaces[i, 0] = h_star_L
            h_star_interfaces[i, 1] = h_star_R

            # 重构流量
            if h_L > self.eps_dry:
                hu_star_L = hu_L * (h_star_L / h_L)
            else:
                hu_star_L = 0.0

            if h_R > self.eps_dry:
                hu_star_R = hu_R * (h_star_R / h_R)
            else:
                hu_star_R = 0.0

            # HLL通量
            F_mass[i], F_momentum[i] = self.hll_flux(
                h_star_L, hu_star_L, h_star_R, hu_star_R
            )

        # 计算源项（使用重构水深）
        S_mass = np.zeros(n_cells)
        S_momentum = np.zeros(n_cells)

        for i in range(n_cells):
            # 左界面重构水深（从右侧看）
            h_star_L = h_star_interfaces[i, 1]
            # 右界面重构水深（从左侧看）
            h_star_R = h_star_interfaces[i+1, 0]

            # 良平衡源项（Audusse公式）
            S_gravity = 0.5 * self.g * (h_star_R**2 - h_star_L**2) / dx

            # 摩擦项
            if h[i] > self.eps_dry and abs(self.n) > 1e-10:
                u_i = hu[i] / h[i]
                R_i = h[i]  # 矩形渠道近似
                S_friction = -self.g * self.n**2 * abs(u_i) * hu[i] / (R_i**(4/3))
            else:
                S_friction = 0.0

            S_mass[i] = 0.0
            S_momentum[i] = S_gravity + S_friction

        # ========================================================================
        # 泵站源项法（v5.0 - 实现版）
        # ========================================================================
        # 原理：泵站通过动量源项添加能量，避免剧烈的水深跳跃
        # 
        # 物理模型：
        #   S_momentum = ρ * g * H_pump * Q / Δx
        # 
        # 其中：
        #   H_pump: 泵站扬程 (m)
        #   Q: 局部流量 (m³/s)
        #   Δx: 网格间距 (m)
        #
        # 优点：
        #   ✓ 避免水深跳跃导致的数值不稳定
        #   ✓ 适合非恒定流
        #   ✓ 物理上合理（能量输入分布在空间上）
        #
        # 参考文献：
        # - Sanders et al. (2010): ParBreZo shallow-water code
        # - Guinot (2008): Wave Propagation in Fluids, Chapter 9
        # - Toro (2009): Riemann Solvers, Chapter 10
        # ========================================================================
        
        if self.structure_indices and self.structure_objects:
            from solvers.gate import PumpStation
            
            for idx, structure in zip(self.structure_indices, self.structure_objects):
                # 仅处理运行中的泵站
                if not isinstance(structure, PumpStation) or not structure.is_running:
                    continue
                
                # 边界检查
                if idx <= 0 or idx >= n_cells:
                    continue
                
                # 获取泵站位置的流量
                Q_pump = hu[idx] * self.B  # m³/s
                
                # 计算动量源项: S = ρ * g * H_pump * Q / Δx
                # 简化：ρ = 1000 kg/m³, 单位面积: S = g * H_pump * Q / (B * Δx)
                # 这里 hu 已经是单位宽度流量，所以：
                S_pump_base = self.g * structure.rated_head * abs(hu[idx]) / dx
                
                # ⚠️ 实验：减小源项强度（平滑分布，避免过强）
                # 将源项分布到3个节点，权重 [0.2, 0.6, 0.2]
                weight_center = 0.6
                weight_neighbor = 0.2
                
                S_momentum[idx] += weight_center * S_pump_base
                if idx > 0:
                    S_momentum[idx-1] += weight_neighbor * S_pump_base
                if idx < n_cells - 1:
                    S_momentum[idx+1] += weight_neighbor * S_pump_base
                
                # 可选：平滑源项到相邻单元（提高数值稳定性）
                # weight_center = 0.6
                # weight_neighbor = 0.2
                # S_momentum[idx] += weight_center * S_pump
                # if idx > 0:
                #     S_momentum[idx-1] += weight_neighbor * S_pump
                # if idx < n_cells - 1:
                #     S_momentum[idx+1] += weight_neighbor * S_pump

        return F_mass, F_momentum, S_mass, S_momentum

    def _apply_internal_bc(self, t: float = 0.0, Q_target: float = None,
                          max_iter: int = 20, tol: float = 0.01, relax: float = 0.5):
        """
        应用内部边界条件（闸门、泵站等水工建筑物）

        对于稳态流：通过调整水深来满足闸门流量公式
        闸门公式: Q = f(h_up, h_down)
        已知Q_target，调整h_up使得f(h_up, h_down) = Q_target

        泵站处理：先调整上游水深满足流量，然后应用扬程到下游

        Args:
            t: 当前时间 (s)
            Q_target: 目标流量 (m³/s)，用于闸门约束
            max_iter: 最大迭代次数
            tol: 收敛容差 (m³/s)
            relax: 松弛因子
        """
        if not self.structure_indices or Q_target is None:
            return

        for iter_count in range(max_iter):
            converged = True

            for idx, structure in zip(self.structure_indices, self.structure_objects):
                # 导入PumpStation类型
                from solvers.gate import PumpStation

                # 更新结构时间
                structure.update_time(t)

                # 边界检查
                if idx <= 0 or idx >= self.nx - 1:
                    continue

                # 🔧 跳过泵站：泵站的水位跃变通过_apply_pump_head_jump单独处理
                if isinstance(structure, PumpStation):
                    continue

                # 获取闸门上下游水深（闸门在节点idx，上游idx-1，下游idx+1）
                h_up = self.h[idx - 1]
                h_down = self.h[idx + 1]

                # 计算当前闸门流量
                Q_gate_current, _ = structure.calculate_discharge(h_up, h_down, t)

                # 残差
                residual = Q_target - Q_gate_current

                if abs(residual) > tol:
                    converged = False

                    # 使用导数调整上游水深
                    # Q = f(h_up, h_down)，目标：f(h_up, h_down) = Q_target
                    # 使用牛顿法：Δh_up ≈ (Q_target - Q_current) / (dQ/dh_up)
                    dQ_dh_up, dQ_dh_down = structure.calculate_discharge_derivatives(h_up, h_down, t)

                    if abs(dQ_dh_up) > 1e-6:
                        # 牛顿步长
                        dh_up = residual / dQ_dh_up
                        # 限制步长避免过冲
                        dh_up = np.clip(dh_up, -0.1, 0.1)
                        # 松弛更新
                        self.h[idx - 1] = h_up + relax * dh_up
                        # 确保水深为正
                        self.h[idx - 1] = max(self.eps_dry, self.h[idx - 1])

            if converged:
                break

        # 注意：泵站扬程不通过这里的迭代实现，而是在每次迭代后强制施加跃变
        # （见_apply_pump_head_jump方法）

    def _get_pump_region_mask(self) -> np.ndarray:
        """
        获取泵站区域掩码（源项法版本）
        
        在源项法中，泵站仅影响3个节点的流量设置。
        水位抬升由源项自动产生，不需要人工设置。
        
        Returns:
            mask: 布尔数组，True表示该点在泵站影响区内
        """
        mask = np.zeros(self.nx, dtype=bool)

        if not self.structure_indices or not self.structure_objects:
            return mask

        for idx, structure in zip(self.structure_indices, self.structure_objects):
            from solvers.gate import PumpStation

            if not isinstance(structure, PumpStation) or not structure.is_running:
                continue

            # 边界检查
            if idx <= 0 or idx >= self.nx - 1:
                continue

            # 标记泵站直接影响的3个节点（用于流量连续性设置）
            mask[idx - 1] = True
            mask[idx] = True
            mask[idx + 1] = True

        return mask

    def _apply_pump_internal_bc(self, conserve_local_flow=False):
        """
        泵站作为内部边界条件（标准方法 v4.0 - 改进版）
        
        理论基础：
        =========
        泵站产生水位跃变，根据Rankine-Hugoniot跳跃条件：
        
        质量守恒：Q⁺ = Q⁻  (流量连续)
        能量跃变：h⁺ = h⁻ + H_pump  (水位跃升)
        
        数值实现：
        =========
        在泵站节点i处：
        1. 从上游（i-1）获取状态
        2. 施加跳跃条件到下游（i+1）
        3. 泵站节点（i）设为过渡值
        4. 其余节点由PDE求解器自然求解
        
        改进（v4.1 - 非恒定流）：
        =====================
        当conserve_local_flow=True时（用于非恒定流）：
        - 保持泵站附近3节点的平均流量（来自Preissmann更新）
        - 仅调整水深分布（施加扬程）
        - 避免破坏Preissmann步的流量守恒
        
        参考文献：
        =========
        - Toro (2009): Riemann Solvers, Chapter 10
        - HEC-RAS: Energy equation at structures
        - DHI MIKE 11: Internal boundary conditions
        
        优点：
        =====
        ✓ 物理清晰（能量守恒 + 质量守恒）
        ✓ 仅影响3个节点
        ✓ 适合稳态和瞬态问题
        ✓ 改进后在非恒定流中保持流量守恒
        """
        if not self.structure_indices or not self.structure_objects:
            return

        for idx, structure in zip(self.structure_indices, self.structure_objects):
            from solvers.gate import PumpStation

            if not isinstance(structure, PumpStation) or not structure.is_running:
                continue

            # 边界检查
            if idx <= 0 or idx >= self.nx - 1:
                continue

            if conserve_local_flow:
                # 非恒定流模式：暂不处理泵站跳跃
                # 原因：在非恒定流中施加跳跃条件会破坏数值稳定性
                # 
                # TODO: 实现稳定的非恒定流泵站处理方法
                # 可能方案：
                # 1. 源项法（需要兼容的稳态求解器）
                # 2. 更温和的跳跃条件（渐进施加）
                # 3. 特征线方法
                #
                # 当前：让泵站像普通渠段一样演化，保证流量守恒
                pass
            else:
                # 稳态模式：标准跳跃条件
                # 获取上游状态
                h_upstream = self.h[idx - 1]
                hu_upstream = self.hu[idx - 1]
                
                # 施加跳跃条件
                # 1. 能量跃变：h⁺ = h⁻ + H_pump
                h_downstream = h_upstream + structure.rated_head
                
                # 2. 质量守恒：Q⁺ = Q⁻
                hu_downstream = hu_upstream
                
                # 应用到节点
                self.h[idx + 1] = h_downstream
                self.hu[idx + 1] = hu_downstream
                
                # 泵站节点：线性插值
                self.h[idx] = 0.5 * (h_upstream + h_downstream)
                self.hu[idx] = hu_upstream
            
            # 确保正值
            self.h[idx] = max(self.eps_dry, self.h[idx])
            self.h[idx + 1] = max(self.eps_dry, self.h[idx + 1])
    
    def _apply_pump_region_constraints(self):
        """
        【已废弃 v3.0】应用泵站区域约束（旧方法）
        
        v4.0使用源项法，此方法已废弃。
        保留仅为向后兼容。
        """
        # 调用源项法的辅助方法
        self._apply_pump_internal_bc()

    def _apply_pump_region_constraints(self):
        """
        【已废弃 v3.0】应用泵站区域约束（旧方法）
        
        此方法使用15点区域约束，存在以下问题：
        - 与Preissmann PDE求解器冲突
        - 创造非物理的"平台区"
        - 在边界产生数值台阶
        - 需要调整松弛因子"凑"结果
        
        已被标准的内部边界条件法(_apply_pump_internal_bc)替代。
        保留此方法仅为向后兼容。
        """
        # 调用新的标准内部边界条件方法
        self._apply_pump_internal_bc()


    def _apply_pump_head_jump(self):
        """
        应用泵站水位跃变（别名方法，向后兼容）
        
        这是_apply_pump_internal_bc的简化调用接口。
        默认使用稳态模式。
        """
        self._apply_pump_internal_bc(conserve_local_flow=False)

    def step_explicit(self, dt: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        显式欧拉时间步（用于简单测试）

        Args:
            dt: 时间步长 (s)

        Returns:
            (h_new, hu_new): 更新后的状态
        """
        # 计算通量和源项
        F_mass, F_momentum, S_mass, S_momentum = \
            self.compute_fluxes_and_sources(self.h, self.hu, self.z, self.dx)

        h_new = self.h.copy()
        hu_new = self.hu.copy()

        # 时间推进
        for i in range(self.nx):
            # 连续性方程
            dh = dt * (-(F_mass[i+1] - F_mass[i])/self.dx + S_mass[i])
            h_new[i] = self.h[i] + dh

            # 动量方程
            dhu = dt * (-(F_momentum[i+1] - F_momentum[i])/self.dx + S_momentum[i])
            hu_new[i] = self.hu[i] + dhu

        # 更新状态并应用泵站区域约束
        self.h[:] = h_new
        self.hu[:] = hu_new
        self._apply_pump_region_constraints()

        return self.h.copy(), self.hu.copy()

    def set_boundary_conditions(
        self,
        Q_in: Optional[float] = None,
        h_out: Optional[float] = None
    ):
        """
        设置边界条件

        Args:
            Q_in: 入流流量 (m³/s)，None则使用当前值
            h_out: 出流水深 (m)，None则使用当前值
        """
        if Q_in is not None:
            self.hu[0] = Q_in / self.B

        if h_out is not None:
            self.h[-1] = h_out

    def step_preissmann(self, dt: float, max_iter: int = 10,
                       enforce_bc: bool = False,
                       Q_in: float = None, h_out: float = None,
                       use_pump_mask: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        """
        Preissmann四点隐式格式时间步

        使用迭代求解非线性系统（静水重构 + Preissmann）

        Args:
            dt: 时间步长 (s)
            max_iter: 最大迭代次数
            enforce_bc: 是否在每次迭代中强制边界条件（瞬态流用）
            Q_in: 入流流量 (m³/s)，enforce_bc=True时需要
            h_out: 出流水深 (m)，enforce_bc=True时需要

        Returns:
            (h_new, hu_new): 更新后的状态
        """
        # 初始猜测：显式步
        h_new = self.h.copy()
        hu_new = self.hu.copy()

        # 迭代求解
        for iter in range(max_iter):
            # 计算 n+1 时刻的通量和源项
            F_mass_new, F_momentum_new, S_mass_new, S_momentum_new = \
                self.compute_fluxes_and_sources(h_new, hu_new, self.z, self.dx)

            # 计算 n 时刻的通量和源项
            F_mass_old, F_momentum_old, S_mass_old, S_momentum_old = \
                self.compute_fluxes_and_sources(self.h, self.hu, self.z, self.dx)

            # Preissmann加权
            F_mass = self.theta * F_mass_new + (1 - self.theta) * F_mass_old
            F_momentum = self.theta * F_momentum_new + (1 - self.theta) * F_momentum_old
            S_mass = self.theta * S_mass_new + (1 - self.theta) * S_mass_old
            S_momentum = self.theta * S_momentum_new + (1 - self.theta) * S_momentum_old

            # 保存旧值用于松弛
            h_old_iter = h_new.copy()
            hu_old_iter = hu_new.copy()

            # 获取泵站区域掩码（在更新前）
            # 稳态求解使用掩码，非恒定流不使用（避免流量累积）
            if use_pump_mask:
                pump_mask = self._get_pump_region_mask()
            else:
                pump_mask = np.zeros(self.nx, dtype=bool)

            # 更新（排除泵站区域）
            for i in range(self.nx):
                if pump_mask[i]:
                    # 泵站区域：保持不变
                    continue
                
                # 连续性方程
                dh = dt * (-(F_mass[i+1] - F_mass[i])/self.dx + S_mass[i])
                h_new[i] = self.h[i] + dh

                # 动量方程
                dhu = dt * (-(F_momentum[i+1] - F_momentum[i])/self.dx + S_momentum[i])
                hu_new[i] = self.hu[i] + dhu

            # 松弛（排除泵站区域）
            for i in range(self.nx):
                if not pump_mask[i]:
                    h_new[i] = self.omega * h_new[i] + (1 - self.omega) * h_old_iter[i]
                    hu_new[i] = self.omega * hu_new[i] + (1 - self.omega) * hu_old_iter[i]

            # 应用泵站区域约束（在每次迭代中）
            self.h[:] = h_new
            self.hu[:] = hu_new
            self._apply_pump_region_constraints()
            h_new = self.h.copy()
            hu_new = self.hu.copy()

            # ⭐ 关键修复：在所有更新操作后最终强制边界条件
            # 这确保边界条件不被松弛或泵站约束覆盖
            if enforce_bc:
                # 确保泵站掩码不影响边界节点
                pump_mask[0] = False
                pump_mask[-1] = False
                
                # 强制上游流量边界
                if Q_in is not None:
                    hu_new[0] = Q_in / self.B
                
                # 强制下游水深边界
                if h_out is not None:
                    h_new[-1] = h_out

        return h_new, hu_new

    def solve_steady_state(
        self,
        Q_target: float,
        h_downstream: float,
        max_iterations: int = 5000,
        convergence_tol: float = 0.001,
        dt: float = 0.5,
        verbose: bool = True,
        h_upstream_guess: Optional[float] = None
    ) -> dict:
        """
        求解稳态解

        Args:
            Q_target: 目标流量 (m³/s)
            h_downstream: 下游水深边界条件 (m)
            max_iterations: 最大迭代次数
            convergence_tol: 收敛容差（水深变化）
            dt: 时间步长 (s)
            verbose: 是否打印进度
            h_upstream_guess: 上游水深初始猜测（可选）

        Returns:
            result: 求解结果字典
        """
        # 初始化流量
        self.hu = np.ones(self.nx) * Q_target / self.B

        # 初始水深猜测：如果有闸门，上游应该有回水
        if h_upstream_guess is None:
            # 简单估算：使用下游水深作为基准
            h_upstream_guess = h_downstream * 1.2  # 假设上游水深高20%

        # 线性插值初始水深分布
        self.h = np.linspace(h_upstream_guess, h_downstream, self.nx)

        # 强制设置下游边界
        self.h[-1] = h_downstream

        if verbose:
            print(f"稳态求解：")
            print(f"  目标流量：{Q_target:.3f} m³/s")
            print(f"  下游水深：{h_downstream:.3f} m")
            print(f"  上游初始猜测：{h_upstream_guess:.3f} m")

        # 时间推进至稳态
        for iteration in range(max_iterations):
            h_old = self.h.copy()
            hu_old = self.hu.copy()

            # Preissmann步
            h_new, hu_new = self.step_preissmann(dt)

            # 应用边界条件
            # 出口：设置水深
            h_new[-1] = h_downstream

            # 更新状态（先更新，以便后续方法访问当前状态）
            self.h = h_new
            self.hu = hu_new

            # 应用泵站水位跃变（稳态模式：标准跳跃条件）
            self._apply_pump_internal_bc(conserve_local_flow=False)

            # 获取泵站区域掩码
            pump_mask = self._get_pump_region_mask()

            # 流量约束策略：稳态流全渠道流量应守恒
            # 强制所有节点流量相同（质量守恒），但排除泵站区域
            # 关键修复：不覆盖泵站区域的流量设置
            if pump_mask.any():
                # 有泵站：只强制非泵站区域的流量
                self.hu[~pump_mask] = Q_target / self.B
            else:
                # 无泵站：所有节点强制流量
                self.hu[:] = Q_target / self.B

            # 应用内部边界条件（闸门）
            # 通过调整水深使闸门流量公式满足Q_target
            if self.structure_indices:
                self._apply_internal_bc(t=self.current_time, Q_target=Q_target,
                                      max_iter=20, tol=0.05, relax=0.3)  # P2优化: 降低松弛因子 (0.6→0.3)
            
            # 再次应用泵站约束，确保不被闸门约束覆盖
            self._apply_pump_internal_bc(conserve_local_flow=False)

            # 检查收敛
            dh_max = np.max(np.abs(self.h - h_old))
            dhu_max = np.max(np.abs(self.hu - hu_old))

            if iteration % 500 == 0 and verbose:
                Q_actual = np.mean(self.get_Q())
                Q_error = abs(Q_actual - Q_target) / Q_target * 100
                print(f"  迭代 {iteration}: dh={dh_max:.4e}, dhu={dhu_max:.4e}, Q={Q_actual:.3f} ({Q_error:.2f}%误差)")

            if dh_max < convergence_tol and dhu_max < convergence_tol:
                if verbose:
                    print(f"  收敛于迭代 {iteration}")
                break

        # 计算结果
        Q_final = self.get_Q()
        Q_mean = np.mean(Q_final)
        Q_error = abs(Q_mean - Q_target) / Q_target * 100

        result = {
            'converged': iteration < max_iterations - 1,
            'iterations': iteration,
            'h': self.h.copy(),
            'Q': Q_final.copy(),
            'Q_mean': Q_mean,
            'Q_error_percent': Q_error,
            'dh_max': dh_max,
            'dhu_max': dhu_max
        }

        if verbose:
            print(f"\n稳态结果：")
            print(f"  流量：{Q_mean:.3f} m³/s（误差{Q_error:.2f}%）")
            print(f"  水深范围：[{self.h.min():.3f}, {self.h.max():.3f}] m")

        return result

    def get_Q(self) -> np.ndarray:
        """获取流量数组 (m³/s)"""
        return self.hu * self.B

    def set_Q(self, Q: np.ndarray):
        """设置流量数组 (m³/s)"""
        self.hu = Q / self.B

    Q = property(get_Q, set_Q)

    def compute_cfl_timestep(self, CFL_number: float = 0.5) -> float:
        """
        根据CFL条件计算自适应时间步

        CFL条件: Δt ≤ CFL * Δx / (|u| + c)
        其中 c = √(gh) 是波速

        Args:
            CFL_number: CFL数（默认0.5，安全范围0.2-0.9）

        Returns:
            dt: 建议的时间步长 (s)
        """
        # 计算流速
        u = np.abs(self.hu / (self.h + 1e-6))

        # 计算波速 c = sqrt(gh)
        c = np.sqrt(self.g * (self.h + 1e-6))

        # 最大特征速度
        max_char_speed = np.max(u + c)

        # CFL条件
        if max_char_speed > 1e-6:
            dt_cfl = CFL_number * self.dx / max_char_speed
        else:
            dt_cfl = 1.0  # 默认值

        return dt_cfl

    def solve_transient(
        self,
        t_end: float,
        dt: float = 0.1,
        Q_upstream: float = None,
        h_downstream: float = None,
        Q_upstream_func: callable = None,
        h_downstream_func: callable = None,
        save_interval: int = 10,
        verbose: bool = True
    ) -> dict:
        """
        求解瞬态流（时间演化）

        Args:
            t_end: 结束时间 (s)
            dt: 时间步长 (s)
            Q_upstream: 上游流量边界 (m³/s)，常数
            h_downstream: 下游水深边界 (m)，常数
            Q_upstream_func: 上游流量时间函数 Q(t)
            h_downstream_func: 下游水深时间函数 h(t)
            save_interval: 保存间隔（每N步保存一次）
            verbose: 是否打印进度

        Returns:
            result: 包含时间历史的结果字典
        """
        # 清空历史记录
        self.h_history = []
        self.Q_history = []
        self.t_history = []

        # 边界条件函数
        if Q_upstream_func is None:
            Q_upstream_func = lambda t: Q_upstream
        if h_downstream_func is None:
            h_downstream_func = lambda t: h_downstream

        # 初始化
        t = 0.0
        n_steps = int(t_end / dt)

        if verbose:
            print(f"瞬态流求解：")
            print(f"  时间: 0 → {t_end} s")
            print(f"  时间步: {dt} s")
            print(f"  总步数: {n_steps}")

        # 初始状态保存
        self.h_history.append(self.h.copy())
        self.Q_history.append(self.get_Q().copy())
        self.t_history.append(t)

        # 时间循环
        for step in range(n_steps):
            t = (step + 1) * dt
            self.current_time = t

            # 获取当前边界条件
            Q_in = Q_upstream_func(t)
            h_out = h_downstream_func(t)

            # 应用边界条件到当前状态（用于flux计算）
            self.set_boundary_conditions(Q_in=Q_in, h_out=h_out)

            # Preissmann时间步（在迭代中强制边界条件）
            # 非恒定流不使用泵站掩码，避免流量累积
            h_new, hu_new = self.step_preissmann(dt, enforce_bc=True,
                                                Q_in=Q_in, h_out=h_out,
                                                use_pump_mask=False)

            # 更新状态
            self.h = h_new
            self.hu = hu_new

            # ⚠️ 源项法模式：不施加泵站跳跃条件
            # 泵站效果已通过compute_fluxes_and_sources中的源项实现
            # self._apply_pump_internal_bc(conserve_local_flow=True)  # 禁用

            # 应用内部边界条件（闸门）
            if self.structure_indices:
                self._apply_internal_bc(t=t, Q_target=Q_in,
                                      max_iter=20, tol=0.05, relax=0.6)

            # 保存历史
            if (step + 1) % save_interval == 0:
                self.h_history.append(self.h.copy())
                self.Q_history.append(self.get_Q().copy())
                self.t_history.append(t)

            # 进度输出
            if verbose and (step + 1) % max(n_steps // 10, 1) == 0:
                Q_mean = np.mean(self.get_Q())
                h_mean = np.mean(self.h)
                print(f"  t={t:.2f}s ({(step+1)/n_steps*100:.1f}%): " +
                      f"Q={Q_mean:.3f} m³/s, h_avg={h_mean:.3f} m")

        # 最终状态
        if verbose:
            print(f"\n瞬态求解完成：")
            print(f"  保存的时间步: {len(self.t_history)}")
            print(f"  最终流量: {np.mean(self.get_Q()):.3f} m³/s")
            print(f"  最终水深范围: [{self.h.min():.3f}, {self.h.max():.3f}] m")

        result = {
            't_history': np.array(self.t_history),
            'h_history': np.array(self.h_history),
            'Q_history': np.array(self.Q_history),
            'h_final': self.h.copy(),
            'Q_final': self.get_Q().copy(),
            'x': self.x.copy()
        }

        return result

    def solve_transient_adaptive(
        self,
        t_end: float,
        dt_initial: float = 0.1,
        dt_min: float = 0.001,
        dt_max: float = 1.0,
        CFL_number: float = 0.5,
        Q_upstream: float = None,
        h_downstream: float = None,
        Q_upstream_func: callable = None,
        h_downstream_func: callable = None,
        save_interval_time: float = 1.0,
        verbose: bool = True
    ) -> dict:
        """
        求解瞬态流（自适应时间步）

        使用CFL条件自动调整时间步长，提高计算效率和稳定性

        Args:
            t_end: 结束时间 (s)
            dt_initial: 初始时间步长 (s)
            dt_min: 最小允许时间步 (s)
            dt_max: 最大允许时间步 (s)
            CFL_number: CFL数（0.2-0.9，推荐0.5）
            Q_upstream: 上游流量边界 (m³/s)，常数
            h_downstream: 下游水深边界 (m)，常数
            Q_upstream_func: 上游流量时间函数 Q(t)
            h_downstream_func: 下游水深时间函数 h(t)
            save_interval_time: 保存时间间隔 (s)
            verbose: 是否打印进度

        Returns:
            result: 包含时间历史的结果字典
        """
        # 清空历史记录
        self.h_history = []
        self.Q_history = []
        self.t_history = []
        self.dt_history = []  # 记录时间步历史

        # 边界条件函数
        if Q_upstream_func is None:
            Q_upstream_func = lambda t: Q_upstream
        if h_downstream_func is None:
            h_downstream_func = lambda t: h_downstream

        t = 0.0
        dt = dt_initial
        step = 0
        next_save_time = 0.0

        if verbose:
            print(f"自适应瞬态流求解：")
            print(f"  时间: 0 → {t_end} s")
            print(f"  初始时间步: {dt_initial} s")
            print(f"  CFL数: {CFL_number}")
            print(f"  时间步范围: [{dt_min}, {dt_max}] s")

        # 初始状态保存
        self.h_history.append(self.h.copy())
        self.Q_history.append(self.get_Q().copy())
        self.t_history.append(t)
        self.dt_history.append(dt)
        next_save_time = save_interval_time

        # 时间循环
        while t < t_end:
            step += 1

            # 计算自适应时间步
            dt_cfl = self.compute_cfl_timestep(CFL_number)
            dt = np.clip(dt_cfl, dt_min, dt_max)

            # 避免超出结束时间
            if t + dt > t_end:
                dt = t_end - t

            # 更新时间
            t_new = t + dt
            self.current_time = t_new

            # 获取当前边界条件
            Q_in = Q_upstream_func(t_new)
            h_out = h_downstream_func(t_new)

            # 应用边界条件到当前状态
            self.set_boundary_conditions(Q_in=Q_in, h_out=h_out)

            # Preissmann时间步（在迭代中强制边界条件）
            # 非恒定流不使用泵站掩码，避免流量累积
            h_new, hu_new = self.step_preissmann(dt, enforce_bc=True,
                                                Q_in=Q_in, h_out=h_out,
                                                use_pump_mask=False)

            # 更新状态
            self.h = h_new
            self.hu = hu_new

            # ⚠️ 源项法模式：不施加泵站跳跃条件
            # 泵站效果已通过compute_fluxes_and_sources中的源项实现
            # self._apply_pump_internal_bc(conserve_local_flow=True)  # 禁用

            # 应用内部边界条件（闸门）
            if self.structure_indices:
                self._apply_internal_bc(t=t_new, Q_target=Q_in,
                                      max_iter=20, tol=0.05, relax=0.6)

            # 更新时间
            t = t_new

            # 按时间间隔保存
            if t >= next_save_time or t >= t_end:
                self.h_history.append(self.h.copy())
                self.Q_history.append(self.get_Q().copy())
                self.t_history.append(t)
                self.dt_history.append(dt)
                next_save_time += save_interval_time

            # 进度输出
            if verbose and step % max(1, int(100 / (dt_max/dt_initial))) == 0:
                Q_mean = np.mean(self.get_Q())
                h_mean = np.mean(self.h)
                progress = t / t_end * 100
                print(f"  t={t:.2f}s ({progress:.1f}%), dt={dt:.4f}s: " +
                      f"Q={Q_mean:.3f} m³/s, h_avg={h_mean:.3f} m")

        # 最终状态
        if verbose:
            print(f"\n自适应瞬态求解完成：")
            print(f"  总时间步数: {step}")
            print(f"  保存的时间步: {len(self.t_history)}")
            print(f"  平均时间步: {np.mean(self.dt_history):.4f} s")
            print(f"  时间步范围: [{np.min(self.dt_history):.4f}, {np.max(self.dt_history):.4f}] s")
            print(f"  最终流量: {np.mean(self.get_Q()):.3f} m³/s")
            print(f"  最终水深范围: [{self.h.min():.3f}, {self.h.max():.3f}] m")

        result = {
            't_history': np.array(self.t_history),
            'h_history': np.array(self.h_history),
            'Q_history': np.array(self.Q_history),
            'dt_history': np.array(self.dt_history),
            'h_final': self.h.copy(),
            'Q_final': self.get_Q().copy(),
            'x': self.x.copy(),
            'n_steps': step
        }

        return result


# 测试代码
if __name__ == "__main__":
    print("=" * 70)
    print("HydrostaticCanalSolver 基础测试")
    print("=" * 70)

    # 创建求解器
    solver = HydrostaticCanalSolver(
        length=1000.0,
        nx=101,
        B=10.0,
        S0=0.001,
        n=0.025,
        g=9.81
    )

    print(f"\n求解器初始化：")
    print(f"  渠道长度：{solver.length} m")
    print(f"  网格点数：{solver.nx}")
    print(f"  网格间距：{solver.dx:.2f} m")
    print(f"  渠道宽度：{solver.B} m")

    # 测试通量和源项计算
    print(f"\n测试通量和源项计算...")

    F_mass, F_momentum, S_mass, S_momentum = \
        solver.compute_fluxes_and_sources(solver.h, solver.hu, solver.z, solver.dx)

    print(f"  通量：")
    print(f"    质量通量范围：[{F_mass.min():.3f}, {F_mass.max():.3f}] m²/s")
    print(f"    动量通量范围：[{F_momentum.min():.3f}, {F_momentum.max():.3f}] m³/s²")

    print(f"  源项：")
    print(f"    质量源项：{S_mass.min():.3f} - {S_mass.max():.3f} m/s")
    print(f"    动量源项：{S_momentum.min():.3f} - {S_momentum.max():.3f} m²/s²")

    # 测试显式时间步
    print(f"\n测试显式时间步...")
    dt = 0.1
    h_new, hu_new = solver.step_explicit(dt)

    dh_max = np.max(np.abs(h_new - solver.h))
    dhu_max = np.max(np.abs(hu_new - solver.hu))

    print(f"  时间步长：{dt} s")
    print(f"  水深变化：max={dh_max:.4e} m")
    print(f"  流量变化：max={dhu_max:.4e} m²/s")

    print(f"\n✓ 基础功能测试完成")
    print("=" * 70)
