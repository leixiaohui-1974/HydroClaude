"""
静水重构法 v3 - 正确的边界条件处理

关键改进：使用虚拟单元（ghost cells）确保边界单元也满足良平衡性质

边界条件类型：
1. 周期边界（Periodic）
2. 反射边界（Reflective/Wall）
3. 外推边界（Extrapolation）
"""

import numpy as np
from typing import Tuple, Optional
import math
from enum import Enum


class BoundaryType(Enum):
    """边界条件类型"""
    PERIODIC = "periodic"          # 周期边界
    REFLECTIVE = "reflective"      # 反射边界（固壁）
    EXTRAPOLATION = "extrapolation"  # 外推边界
    TRANSMISSIVE = "transmissive"  # 透射边界（自然边界）


class WellBalancedSolverV3:
    """
    良平衡求解器 v3 - 正确的边界条件

    关键改进：
    1. 虚拟单元（ghost cells）方法
    2. 边界也进行静水重构
    3. 确保边界单元的良平衡性
    """

    def __init__(self,
                 g: float = 9.81,
                 eps_dry: float = 1e-6,
                 bc_left: BoundaryType = BoundaryType.TRANSMISSIVE,
                 bc_right: BoundaryType = BoundaryType.TRANSMISSIVE):
        """
        初始化

        参数:
            g: 重力加速度
            eps_dry: 干湿判定阈值
            bc_left: 左边界条件
            bc_right: 右边界条件
        """
        self.g = g
        self.eps_dry = eps_dry
        self.bc_left = bc_left
        self.bc_right = bc_right

    def setup_ghost_cells(
        self,
        h: np.ndarray,
        hu: np.ndarray,
        z: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        设置虚拟单元（边界外侧的虚拟状态）

        参数:
            h, hu, z: 物理单元数据 [n_cells]

        返回:
            h_ext, hu_ext, z_ext: 扩展数据 [n_cells+2]（包含左右虚拟单元）
        """
        n_cells = len(h)

        # 创建扩展数组（包含左右各1个虚拟单元）
        h_ext = np.zeros(n_cells + 2)
        hu_ext = np.zeros(n_cells + 2)
        z_ext = np.zeros(n_cells + 2)

        # 复制物理单元数据到中间
        h_ext[1:-1] = h
        hu_ext[1:-1] = hu
        z_ext[1:-1] = z

        # 左边界虚拟单元（索引0）
        if self.bc_left == BoundaryType.TRANSMISSIVE:
            # 透射：外推（保持水位，流速）
            eta_0 = h[0] + z[0]
            z_ext[0] = z[0]  # 底床外推
            h_ext[0] = eta_0 - z_ext[0]
            hu_ext[0] = hu[0]

        elif self.bc_left == BoundaryType.REFLECTIVE:
            # 反射：镜像（水深相同，流速反向）
            h_ext[0] = h[0]
            hu_ext[0] = -hu[0]  # 流速反向
            z_ext[0] = z[0]

        elif self.bc_left == BoundaryType.EXTRAPOLATION:
            # 外推：零梯度
            h_ext[0] = h[0]
            hu_ext[0] = hu[0]
            z_ext[0] = z[0]

        # 右边界虚拟单元（索引n_cells+1）
        if self.bc_right == BoundaryType.TRANSMISSIVE:
            # 透射：外推
            eta_n = h[-1] + z[-1]
            z_ext[-1] = z[-1]  # 底床外推
            h_ext[-1] = eta_n - z_ext[-1]
            hu_ext[-1] = hu[-1]

        elif self.bc_right == BoundaryType.REFLECTIVE:
            # 反射：镜像
            h_ext[-1] = h[-1]
            hu_ext[-1] = -hu[-1]
            z_ext[-1] = z[-1]

        elif self.bc_right == BoundaryType.EXTRAPOLATION:
            # 外推：零梯度
            h_ext[-1] = h[-1]
            hu_ext[-1] = hu[-1]
            z_ext[-1] = z[-1]

        return h_ext, hu_ext, z_ext

    def reconstruct_interface(
        self, h_L: float, z_L: float, h_R: float, z_R: float
    ) -> Tuple[float, float]:
        """静水重构"""
        eta_L = h_L + z_L
        eta_R = h_R + z_R
        z_interface = max(z_L, z_R)

        h_star_L = max(0.0, eta_L - z_interface)
        h_star_R = max(0.0, eta_R - z_interface)

        return h_star_L, h_star_R

    def hll_flux(
        self, h_L: float, hu_L: float, h_R: float, hu_R: float
    ) -> Tuple[float, float]:
        """HLL Riemann求解器"""
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

    def solve_step(
        self,
        h: np.ndarray,
        hu: np.ndarray,
        z: np.ndarray,
        dx: float,
        n: float = 0.0
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        完整的良平衡时间步（带正确边界条件）

        返回:
            (F_mass, F_momentum, S_mass, S_momentum)
        """
        n_cells = len(h)

        # Step 1: 设置虚拟单元
        h_ext, hu_ext, z_ext = self.setup_ghost_cells(h, hu, z)

        # 存储通量（n_cells+1个界面，包括两个边界）
        F_mass = np.zeros(n_cells + 1)
        F_momentum = np.zeros(n_cells + 1)

        # 存储重构水深（用于源项计算）
        # h_star[i] = (从左看, 从右看) 对于界面i
        h_star_interfaces = np.zeros((n_cells + 1, 2))

        # Step 2: 计算所有界面的通量（包括边界）
        for i in range(n_cells + 1):
            # 界面i在扩展数组中是单元i和i+1之间
            # 对应物理单元：界面0是虚拟单元和单元0，界面n_cells是单元n_cells-1和虚拟单元

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

        # Step 3: 计算源项（使用重构水深）
        S_mass = np.zeros(n_cells)
        S_momentum = np.zeros(n_cells)

        for i in range(n_cells):
            # 物理单元i的左界面是界面i，右界面是界面i+1

            # 左界面重构水深（从右侧看，即从单元i看）
            h_star_L = h_star_interfaces[i, 1]

            # 右界面重构水深（从左侧看，即从单元i看）
            h_star_R = h_star_interfaces[i+1, 0]

            # 良平衡源项（Audusse公式）
            # S = g/2 * (h*_{i+1/2}² - h*_{i-1/2}²) / dx
            # 注意：右界面在前！
            S_gravity = 0.5 * self.g * (h_star_R**2 - h_star_L**2) / dx

            # 摩擦项
            if h[i] > self.eps_dry and abs(n) > 1e-10:
                u_i = hu[i] / h[i]
                R_i = h[i]
                S_friction = -self.g * n**2 * abs(u_i) * hu[i] / (R_i**(4/3))
            else:
                S_friction = 0.0

            S_mass[i] = 0.0
            S_momentum[i] = S_gravity + S_friction

        return F_mass, F_momentum, S_mass, S_momentum


def test_well_balanced_v3():
    """测试v3的良平衡性质"""
    print("=" * 70)
    print("良平衡性质测试 v3（正确的边界条件）")
    print("=" * 70)

    # 创建求解器（使用透射边界条件）
    solver = WellBalancedSolverV3(
        g=9.81,
        bc_left=BoundaryType.TRANSMISSIVE,
        bc_right=BoundaryType.TRANSMISSIVE
    )

    # 测试1: 平坦底床
    print("\n【测试1: 平坦底床】")
    print("-" * 70)

    n_cells = 10
    dx = 1.0
    z = np.zeros(n_cells)
    h = 10.0 * np.ones(n_cells)
    hu = np.zeros(n_cells)

    print(f"设置：z=0, h=10m, u=0")

    F_mass, F_momentum, S_mass, S_momentum = solver.solve_step(h, hu, z, dx, n=0.0)

    # 计算残差
    R_mass = np.zeros(n_cells)
    R_momentum = np.zeros(n_cells)

    for i in range(n_cells):
        dF_mass = -(F_mass[i+1] - F_mass[i]) / dx
        dF_momentum = -(F_momentum[i+1] - F_momentum[i]) / dx
        R_mass[i] = dF_mass + S_mass[i]
        R_momentum[i] = dF_momentum + S_momentum[i]

    max_R_mass = np.max(np.abs(R_mass))
    max_R_momentum = np.max(np.abs(R_momentum))

    print(f"残差：")
    print(f"  质量：max={max_R_mass:.2e}")
    print(f"  动量：max={max_R_momentum:.2e}")

    test1_pass = max_R_mass < 1e-10 and max_R_momentum < 1e-10
    print(f"结果：{'✓✓✓ PASS' if test1_pass else '✗✗✗ FAIL'}")

    # 测试2: 复杂地形
    print("\n【测试2: 复杂地形】")
    print("-" * 70)

    n_cells = 10
    dx = 1.0
    x = np.linspace(0.5*dx, 10-0.5*dx, n_cells)
    z = np.zeros(n_cells)

    # 创建不规则底床
    for i in range(n_cells):
        if x[i] < 2.0:
            z[i] = 0.0
        elif x[i] < 3.0:
            z[i] = 1.5  # 台阶
        elif x[i] < 5.0:
            z[i] = 1.5 + 0.5 * (x[i] - 3.0)  # 斜坡
        elif x[i] < 7.0:
            z[i] = 2.5  # 平台
        elif x[i] < 8.0:
            z[i] = 2.5 - 1.0 * (x[i] - 7.0)  # 下降
        else:
            z[i] = 1.5

    # 湖面静止
    eta_const = 10.0
    h = eta_const - z
    hu = np.zeros(n_cells)

    print(f"设置：不规则底床（z: {z.min():.1f}-{z.max():.1f}m），η=10m恒定，u=0")

    F_mass, F_momentum, S_mass, S_momentum = solver.solve_step(h, hu, z, dx, n=0.0)

    # 计算残差
    R_mass = np.zeros(n_cells)
    R_momentum = np.zeros(n_cells)

    for i in range(n_cells):
        dF_mass = -(F_mass[i+1] - F_mass[i]) / dx
        dF_momentum = -(F_momentum[i+1] - F_momentum[i]) / dx
        R_mass[i] = dF_mass + S_mass[i]
        R_momentum[i] = dF_momentum + S_momentum[i]

    max_R_mass = np.max(np.abs(R_mass))
    max_R_momentum = np.max(np.abs(R_momentum))
    rms_R_momentum = np.sqrt(np.mean(R_momentum**2))

    print(f"残差：")
    print(f"  质量：max={max_R_mass:.2e}")
    print(f"  动量：max={max_R_momentum:.2e}, RMS={rms_R_momentum:.2e}")

    test2_pass = max_R_mass < 1e-10 and max_R_momentum < 1e-10

    if not test2_pass:
        # 详细诊断
        i_max = np.argmax(np.abs(R_momentum))
        print(f"\n最大残差位置：单元{i_max}")
        print(f"  h={h[i_max]:.3f}, z={z[i_max]:.3f}, η={h[i_max]+z[i_max]:.3f}")
        print(f"  F_L={F_momentum[i_max]:.3f}, F_R={F_momentum[i_max+1]:.3f}")
        print(f"  ∂F/∂x={-(F_momentum[i_max+1]-F_momentum[i_max])/dx:.3f}")
        print(f"  S={S_momentum[i_max]:.3f}")
        print(f"  R={R_momentum[i_max]:.3f}")

    print(f"结果：{'✓✓✓ PASS' if test2_pass else '✗✗✗ FAIL'}")

    # 总结
    print("\n" + "=" * 70)
    overall_pass = test1_pass and test2_pass
    if overall_pass:
        print("✓✓✓ 所有测试通过！良平衡性质验证成功！")
    else:
        print("部分测试失败")
    print("=" * 70)

    return overall_pass


if __name__ == "__main__":
    import sys
    success = test_well_balanced_v3()
    sys.exit(0 if success else 1)
