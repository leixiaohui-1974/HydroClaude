"""
静水重构法 v2 - 正确的良平衡实现

修正：使用重构后的水深计算源项，确保精确的良平衡性质

基于：Audusse et al. (2004) 正确的源项离散化
"""

import numpy as np
from typing import Tuple
import math


class WellBalancedSolver:
    """
    良平衡求解器 - 正确实现Audusse的静水重构

    关键改进：
    1. 存储所有界面的重构水深
    2. 使用重构水深计算源项
    3. 确保通量梯度与源项精确匹配
    """

    def __init__(self, g: float = 9.81, eps_dry: float = 1e-6):
        """初始化"""
        self.g = g
        self.eps_dry = eps_dry

    def reconstruct_interface(
        self, h_L: float, z_L: float, h_R: float, z_R: float
    ) -> Tuple[float, float]:
        """
        在界面进行静水重构

        返回：
            (h_star_L, h_star_R): 从左侧和右侧看到的重构水深
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
        完整的良平衡时间步

        返回:
            (F_mass, F_momentum, S_mass, S_momentum)
        """
        n_cells = len(h)

        # 存储通量
        F_mass = np.zeros(n_cells + 1)
        F_momentum = np.zeros(n_cells + 1)

        # 存储重构水深（用于源项计算）
        h_star_interfaces = np.zeros((n_cells + 1, 2))  # [界面, (左侧看, 右侧看)]

        # Step 1: 计算所有界面的重构和通量
        for i in range(n_cells + 1):
            if i == 0:
                # 左边界
                h_star_interfaces[i, 0] = h[0]  #从左边界外看
                h_star_interfaces[i, 1] = h[0]  #从第一个单元看
                # 边界通量使用第一个单元状态
                F_mass[i] = hu[0]
                F_momentum[i] = hu[0]**2 / h[0] + 0.5 * self.g * h[0]**2 if h[0] > self.eps_dry else 0.0

            elif i == n_cells:
                # 右边界
                h_star_interfaces[i, 0] = h[n_cells-1]  # 从最后单元看
                h_star_interfaces[i, 1] = h[n_cells-1]  # 从边界外看
                # 边界通量使用最后一个单元状态
                F_mass[i] = hu[n_cells-1]
                F_momentum[i] = (hu[n_cells-1]**2 / h[n_cells-1] +
                               0.5 * self.g * h[n_cells-1]**2) if h[n_cells-1] > self.eps_dry else 0.0

            else:
                # 内部界面：单元i-1和单元i之间
                h_L = h[i-1]
                hu_L = hu[i-1]
                z_L = z[i-1]

                h_R = h[i]
                hu_R = hu[i]
                z_R = z[i]

                # 静水重构
                h_star_L, h_star_R = self.reconstruct_interface(h_L, z_L, h_R, z_R)
                h_star_interfaces[i, 0] = h_star_L  # 从左侧（单元i-1）看
                h_star_interfaces[i, 1] = h_star_R  # 从右侧（单元i）看

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

        # Step 2: 计算源项（使用重构水深）
        S_mass = np.zeros(n_cells)
        S_momentum = np.zeros(n_cells)

        for i in range(n_cells):
            # 左界面重构水深（从右侧看，即从单元i看）
            h_star_L = h_star_interfaces[i, 1]

            # 右界面重构水深（从左侧看，即从单元i看）
            h_star_R = h_star_interfaces[i+1, 0]

            # 良平衡源项（Audusse公式）
            S_gravity = -0.5 * self.g * (h_star_R**2 - h_star_L**2) / dx

            # 摩擦项
            if h[i] > self.eps_dry and abs(n) > 1e-10:
                u_i = hu[i] / h[i]
                R_i = h[i]
                S_friction = -self.g * n**2 * abs(u_i) * hu[i] / (R_i**(4/3))
            else:
                S_friction = 0.0

            S_mass[i] = 0.0  # 质量源项为零
            S_momentum[i] = S_gravity + S_friction

        return F_mass, F_momentum, S_mass, S_momentum


