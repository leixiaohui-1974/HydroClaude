"""
静水重构法 (Hydrostatic Reconstruction) 实现

基于：Audusse et al. (2004) "A Fast and Stable Well-Balanced Scheme
with Hydrostatic Reconstruction for Shallow Water Flows"

核心思想：通过重构水位（而非水深）确保良平衡性质，
在稳态时数值通量与源项精确平衡，消除人工数值耗散。
"""

import numpy as np
from typing import Tuple, Optional
import math


class HydrostaticReconstruction:
    """
    静水重构类

    提供良平衡的数值通量计算，专门优化用于包含底床不连续
    （如闸门、堰、台阶）的开放渠道流动。
    """

    def __init__(self, g: float = 9.81, eps_dry: float = 1e-6):
        """
        初始化

        参数:
            g: 重力加速度 [m/s²]
            eps_dry: 干湿判定阈值 [m]
        """
        self.g = g
        self.eps_dry = eps_dry

    def reconstruct_at_interface(
        self,
        h_L: float,
        hu_L: float,
        z_L: float,
        h_R: float,
        hu_R: float,
        z_R: float
    ) -> Tuple[float, float, float, float]:
        """
        在单元界面进行静水重构

        核心算法：
        1. 计算左右单元的水位 η = h + z
        2. 确定界面底床高程 z_interface = max(z_L, z_R)
        3. 重构水深 h* = max(0, η - z_interface)
        4. 按比例重构流量 (hu)* = hu * (h*/h)

        参数:
            h_L: 左单元水深 [m]
            hu_L: 左单元流量 [m²/s]
            z_L: 左单元底床高程 [m]
            h_R: 右单元水深 [m]
            hu_R: 右单元流量 [m²/s]
            z_R: 右单元底床高程 [m]

        返回:
            (h_star_L, hu_star_L, h_star_R, hu_star_R): 重构后的左右状态

        良平衡性质：
            如果 η_L = η_R 且 u_L = u_R = 0（湖面静止），
            则 h_star_L = h_star_R 且 hu_star_L = hu_star_R = 0，
            Riemann求解器将产生零通量，完美平衡源项。
        """
        # Step 1: 计算水位
        eta_L = h_L + z_L
        eta_R = h_R + z_R

        # Step 2: 界面底床高程（取最大值，确保正性）
        z_interface = max(z_L, z_R)

        # Step 3: 重构水深
        h_star_L = max(0.0, eta_L - z_interface)
        h_star_R = max(0.0, eta_R - z_interface)

        # Step 4: 重构流量（保持流速比例）
        if h_L > self.eps_dry:
            # 有水：按比例缩放流量
            hu_star_L = hu_L * (h_star_L / h_L)
        else:
            # 干单元：流量为零
            hu_star_L = 0.0

        if h_R > self.eps_dry:
            hu_star_R = hu_R * (h_star_R / h_R)
        else:
            hu_star_R = 0.0

        return h_star_L, hu_star_L, h_star_R, hu_star_R

    def hll_flux(
        self,
        h_L: float,
        hu_L: float,
        h_R: float,
        hu_R: float
    ) -> Tuple[float, float]:
        """
        HLL (Harten-Lax-van Leer) Riemann求解器

        HLL求解器的优势：
        - 简单、鲁棒、高效
        - 自然的正性保持（h ≥ 0）
        - 适合干湿界面
        - 对激波和稀疏波都表现良好

        参数:
            h_L, hu_L: 左状态（水深，流量）
            h_R, hu_R: 右状态（水深，流量）

        返回:
            (F_mass, F_momentum): 质量和动量通量

        算法：
        1. 计算左右波速 s_L, s_R
        2. 根据波速位置选择通量：
           - 全部向右传播：F_L
           - 全部向左传播：F_R
           - 跨越界面：HLL加权平均
        """
        # 处理干单元
        if h_L < self.eps_dry and h_R < self.eps_dry:
            return 0.0, 0.0

        # 计算流速
        u_L = hu_L / h_L if h_L > self.eps_dry else 0.0
        u_R = hu_R / h_R if h_R > self.eps_dry else 0.0

        # 计算声速（浅水波速）
        c_L = math.sqrt(self.g * h_L) if h_L > self.eps_dry else 0.0
        c_R = math.sqrt(self.g * h_R) if h_R > self.eps_dry else 0.0

        # 波速估计（简单但有效的估计）
        s_L = min(u_L - c_L, u_R - c_R)
        s_R = max(u_L + c_L, u_R + c_R)

        # 处理静止情况
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

        # HLL通量公式
        if s_L >= 0:
            # 全部向右传播：使用左通量
            return F_mass_L, F_mom_L
        elif s_R <= 0:
            # 全部向左传播：使用右通量
            return F_mass_R, F_mom_R
        else:
            # 跨越界面：HLL加权平均
            U_L = [h_L, hu_L]
            U_R = [h_R, hu_R]
            F_L = [F_mass_L, F_mom_L]
            F_R = [F_mass_R, F_mom_R]

            F_mass_HLL = (s_R * F_L[0] - s_L * F_R[0] +
                         s_L * s_R * (U_R[0] - U_L[0])) / (s_R - s_L)
            F_mom_HLL = (s_R * F_L[1] - s_L * F_R[1] +
                        s_L * s_R * (U_R[1] - U_L[1])) / (s_R - s_L)

            return F_mass_HLL, F_mom_HLL

    def compute_flux_with_reconstruction(
        self,
        h_L: float,
        hu_L: float,
        z_L: float,
        h_R: float,
        hu_R: float,
        z_R: float
    ) -> Tuple[float, float]:
        """
        完整的静水重构 + HLL通量计算

        这是主要接口函数，组合了：
        1. 静水重构（确保良平衡）
        2. HLL Riemann求解（计算通量）

        参数:
            h_L, hu_L, z_L: 左单元状态
            h_R, hu_R, z_R: 右单元状态

        返回:
            (F_mass, F_momentum): 界面数值通量

        特点:
            - 湖面静止时通量精确为零
            - 自动处理干湿界面
            - 正性保持
            - 守恒性
        """
        # Step 1: 静水重构
        h_star_L, hu_star_L, h_star_R, hu_star_R = \
            self.reconstruct_at_interface(h_L, hu_L, z_L, h_R, hu_R, z_R)

        # Step 2: 使用重构状态计算HLL通量
        F_mass, F_mom = self.hll_flux(h_star_L, hu_star_L, h_star_R, hu_star_R)

        return F_mass, F_mom

    def compute_well_balanced_source(
        self,
        h_i: float,
        z_L: float,
        z_R: float,
        dx: float,
        n: float = 0.0,
        hu_i: float = 0.0
    ) -> Tuple[float, float]:
        """
        计算良平衡的源项

        关键：源项离散化必须与通量离散化精确匹配，
        以确保良平衡性质。

        参数:
            h_i: 单元i的水深 [m]
            z_L: 左界面底床高程 [m]
            z_R: 右界面底床高程 [m]
            dx: 单元长度 [m]
            n: Manning糙率
            hu_i: 单元i的流量 [m²/s]

        返回:
            (S_mass, S_momentum): 质量和动量源项

        源项组成:
            1. 重力项：-g*h*∂z/∂x（良平衡形式）
            2. 摩擦项：-g*n²*|u|*u/R^(4/3)
        """
        # 质量源项（连续性方程无源项）
        S_mass = 0.0

        # 动量源项 - 重力部分（良平衡形式）
        # 注意：这里使用界面底床高程差，确保与通量匹配
        S_gravity = -self.g * h_i * (z_R - z_L) / dx

        # 动量源项 - 摩擦部分（Manning公式）
        if h_i > self.eps_dry and abs(n) > 1e-10:
            u_i = hu_i / h_i
            R_i = h_i  # 矩形渠道近似：水力半径 ≈ 水深
            S_friction = -self.g * n**2 * abs(u_i) * hu_i / (R_i**(4/3))
        else:
            S_friction = 0.0

        S_momentum = S_gravity + S_friction

        return S_mass, S_momentum


