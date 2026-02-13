"""测试平坦底床的良平衡性"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import sys
sys.path.append('.')

try:
    from solvers.hydrostatic_reconstruction_v3 import WellBalancedSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)


def test_flat_bed():
    """平坦底床测试 - 最简单的情况"""
    print("="*70)
    print("平坦底床良平衡性测试")
    print("="*70)

    solver = WellBalancedSolver(g=9.81)

    # 完全平坦的底床
    n_cells = 10
    dx = 1.0
    z = np.zeros(n_cells)  # 所有单元z=0
    h = 10.0 * np.ones(n_cells)  # 所有单元h=10
    hu = np.zeros(n_cells)  # u=0

    print(f"\n设置：")
    print(f"  单元数：{n_cells}")
    print(f"  底床：z=0 (完全平坦)")
    print(f"  水深：h=10 m (everywhere)")
    print(f"  流速：u=0 (湖面静止)")

    # 求解
    F_mass, F_momentum, S_mass, S_momentum = solver.solve_step(h, hu, z, dx, n=0.0)

    print(f"\n通量：")
    print(f"  所有界面通量应该相同")
    print(f"  F_momentum = {F_momentum}")
    print(f"  F_momentum[0] = {F_momentum[0]:.6e}")
    print(f"  F_momentum[1] = {F_momentum[1]:.6e}")
    print(f"  差异 = {abs(F_momentum[1] - F_momentum[0]):.6e}")

    # 通量梯度
    dF_dx = np.zeros(n_cells)
    for i in range(n_cells):
        dF_dx[i] = -(F_momentum[i+1] - F_momentum[i]) / dx

    print(f"\n通量梯度：")
    print(f"  所有单元应该为零（通量恒定）")
    print(f"  max|∂F/∂x| = {np.max(np.abs(dF_dx)):.6e}")

    print(f"\n源项：")
    print(f"  所有单元应该为零（平坦底床）")
    print(f"  max|S| = {np.max(np.abs(S_momentum)):.6e}")

    # 残差
    R = dF_dx + S_momentum

    print(f"\n残差：")
    print(f"  max|R| = {np.max(np.abs(R)):.6e}")

    tol = 1e-10
    success = np.max(np.abs(R)) < tol

    print(f"\n结果（阈值{tol:.0e}）：{' PASS' if success else ' FAIL'}")
    print("="*70)

    return success

if __name__ == "__main__":
    success = test_flat_bed()
    sys.exit(0 if success else 1)