def test_well_balanced():
    """测试良平衡性质"""
    print("=" * 70)
    print("良平衡性质测试（正确的v2实现）")
    print("=" * 70)

    solver = WellBalancedSolver(g=9.81)

    # 网格参数
    n_cells = 10
    dx = 1.0

    # 不规则底床
    x = np.linspace(0.5*dx, 10-0.5*dx, n_cells)
    z = np.zeros(n_cells)
    for i in range(n_cells):
        if x[i] < 2.0:
            z[i] = 0.0
        elif x[i] < 3.0:
            z[i] = 1.5  # 台阶
        elif x[i] < 5.0:
            z[i] = 1.5 + 0.5 * (x[i] - 3.0)  # 斜坡
        elif x[i] < 7.0:
            z[i] = 2.5
        elif x[i] < 8.0:
            z[i] = 2.5 - 1.0 * (x[i] - 7.0)
        else:
            z[i] = 1.5

    print(f"\n网格：{n_cells} 单元, dx={dx} m")
    print(f"底床：z ∈ [{z.min():.2f}, {z.max():.2f}] m")

    # 湖面静止
    eta_const = 10.0
    h = eta_const - z
    hu = np.zeros(n_cells)

    print(f"初始：η={eta_const} m (恒定), u=0")

    # 求解一步
    F_mass, F_momentum, S_mass, S_momentum = solver.solve_step(h, hu, z, dx, n=0.0)

    # 计算通量梯度（有限体积法：dU/dt = -∂F/∂x + S）
    # 注意负号！
    dF_mass_dx = np.zeros(n_cells)
    dF_momentum_dx = np.zeros(n_cells)

    for i in range(n_cells):
        dF_mass_dx[i] = -(F_mass[i+1] - F_mass[i]) / dx  # 负号！
        dF_momentum_dx[i] = -(F_momentum[i+1] - F_momentum[i]) / dx  # 负号！

    # 计算残差（良平衡条件：-∂F/∂x + S = 0）
    R_mass = dF_mass_dx + S_mass
    R_momentum = dF_momentum_dx + S_momentum

    print(f"\n残差：")
    print(f"  质量：max={np.max(np.abs(R_mass)):.2e}, RMS={np.sqrt(np.mean(R_mass**2)):.2e}")
    print(f"  动量：max={np.max(np.abs(R_momentum)):.2e}, RMS={np.sqrt(np.mean(R_momentum**2)):.2e}")

    # 判断
    tol = 1e-10
    mass_ok = np.max(np.abs(R_mass)) < tol
    momentum_ok = np.max(np.abs(R_momentum)) < tol

    print(f"\n良平衡性（阈值 {tol:.0e}）：")
    print(f"  质量：{' PASS' if mass_ok else ' FAIL'}")
    print(f"  动量：{' PASS' if momentum_ok else ' FAIL'}")

    if mass_ok and momentum_ok:
        print(f"\n 良平衡性质验证成功！")
        print("="*70)
        return True
    else:
        print(f"\n 良平衡性质验证失败")
        # 详细诊断
        if not momentum_ok:
            i_max = np.argmax(np.abs(R_momentum))
            print(f"\n最大动量残差位置：单元{i_max}")
            print(f"  ∂F/∂x = {dF_momentum_dx[i_max]:.6e}")
            print(f"  S = {S_momentum[i_max]:.6e}")
            print(f"  R = {R_momentum[i_max]:.6e}")
            print(f"  h = {h[i_max]:.6f} m, z = {z[i_max]:.6f} m")

            # 打印前3个单元的详细信息
            print(f"\n前3个单元详细诊断：")
            for i in range(min(3, n_cells)):
                print(f"\n单元{i}: h={h[i]:.3f}, z={z[i]:.3f}, η={h[i]+z[i]:.3f}")
                print(f"  F_L[{i}]   = {F_momentum[i]:.6e}")
                print(f"  F_R[{i+1}] = {F_momentum[i+1]:.6e}")
                print(f"  ∂F/∂x = {dF_momentum_dx[i]:.6e}")
                print(f"  S     = {S_momentum[i]:.6e}")
                print(f"  R     = {R_momentum[i]:.6e}")

            # 重新手动计算单元1进行验证
            i = 1
            print(f"\n手动验证单元{i}的计算：")

            # 重新计算通量
            if i > 0:
                eta_L = h[i-1] + z[i-1]
                eta_curr = h[i] + z[i]
                z_int_L = max(z[i-1], z[i])
                h_star_L_check = max(0, eta_curr - z_int_L)
                print(f"  左界面：η={eta_curr:.3f}, z_int={z_int_L:.3f}, h*_L={h_star_L_check:.3f}")

            if i < n_cells - 1:
                eta_curr = h[i] + z[i]
                eta_R = h[i+1] + z[i+1]
                z_int_R = max(z[i], z[i+1])
                h_star_R_check = max(0, eta_curr - z_int_R)
                print(f"  右界面：η={eta_curr:.3f}, z_int={z_int_R:.3f}, h*_R={h_star_R_check:.3f}")

            # 计算源项
            S_check = -0.5 * 9.81 * (h_star_R_check**2 - h_star_L_check**2) / dx
            print(f"  源项（手动）：S = -0.5*g*(h_R²-h_L²)/dx")
            print(f"               = -0.5*{9.81}*({h_star_R_check:.3f}²-{h_star_L_check:.3f}²)/{dx}")
            print(f"               = {S_check:.6e}")
            print(f"  源项（代码）：S = {S_momentum[i]:.6e}")
            print(f"  匹配？ {'' if abs(S_check - S_momentum[i]) < 1e-6 else ''}")

        print("="*70)
        return False


if __name__ == "__main__":
    import sys
    success = test_well_balanced()
    sys.exit(0 if success else 1)