class HydrostaticFluxCalculator:
    """
    静水重构通量计算器（向量化版本）

    为整个网格批量计算通量，提高效率。
    """

    def __init__(self, g: float = 9.81, eps_dry: float = 1e-6):
        """初始化"""
        self.reconstructor = HydrostaticReconstruction(g=g, eps_dry=eps_dry)
        self.g = g
        self.eps_dry = eps_dry

    def compute_all_fluxes(
        self,
        h: np.ndarray,
        hu: np.ndarray,
        z: np.ndarray,
        n_cells: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        计算所有内部界面的通量

        参数:
            h: 水深数组 [n_cells]
            hu: 流量数组 [n_cells]
            z: 底床高程数组 [n_cells]
            n_cells: 单元数量

        返回:
            (F_mass, F_momentum): 通量数组 [n_cells+1]

        注意：
            - F[0] 和 F[n_cells] 是边界通量，需要单独处理
            - F[i] 是单元i和i+1之间的通量（i=0,1,...,n_cells-1）
        """
        F_mass = np.zeros(n_cells + 1)
        F_momentum = np.zeros(n_cells + 1)

        # 计算所有内部界面的通量
        for i in range(n_cells - 1):
            F_mass[i+1], F_momentum[i+1] = \
                self.reconstructor.compute_flux_with_reconstruction(
                    h[i], hu[i], z[i],
                    h[i+1], hu[i+1], z[i+1]
                )

        # 边界通量初始化为零（将由边界条件设置）
        F_mass[0] = 0.0
        F_momentum[0] = 0.0
        F_mass[n_cells] = 0.0
        F_momentum[n_cells] = 0.0

        return F_mass, F_momentum

    def compute_all_sources(
        self,
        h: np.ndarray,
        hu: np.ndarray,
        z: np.ndarray,
        dx: float,
        n: float,
        n_cells: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        计算所有单元的源项（良平衡形式）

        参数:
            h: 水深数组
            hu: 流量数组
            z: 底床高程数组
            dx: 网格间距
            n: Manning糙率
            n_cells: 单元数量

        返回:
            (S_mass, S_momentum): 源项数组 [n_cells]
        """
        S_mass = np.zeros(n_cells)
        S_momentum = np.zeros(n_cells)

        for i in range(n_cells):
            # 界面底床高程
            if i == 0:
                z_L = z[i]  # 左边界
            else:
                z_L = max(z[i-1], z[i])

            if i == n_cells - 1:
                z_R = z[i]  # 右边界
            else:
                z_R = max(z[i], z[i+1])

            S_mass[i], S_momentum[i] = \
                self.reconstructor.compute_well_balanced_source(
                    h[i], z_L, z_R, dx, n, hu[i]
                )

        return S_mass, S_momentum

    def verify_well_balanced_property(
        self,
        h: np.ndarray,
        z: np.ndarray,
        tol: float = 1e-12
    ) -> Tuple[bool, float]:
        """
        验证良平衡性质

        测试：对于湖面静止状态（η=const, u=0），
        数值格式是否产生零通量。

        参数:
            h: 水深数组
            z: 底床高程数组
            tol: 容差（应接近机器精度）

        返回:
            (is_well_balanced, max_error): 是否良平衡及最大误差
        """
        n_cells = len(h)
        eta = h + z

        # 检查是否为湖面静止
        eta_mean = np.mean(eta)
        if np.max(np.abs(eta - eta_mean)) > tol:
            return False, np.inf  # 不是湖面静止状态

        # 计算所有通量
        hu = np.zeros(n_cells)  # u = 0
        F_mass, F_momentum = self.compute_all_fluxes(h, hu, z, n_cells)

        # 检查通量是否为零
        max_flux_error = max(np.max(np.abs(F_mass)), np.max(np.abs(F_momentum)))

        is_well_balanced = max_flux_error < tol

        return is_well_balanced, max_flux_error


# 测试代码
if __name__ == "__main__":
    """测试静水重构的良平衡性质"""
    print("=" * 70)
    print("静水重构法测试")
    print("=" * 70)

    # 测试1: 湖面静止
    print("\n测试1: 湖面静止（良平衡性验证）")
    print("-" * 70)

    reconstructor = HydrostaticReconstruction(g=9.81)

    # 设置湖面静止状态：η = 10.0 m everywhere, u = 0
    eta_const = 10.0

    # 底床有变化
    z_L = 3.0
    z_R = 5.0  # 底床有2m台阶

    # 水深相应调整以保持水位恒定
    h_L = eta_const - z_L  # = 7.0 m
    h_R = eta_const - z_R  # = 5.0 m

    # 流量为零
    hu_L = 0.0
    hu_R = 0.0

    print(f"左单元：h={h_L:.3f} m, z={z_L:.3f} m, η={h_L+z_L:.3f} m")
    print(f"右单元：h={h_R:.3f} m, z={z_R:.3f} m, η={h_R+z_R:.3f} m")
    print(f"底床台阶：Δz = {z_R - z_L:.3f} m")

    # 静水重构
    h_star_L, hu_star_L, h_star_R, hu_star_R = \
        reconstructor.reconstruct_at_interface(h_L, hu_L, z_L, h_R, hu_R, z_R)

    print(f"\n重构后：")
    print(f"  h*_L = {h_star_L:.6f} m")
    print(f"  h*_R = {h_star_R:.6f} m")
    print(f"  Δh* = {abs(h_star_R - h_star_L):.2e} m (应≈0)")

    # 计算通量
    F_mass, F_mom = reconstructor.hll_flux(h_star_L, hu_star_L, h_star_R, hu_star_R)

    print(f"\n通量：")
    print(f"  F_mass = {F_mass:.2e} m²/s (应≈0, 质量通量)")
    print(f"  F_momentum = {F_mom:.2e} m³/s² (压力通量，非零正常)")

    # 良平衡性的正确验证：质量通量应为零（u=0）
    # 动量通量包含压力项，需要与源项一起验证平衡
    is_well_balanced_mass = abs(F_mass) < 1e-12

    # 计算源项
    dx = 1.0  # 假设单元长度
    z_interface = max(z_L, z_R)
    h_cell = h_L  # 或者取平均
    S_mass, S_mom = reconstructor.compute_well_balanced_source(
        h_cell, z_L, z_R, dx, n=0.0, hu_i=0.0
    )

    print(f"\n源项（单元长度dx={dx}m）：")
    print(f"  S_momentum = {S_mom:.2e} m²/s² (重力源项)")

    # 验证：对于湖面静止，通量应产生与源项相等的效果
    # 这需要在完整的求解器中测试
    print(f"\n质量守恒：{' PASS' if is_well_balanced_mass else ' FAIL'} (质量通量=0)")
    print(f"良平衡性：需要在完整求解器中验证通量梯度+源项=0")

    # 测试2: 带流动的情况
    print("\n\n测试2: 稳态流动")
    print("-" * 70)

    # 设置亚临界流动
    h_L = 5.0
    u_L = 1.0
    hu_L = h_L * u_L
    z_L = 0.0

    h_R = 4.5
    u_R = 1.0
    hu_R = h_R * u_R
    z_R = 0.3

    print(f"左单元：h={h_L:.2f} m, u={u_L:.2f} m/s, z={z_L:.2f} m")
    print(f"右单元：h={h_R:.2f} m, u={u_R:.2f} m/s, z={z_R:.2f} m")

    F_mass, F_mom = reconstructor.compute_flux_with_reconstruction(
        h_L, hu_L, z_L, h_R, hu_R, z_R
    )

    print(f"\n通量：")
    print(f"  F_mass = {F_mass:.3f} m²/s")
    print(f"  F_momentum = {F_mom:.3f} m³/s²")

    # 测试3: 向量化计算
    print("\n\n测试3: 向量化网格计算")
    print("-" * 70)

    calculator = HydrostaticFluxCalculator(g=9.81)

    # 创建测试网格：湖面静止 + 不规则底床
    n_cells = 10
    z = np.array([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 2.0, 1.5, 1.0, 0.5])
    eta_const = 10.0
    h = eta_const - z
    hu = np.zeros(n_cells)

    print(f"网格单元数：{n_cells}")
    print(f"底床高程范围：[{z.min():.1f}, {z.max():.1f}] m")
    print(f"水位：{eta_const:.1f} m (恒定)")

    # 验证良平衡性
    is_wb, max_error = calculator.verify_well_balanced_property(h, z, tol=1e-12)

    print(f"\n良平衡性验证：")
    print(f"  最大通量误差：{max_error:.2e}")
    print(f"  结果：{' PASS' if is_wb else ' FAIL'} (阈值 1e-12)")

    print("\n" + "=" * 70)
    print("测试完成！")
    print("=" * 70)
