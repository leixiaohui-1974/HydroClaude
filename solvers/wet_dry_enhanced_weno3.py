#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
湿干界面增强WENO3求解器（Phase 8.2）

核心特性：
1. 集成Phase 8.1正定性保持
2. 增强型湿干界面检测
3. 界面特殊通量计算
4. 质量守恒监控

目标：
- RP5-RP7干床问题误差：>400% → <50%
- 质量守恒误差：<0.1%
- 正定性：h≥0恒成立

参考文献：
- Toro, E.F. (2001). Shock-Capturing Methods for Free-Surface Shallow Flows.
- Zhang, X., & Shu, C.W. (2010). Positivity-preserving high order finite difference WENO schemes.
- Audusse, E., et al. (2004). A fast and stable well-balanced scheme with hydrostatic reconstruction.

作者: HydroClaude Team
日期: 2025-10-31
阶段: Stage 8 - Phase 8.2
"""

import numpy as np
from typing import Tuple, Dict, Optional
from solvers.positivity_preserving_weno3 import PositivityPreservingWENO3


class WetDryEnhancedWENO3(PositivityPreservingWENO3):
    """
    湿干界面增强WENO3求解器（Phase 8.2）

    继承层次：
    GodunvFVMSolver → GodunvFVMWENO3 → PositivityPreservingWENO3 → WetDryEnhancedWENO3

    新增特性：
    1. 湿干界面检测（_detect_wet_dry_interface）
    2. 界面特殊通量（_hll_flux_wet_dry）
    3. 增强型正定性保持限制器
    4. 质量守恒监控
    """

    def __init__(
        self,
        width: float,
        length: float,
        n_cells: int,
        manning_n: float,
        slope: float,
        g: float = 9.81,
        cfl: float = 0.2,
        eps_dry: float = 1e-6,
        eps_pp: float = 1e-10,
        theta_min: float = 0.0,
        wet_dry_threshold: float = 1e-4,
        interface_theta_max: float = 0.3,
        use_pp: bool = True,
        use_wd_flux: bool = True,
        use_enhanced_bc: bool = True,
        well_balanced: bool = False,
        use_numba: bool = False,
        **kwargs
    ):
        """
        初始化湿干界面增强WENO3求解器

        Args:
            ... (继承参数)
            wet_dry_threshold: 湿干界面阈值（默认1e-4）
            interface_theta_max: 界面处最大θ系数（默认0.3）
            use_wd_flux: 是否使用界面特殊通量（默认True）
        """
        # 调用父类初始化（Phase 8.1）
        super().__init__(
            width=width,
            length=length,
            n_cells=n_cells,
            manning_n=manning_n,
            slope=slope,
            g=g,
            cfl=cfl,
            eps_dry=eps_dry,
            eps_pp=eps_pp,
            theta_min=theta_min,
            use_pp=use_pp,
            use_enhanced_bc=use_enhanced_bc,
            well_balanced=well_balanced,
            use_numba=use_numba,
            **kwargs
        )

        # Phase 8.2特有参数
        self.wet_dry_threshold = wet_dry_threshold
        self.interface_theta_max = interface_theta_max
        self.use_wd_flux = use_wd_flux

        # 统计信息
        self.wd_activations = 0  # 界面通量激活次数
        self.interface_type_counts = {
            'wet_to_dry': 0,
            'dry_to_wet': 0,
            'vacuum_forming': 0
        }

        # 质量守恒监控
        self.initial_mass = None
        self.mass_history = []

        print(f"\n{'='*70}")
        print("湿干界面增强WENO3求解器（Phase 8.2）")
        print(f"{'='*70}")
        print(f"基础: 正定性保持WENO3（Phase 8.1）")
        print(f"湿干界面阈值: {self.wet_dry_threshold}")
        print(f"界面最大θ: {self.interface_theta_max}")
        print(f"界面特殊通量: {'启用' if self.use_wd_flux else '禁用'}")
        print(f"{'='*70}\n")

    def _detect_wet_dry_interface(self, h: np.ndarray) -> Dict:
        """
        检测湿干界面

        Args:
            h: 水深数组

        Returns:
            dict: 包含界面信息
                - is_interface[i]: cell i是否是界面
                - interface_type[i]: 界面类型
                - n_interfaces: 界面总数
        """
        n = len(h)
        is_interface = np.zeros(n, dtype=bool)
        interface_type = ['none'] * n

        for i in range(n):
            # 获取邻居水深
            h_left = h[i-1] if i > 0 else h[i]
            h_center = h[i]
            h_right = h[i+1] if i < n-1 else h[i]

            # 检查邻居中是否有湿有干
            neighbors = [h_left, h_center, h_right]
            has_wet = any(h_val > self.wet_dry_threshold for h_val in neighbors)
            has_dry = any(h_val <= self.wet_dry_threshold for h_val in neighbors)

            if has_wet and has_dry:
                is_interface[i] = True

                # 判断界面类型
                if h_center > self.wet_dry_threshold:
                    # 中心湿，邻居有干 → wet_to_dry
                    if h_left <= self.wet_dry_threshold or h_right <= self.wet_dry_threshold:
                        interface_type[i] = 'wet_to_dry'
                else:
                    # 中心干，邻居有湿 → dry_to_wet
                    if h_left > self.wet_dry_threshold or h_right > self.wet_dry_threshold:
                        interface_type[i] = 'dry_to_wet'

                # 近真空检测（RP7）：中心干，两边湿
                if (h_center <= self.wet_dry_threshold and
                    h_left > self.wet_dry_threshold and
                    h_right > self.wet_dry_threshold):
                    interface_type[i] = 'vacuum_forming'

        n_interfaces = np.sum(is_interface)

        return {
            'is_interface': is_interface,
            'interface_type': interface_type,
            'n_interfaces': n_interfaces
        }

    def _is_interface_face(self, face_idx: int, interface_info: Dict) -> bool:
        """
        判断界面face是否是湿干界面

        Args:
            face_idx: 界面索引（0到n）
            interface_info: 界面检测信息

        Returns:
            bool: 是否是湿干界面
        """
        is_interface = interface_info['is_interface']
        n = len(is_interface)

        # face i+1/2 在cell i和cell i+1之间
        # 如果任一侧是界面，则face是界面
        is_wd_face = False

        if face_idx > 0 and face_idx <= n:
            # 检查左侧cell (i-1)
            if is_interface[face_idx - 1]:
                is_wd_face = True

        if face_idx >= 0 and face_idx < n:
            # 检查右侧cell (i)
            if is_interface[face_idx]:
                is_wd_face = True

        return is_wd_face

    def _hll_flux_wet_dry(
        self,
        h_L: float,
        Q_L: float,
        h_R: float,
        Q_R: float
    ) -> Tuple[float, float]:
        """
        湿干界面修正HLL通量

        参考: Toro (2001), Section 5.4

        处理四种情况：
        1. 两侧都干 → 零通量
        2. 左干右湿 → 单侧稀疏波（RP5）
        3. 左湿右干 → 单侧稀疏波（RP6）
        4. 两侧都湿 → 标准HLL

        Args:
            h_L, Q_L: 左状态
            h_R, Q_R: 右状态

        Returns:
            F_h, F_Q: 通量
        """
        # 干床检测
        dry_L = h_L < self.eps_dry
        dry_R = h_R < self.eps_dry

        # Case 1: 两侧都干
        if dry_L and dry_R:
            return 0.0, 0.0

        # Case 2: 左干右湿（RP5类型）
        if dry_L and not dry_R:
            # 只使用右状态
            A_R = max(h_R * self.B, self.eps_dry * self.B)
            u_R = Q_R / A_R
            c_R = np.sqrt(self.g * h_R)

            # 稀疏波前沿波速
            S_R = u_R + 2.0 * c_R

            if S_R <= 0.0:
                # 超音速向左（通常不会发生在RP5）
                F_h = Q_R
                F_Q = Q_R**2 / A_R + 0.5 * self.g * h_R**2 * self.B
            else:
                # 右向稀疏波扩展到干床
                # 使用零通量（保守策略）
                F_h = 0.0
                F_Q = 0.0

            return F_h, F_Q

        # Case 3: 左湿右干（RP6类型）
        if not dry_L and dry_R:
            # 只使用左状态
            A_L = max(h_L * self.B, self.eps_dry * self.B)
            u_L = Q_L / A_L
            c_L = np.sqrt(self.g * h_L)

            # 稀疏波前沿波速
            S_L = u_L - 2.0 * c_L

            if S_L >= 0.0:
                # 超音速向右（通常不会发生在RP6）
                F_h = Q_L
                F_Q = Q_L**2 / A_L + 0.5 * self.g * h_L**2 * self.B
            else:
                # 左向稀疏波扩展到干床
                # 使用零通量（保守策略）
                F_h = 0.0
                F_Q = 0.0

            return F_h, F_Q

        # Case 4: 两侧都湿（使用标准HLL）
        # 调用父类的HLL通量
        return self._hll_flux(h_L, Q_L, h_R, Q_R)

    def _compute_wet_dry_flux(
        self,
        h: np.ndarray,
        Q: np.ndarray,
        interface_info: Dict
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        计算湿干界面特殊通量（所有faces）

        Args:
            h: 水深数组
            Q: 流量数组
            interface_info: 界面检测信息

        Returns:
            F_h, F_Q: 通量数组（长度n+1）
        """
        n = len(h)
        F_h = np.zeros(n + 1)
        F_Q = np.zeros(n + 1)

        for i in range(n + 1):
            # 获取界面左右状态
            if i == 0:
                # 左边界（使用ghost cell或边界值）
                h_L = h[0]
                Q_L = Q[0]
            else:
                h_L = h[i-1]
                Q_L = Q[i-1]

            if i == n:
                # 右边界
                h_R = h[-1]
                Q_R = Q[-1]
            else:
                h_R = h[i]
                Q_R = Q[i]

            # 使用修正HLL通量
            F_h[i], F_Q[i] = self._hll_flux_wet_dry(h_L, Q_L, h_R, Q_R)

        return F_h, F_Q

    def _compute_positivity_limiter_enhanced(
        self,
        h: np.ndarray,
        Q: np.ndarray,
        F_h_weno: np.ndarray,
        F_Q_weno: np.ndarray,
        F_h_first: np.ndarray,
        F_Q_first: np.ndarray,
        interface_info: Dict
    ) -> np.ndarray:
        """
        增强型正定性保持限制系数（湿干界面增强）

        在湿干界面处：
        - 强制 θ <= interface_theta_max（默认0.3）
        - 真空形成区域：完全降为一阶（θ=0）

        Args:
            ... (同Phase 8.1)
            interface_info: 界面检测信息

        Returns:
            theta: 限制系数数组（长度n+1）
        """
        # 调用父类方法（Phase 8.1基础限制器）
        theta = self._compute_positivity_limiter(
            h, Q, F_h_weno, F_Q_weno, F_h_first, F_Q_first
        )

        # 湿干界面增强
        is_interface = interface_info['is_interface']
        interface_type = interface_info['interface_type']
        n = len(h)

        for i in range(n + 1):
            # face i+1/2对应的cell索引
            cells_to_check = []
            if i > 0:
                cells_to_check.append(i - 1)
            if i < n:
                cells_to_check.append(i)

            # 检查相邻cells是否是界面
            for cell_idx in cells_to_check:
                if is_interface[cell_idx]:
                    # 湿干界面：限制θ
                    theta[i] = min(theta[i], self.interface_theta_max)

                    # 真空形成区域：完全降为一阶
                    if interface_type[cell_idx] == 'vacuum_forming':
                        theta[i] = 0.0

        return theta

    def _compute_rhs(
        self,
        h: np.ndarray,
        Q: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        计算右端项（湿干界面增强版）

        步骤：
        0. 检测湿干界面
        1. 计算WENO3通量（继承）
        2. 计算一阶通量（继承）
        3. 计算湿干界面特殊通量
        4. 计算增强型正定性保持限制系数
        5. 混合三种通量
        6. 计算时间导数

        Args:
            h: 水深数组
            Q: 流量数组

        Returns:
            dh_dt, dQ_dt: 时间导数
        """
        n = len(h)

        # === Step 0: 检测湿干界面 ===
        interface_info = self._detect_wet_dry_interface(h)
        n_interfaces = interface_info['n_interfaces']

        # === Step 1: 计算标准WENO3通量 ===
        # 扩展边界条件
        h_ext, Q_ext = self._extend_ghost_cells(h, Q)

        # WENO3重构
        h_L_weno, h_R_weno = self._weno3_reconstruction(h_ext)
        Q_L_weno, Q_R_weno = self._weno3_reconstruction(Q_ext)

        # 计算WENO3通量
        F_h_weno = np.zeros(n + 1)
        F_Q_weno = np.zeros(n + 1)

        for i in range(n + 1):
            F_h_weno[i], F_Q_weno[i] = self._hll_flux(
                h_L_weno[i], Q_L_weno[i], h_R_weno[i], Q_R_weno[i]
            )

        # === Step 2: 计算一阶HLL通量（保证正定性） ===
        F_h_first = np.zeros(n + 1)
        F_Q_first = np.zeros(n + 1)

        for i in range(n + 1):
            # 获取左右状态（不做重构）
            if i == 0:
                h_L_first = h[0]
                Q_L_first = Q[0]
            else:
                h_L_first = h[i-1]
                Q_L_first = Q[i-1]

            if i == n:
                h_R_first = h[-1]
                Q_R_first = Q[-1]
            else:
                h_R_first = h[i]
                Q_R_first = Q[i]

            F_h_first[i], F_Q_first[i] = self._hll_flux(
                h_L_first, Q_L_first, h_R_first, Q_R_first
            )

        # === Step 3: 计算湿干界面特殊通量 ===
        if self.use_wd_flux and n_interfaces > 0:
            F_h_wd, F_Q_wd = self._compute_wet_dry_flux(h, Q, interface_info)
        else:
            F_h_wd = None
            F_Q_wd = None

        # === Step 4: 计算增强型正定性保持限制系数θ ===
        if self.use_pp:
            theta = self._compute_positivity_limiter_enhanced(
                h, Q, F_h_weno, F_Q_weno, F_h_first, F_Q_first, interface_info
            )
        else:
            theta = np.ones(n + 1)

        # === Step 5: 混合三种通量 ===
        F_h = np.zeros(n + 1)
        F_Q = np.zeros(n + 1)

        wd_flux_used = 0

        for i in range(n + 1):
            # 判断是否是湿干界面
            is_wd_face = self._is_interface_face(i, interface_info)

            if self.use_wd_flux and is_wd_face and F_h_wd is not None:
                # 湿干界面：使用特殊通量
                F_h[i] = F_h_wd[i]
                F_Q[i] = F_Q_wd[i]
                wd_flux_used += 1
            else:
                # 非界面：使用正定性保持混合通量（Phase 8.1）
                F_h[i] = theta[i] * F_h_weno[i] + (1.0 - theta[i]) * F_h_first[i]
                F_Q[i] = theta[i] * F_Q_weno[i] + (1.0 - theta[i]) * F_Q_first[i]

        # 统计
        if wd_flux_used > 0:
            self.wd_activations += 1
            for i in range(n):
                if interface_info['is_interface'][i]:
                    itype = interface_info['interface_type'][i]
                    self.interface_type_counts[itype] += 1

        # === Step 6: 计算时间导数 ===
        dh_dt = np.zeros(n)
        dQ_dt = np.zeros(n)

        for i in range(n):
            dh_dt[i] = -(F_h[i+1] - F_h[i]) / self.dx
            dQ_dt[i] = -(F_Q[i+1] - F_Q[i]) / self.dx
            dQ_dt[i] += self._compute_source_term(h[i], Q[i], i)

        return dh_dt, dQ_dt

    def step(self, dt: Optional[float] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        时间步进（覆盖以添加质量守恒监控）

        Args:
            dt: 时间步长（可选）

        Returns:
            h, Q: 更新后的状态
        """
        # 调用父类step
        h, Q = super().step(dt)

        # 质量守恒监控
        self._check_mass_conservation()

        return h, Q

    def _check_mass_conservation(self):
        """
        检查质量守恒

        干床问题容易出现质量损失，需要监控
        """
        # 计算当前总质量
        total_mass = np.sum(self.h * self.dx * self.B)

        if self.initial_mass is None:
            # 记录初始质量
            self.initial_mass = total_mass
            self.mass_history = [total_mass]
        else:
            self.mass_history.append(total_mass)

            # 计算相对误差
            if abs(self.initial_mass) > 1e-14:
                mass_error = abs(total_mass - self.initial_mass) / self.initial_mass * 100

                # 如果质量损失超过1%，发出警告
                if mass_error > 1.0:
                    print(f"⚠️  警告：质量损失 {mass_error:.2f}% 在 t={self.t:.4f}s")

    def get_statistics(self) -> Dict:
        """
        获取统计信息（包含湿干界面统计）

        Returns:
            dict: 统计信息
        """
        # 获取Phase 8.1统计信息
        stats = super().get_statistics()

        # 添加Phase 8.2湿干界面统计
        stats['wd_activations'] = self.wd_activations

        if self.step_count > 0:
            stats['interface_flux_usage_rate'] = self.wd_activations / self.step_count
        else:
            stats['interface_flux_usage_rate'] = 0.0

        stats['interface_type_counts'] = self.interface_type_counts.copy()

        # 质量守恒误差
        if self.initial_mass is not None and abs(self.initial_mass) > 1e-14:
            current_mass = np.sum(self.h * self.dx * self.B)
            stats['mass_conservation_error'] = abs(current_mass - self.initial_mass) / self.initial_mass * 100
        else:
            stats['mass_conservation_error'] = 0.0

        stats['mass_history'] = self.mass_history.copy() if self.mass_history else []

        return stats

    def print_statistics(self):
        """打印统计信息（湿干界面增强版）"""
        stats = self.get_statistics()

        print(f"\n{'='*70}")
        print("湿干界面增强WENO3统计信息")
        print(f"{'='*70}")

        # Phase 8.1统计
        print("\n[正定性保持统计（Phase 8.1）]")
        print(f"总时间步数: {stats['total_steps']}")
        print(f"激活次数: {stats['pp_activations']}")
        print(f"激活率: {stats['activation_rate']*100:.2f}%")

        if stats['pp_activations'] > 0:
            print(f"最小θ: {stats['min_theta']:.6f}")
            print(f"平均θ: {stats['avg_theta']:.6f}")

        # Phase 8.2统计
        print("\n[湿干界面统计（Phase 8.2）]")
        print(f"界面通量激活: {stats['wd_activations']}")
        print(f"界面通量使用率: {stats['interface_flux_usage_rate']*100:.2f}%")

        print("\n界面类型分布:")
        total_interfaces = sum(stats['interface_type_counts'].values())
        if total_interfaces > 0:
            for itype, count in stats['interface_type_counts'].items():
                percentage = count / total_interfaces * 100
                print(f"  - {itype}: {count} ({percentage:.1f}%)")
        else:
            print("  （无湿干界面）")

        print(f"\n质量守恒误差: {stats['mass_conservation_error']:.4f}%")

        print(f"\n{'='*70}")
        print("说明:")
        print("- θ=1.0: 完全高阶WENO3")
        print("- θ∈(0,1): 混合格式")
        print("- θ=0.0: 完全一阶或界面特殊通量")
        print("- 界面通量使用率: 湿干界面被检测并使用特殊通量的比例")
        print(f"{'='*70}\n")


# =============================================================================
# 快速测试函数
# =============================================================================

def quick_test():
    """
    快速测试湿干界面增强WENO3求解器

    测试RP5（左侧干床）简化版本
    """
    print("\n" + "="*80)
    print("快速测试：湿干界面增强WENO3求解器（Phase 8.2）")
    print("="*80)

    # 参数设置
    L = 100.0
    B = 10.0
    x_dam = L / 2.0
    n_cells = 200  # 粗网格快速测试
    t_end = 0.2  # 短时间

    # RP5简化：左干右湿
    h_L, u_L = 0.0, 0.0
    h_R, u_R = 2.0, 0.0  # 降低水深，加快计算

    print(f"\n测试配置（RP5简化版）:")
    print(f"- 左侧: h={h_L}, u={u_L} (干床)")
    print(f"- 右侧: h={h_R}, u={u_R} (湿)")
    print(f"- 网格: {n_cells} cells")
    print(f"- 模拟时间: {t_end}s")

    # 创建求解器
    solver = WetDryEnhancedWENO3(
        width=B,
        length=L,
        n_cells=n_cells,
        manning_n=0.0,
        slope=0.0,
        cfl=0.2,
        eps_pp=1e-10,
        theta_min=0.0,
        wet_dry_threshold=1e-4,
        interface_theta_max=0.3,
        use_pp=True,
        use_wd_flux=True,
        use_enhanced_bc=True,
        well_balanced=False,
        use_numba=False
    )

    # 初始条件
    x = solver.x
    h_init = np.where(x <= x_dam, h_L, h_R)
    Q_init = B * np.where(x <= x_dam, h_L * u_L, h_R * u_R)

    bc_left = {'type': 'transmissive'}
    bc_right = {'type': 'transmissive'}
    solver.initialize(h_init, Q_init, bc_left, bc_right)

    # 运行
    print(f"\n运行中...")
    step_count = 0

    while solver.t < t_end:
        solver.step()
        step_count += 1

        if step_count % 20 == 0:
            h_min = np.min(solver.h)
            h_max = np.max(solver.h)
            print(f"  Step {step_count}: t={solver.t:.4f}s, h∈[{h_min:.4f}, {h_max:.4f}]")

    print(f"\n完成！总步数: {step_count}, 最终时间: t={solver.t:.4f}s")

    # 统计信息
    solver.print_statistics()

    # 检查正定性
    h_min = np.min(solver.h)
    print(f"\n正定性检查:")
    print(f"- 最小水深: {h_min:.6e}")
    if h_min >= 0.0:
        print("- ✅ 正定性保持成功（h≥0）")
    else:
        print(f"- ❌ 正定性违背（h<0）")

    # 质量守恒检查
    stats = solver.get_statistics()
    mass_error = stats['mass_conservation_error']
    print(f"\n质量守恒检查:")
    print(f"- 相对误差: {mass_error:.4f}%")
    if mass_error < 0.1:
        print("- ✅ 质量守恒良好（<0.1%）")
    elif mass_error < 1.0:
        print("- ⚠️  质量守恒一般（<1.0%）")
    else:
        print("- ❌ 质量守恒较差（>1.0%）")

    print("\n" + "="*80)
    print("快速测试完成！")
    print("="*80)

    return solver


if __name__ == '__main__':
    # 运行快速测试
    solver = quick_test()
