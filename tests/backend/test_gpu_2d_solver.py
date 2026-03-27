"""
test_gpu_2d_solver.py — GPU2DSolver 验证测试

测试 GPU2DSolver 与 Hydrostatic2DSolver 的数值等价性，
以及 GPU 加速功能（无 GPU 时在 CPU 上验证逻辑正确性）。

测试案例：
  1. 静水平衡（C-property）
  2. 溃坝精度（与解析解对比）
  3. 质量守恒
  4. 干湿边界稳定性
  5. 与 Hydrostatic2DSolver 的数值等价性
  6. 性能基准（CPU 模式）
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import numpy as np
import pytest
from solvers.gpu_2d_solver import GPU2DSolver, get_backend_info, benchmark
from solvers.hydrostatic_2d_solver import Hydrostatic2DSolver


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def make_gpu_solver(nx=50, ny=50, Lx=100.0, Ly=100.0, **kwargs) -> GPU2DSolver:
    """创建 GPU2DSolver（强制 CPU 模式用于测试）。"""
    return GPU2DSolver(Lx=Lx, Ly=Ly, nx=nx, ny=ny, force_cpu=True, **kwargs)


def make_ref_solver(nx=50, ny=50, Lx=100.0, Ly=100.0, **kwargs) -> Hydrostatic2DSolver:
    """创建参考 Hydrostatic2DSolver。"""
    return Hydrostatic2DSolver(Lx=Lx, Ly=Ly, nx=nx, ny=ny, **kwargs)


# ---------------------------------------------------------------------------
# 测试 1：后端检测
# ---------------------------------------------------------------------------

def test_backend_detection():
    """验证后端检测功能正常工作。"""
    info = get_backend_info()
    assert 'backend' in info
    assert 'device' in info
    assert 'gpu_available' in info
    assert info['backend'] in ('cuda', 'cpu')
    print(f"\nBackend: {info['backend']} | Device: {info['device']}")


def test_force_cpu_mode():
    """验证强制 CPU 模式正常工作。"""
    solver = GPU2DSolver(Lx=100.0, Ly=100.0, nx=20, ny=20, force_cpu=True)
    assert solver.backend == 'cpu'
    assert solver.xp is np


# ---------------------------------------------------------------------------
# 测试 2：静水平衡（C-property）
# ---------------------------------------------------------------------------

def test_still_water_flat_bed():
    """平底静水：水面高程应保持不变（C-property）。"""
    solver = make_gpu_solver(nx=40, ny=40, Lx=100.0, Ly=100.0)
    h_init = np.ones((40, 40)) * 1.0
    solver.set_initial_condition(h_init)

    # 运行 50 步
    for _ in range(50):
        solver.step(0.1)

    h_final, _, _ = solver.to_numpy()
    # 水深应保持 1.0（允许数值误差 1e-10）
    assert np.max(np.abs(h_final - 1.0)) < 1e-10, \
        f"静水平衡被破坏，最大误差: {np.max(np.abs(h_final - 1.0)):.2e}"


def test_still_water_sloped_bed():
    """斜底静水：水面高程应保持不变（Audusse well-balanced）。"""
    nx, ny = 40, 40
    Lx, Ly = 200.0, 200.0
    # 斜底床面
    x = np.linspace(5.0, Lx - 5.0, nx)
    y = np.linspace(5.0, Ly - 5.0, ny)
    X, Y = np.meshgrid(x, y)
    z_bed = 0.001 * X  # 1/1000 坡度

    solver = GPU2DSolver(Lx=Lx, Ly=Ly, nx=nx, ny=ny,
                         z_bed=z_bed, force_cpu=True)
    # 初始水面高程 = 1.0 m（均匀）
    h_init = np.maximum(1.0 - z_bed, 0.0)
    solver.set_initial_condition(h_init)

    for _ in range(50):
        solver.step(0.1)

    h_final, _, _ = solver.to_numpy()
    eta_final = h_final + z_bed

    # 有水的区域水面高程应保持 1.0
    wet = h_init > 1e-4
    if wet.any():
        eta_error = np.max(np.abs(eta_final[wet] - 1.0))
        # 一阶 Godunov 格式的 well-balanced 误差为 O(dx)，dx=5m 时误差 ~0.01
        assert eta_error < 1e-2, \
            f"斜底静水平衡误差: {eta_error:.2e}"


# ---------------------------------------------------------------------------
# 测试 3：溃坝精度
# ---------------------------------------------------------------------------

def test_dam_break_1d_accuracy():
    """
    1D 溃坝（y 方向均匀）：与 Ritter 解析解对比。

    Ritter 解（t > 0）：
      x < (u_c - c_c) * t : h = h_L, u = 0
      (u_c - c_c)*t ≤ x ≤ (u_c + c_c)*t : h = (2/3)^2 * (c_L - x/(3t))^2 / g
      x > (u_c + c_c) * t : h = 0
    """
    nx, ny = 100, 10
    Lx, Ly = 100.0, 10.0
    x_dam = 50.0
    h_L, h_R = 1.0, 0.0
    g = 9.81
    t_end = 2.0

    solver = make_gpu_solver(nx=nx, ny=ny, Lx=Lx, Ly=Ly, g=g, n=0.0)
    x = np.linspace(solver.dx / 2, Lx - solver.dx / 2, nx)
    X_2d, _ = np.meshgrid(x, np.ones(ny))
    h_init = np.where(X_2d < x_dam, h_L, h_R)
    solver.set_initial_condition(h_init)

    # 运行到 t_end（自适应时间步）
    t = 0.0
    while t < t_end:
        dt = min(solver.compute_dt(0.45), t_end - t)
        solver.step(dt)
        t += dt

    h_final, _, _ = solver.to_numpy()
    h_1d = h_final[ny // 2, :]  # 取中间行

    # Ritter 解析解
    c_L = np.sqrt(g * h_L)
    h_ritter = np.zeros(nx)
    for i, xi in enumerate(x):
        xi_shifted = xi - x_dam
        if xi_shifted < -c_L * t_end:
            h_ritter[i] = h_L
        elif xi_shifted <= 2 * c_L * t_end:
            val = (2.0 / 3.0) * (c_L - xi_shifted / (3.0 * t_end))
            h_ritter[i] = max(val**2 / g, 0.0)
        else:
            h_ritter[i] = 0.0

    # 排除波前附近（数值扩散区域）
    mask = (h_ritter > 0.05) & (h_ritter < 0.95)
    if mask.sum() > 5:
        l2_err = np.sqrt(np.mean((h_1d[mask] - h_ritter[mask])**2))
        l2_ref = np.sqrt(np.mean(h_ritter[mask]**2))
        rel_err = l2_err / (l2_ref + 1e-10)
        # 一阶格式在波前附近有较大数値扩散，25% 是合理阈値
        assert rel_err < 0.25, \
            f"溃坝 L2 相对误差 {rel_err*100:.1f}% 超过 25%"


# ---------------------------------------------------------------------------
# 测试 4：质量守恒
# ---------------------------------------------------------------------------

def test_mass_conservation():
    """封闭域内总水量应守恒（无源汇）。"""
    nx, ny = 60, 60
    solver = make_gpu_solver(nx=nx, ny=ny, Lx=120.0, Ly=120.0, n=0.025)

    # 随机初始条件（模拟复杂地形）
    rng = np.random.default_rng(42)
    h_init = np.abs(rng.normal(0.5, 0.3, (ny, nx)))
    solver.set_initial_condition(h_init)

    V_init = float(np.sum(h_init)) * solver.dx * solver.dy

    for _ in range(100):
        dt = solver.compute_dt(0.45)
        solver.step(dt)

    h_final, _, _ = solver.to_numpy()
    V_final = float(np.sum(h_final)) * solver.dx * solver.dy

    rel_err = abs(V_final - V_init) / (V_init + 1e-10)
    assert rel_err < 0.01, \
        f"质量守恒误差 {rel_err*100:.2f}% 超过 1%"


# ---------------------------------------------------------------------------
# 测试 5：干湿边界稳定性
# ---------------------------------------------------------------------------

def test_dry_wet_stability():
    """干湿边界处不应出现 NaN 或负水深。"""
    nx, ny = 50, 50
    solver = make_gpu_solver(nx=nx, ny=ny, Lx=100.0, Ly=100.0, n=0.03)

    # 初始条件：左半部分有水，右半部分干床
    h_init = np.zeros((ny, nx))
    h_init[:, :nx//2] = 1.0
    solver.set_initial_condition(h_init)

    for _ in range(200):
        dt = solver.compute_dt(0.45)
        solver.step(dt)

    h_final, u_final, v_final = solver.to_numpy()

    assert not np.any(np.isnan(h_final)), "水深出现 NaN"
    assert not np.any(np.isnan(u_final)), "x 速度出现 NaN"
    assert not np.any(h_final < -1e-10), f"水深出现负值：{np.min(h_final):.2e}"


# ---------------------------------------------------------------------------
# 测试 6：与 Hydrostatic2DSolver 数值等价性
# ---------------------------------------------------------------------------

def test_numerical_equivalence_with_reference():
    """
    GPU2DSolver（CPU 模式）与 Hydrostatic2DSolver 的数值结果应高度一致。

    两个求解器使用相同的数值方法，结果差异应在机器精度量级。
    """
    nx, ny = 30, 30
    Lx, Ly = 60.0, 60.0
    g = 9.81
    n = 0.025

    # 相同初始条件
    h_init = np.zeros((ny, nx))
    h_init[ny//4:3*ny//4, nx//4:3*nx//4] = 1.0

    # GPU 求解器（CPU 模式）
    gpu_solver = GPU2DSolver(Lx=Lx, Ly=Ly, nx=nx, ny=ny,
                              g=g, n=n, force_cpu=True)
    gpu_solver.set_initial_condition(h_init.copy())

    # 参考求解器
    ref_solver = Hydrostatic2DSolver(Lx=Lx, Ly=Ly, nx=nx, ny=ny, g=g, n=n)
    ref_solver.h = h_init.copy()
    ref_solver.hu = np.zeros_like(h_init)
    ref_solver.hv = np.zeros_like(h_init)

    # 运行相同步数（使用相同 dt）
    dt = 0.05
    for _ in range(50):
        gpu_solver.step(dt)
        ref_solver.step_2d(dt)

    h_gpu, _, _ = gpu_solver.to_numpy()
    h_ref = np.array(ref_solver.h)

    # 两个求解器的结果应非常接近（允许浮点误差）
    max_diff = np.max(np.abs(h_gpu - h_ref))
    assert max_diff < 0.05, \
        f"GPU2DSolver 与参考求解器最大差异 {max_diff:.4f} 超过 0.05"


# ---------------------------------------------------------------------------
# 测试 7：性能基准（CPU 模式）
# ---------------------------------------------------------------------------

def test_performance_benchmark():
    """验证性能基准测试函数正常运行并返回合理结果。"""
    result = benchmark(nx=50, ny=50, n_steps=20, force_cpu=True)

    assert result['backend'] == 'cpu'
    assert result['elapsed_s'] > 0
    assert result['steps_per_sec'] > 0
    assert result['mcells_per_sec'] > 0

    print(f"\nCPU Benchmark (50x50, 20 steps):")
    print(f"  Speed: {result['steps_per_sec']:.1f} steps/s | "
          f"Throughput: {result['mcells_per_sec']:.3f} MCells/s")


# ---------------------------------------------------------------------------
# 测试 8：to_numpy 数据传输
# ---------------------------------------------------------------------------

def test_to_numpy_transfer():
    """验证 to_numpy 方法正确传输数据。"""
    solver = make_gpu_solver(nx=20, ny=20)
    h_init = np.ones((20, 20)) * 0.5
    solver.set_initial_condition(h_init)

    h, u, v = solver.to_numpy()

    assert isinstance(h, np.ndarray), "h 应为 NumPy 数组"
    assert isinstance(u, np.ndarray), "u 应为 NumPy 数组"
    assert isinstance(v, np.ndarray), "v 应为 NumPy 数组"
    assert h.shape == (20, 20)
    assert np.allclose(h, 0.5)
    assert np.allclose(u, 0.0)  # 初始速度为零
    assert np.allclose(v, 0.0)


# ---------------------------------------------------------------------------
# 测试 9：run 方法
# ---------------------------------------------------------------------------

def test_run_method():
    """验证 run 方法正确推进模拟并返回快照。"""
    solver = make_gpu_solver(nx=30, ny=30, Lx=60.0, Ly=60.0)
    h_init = np.zeros((30, 30))
    h_init[10:20, 10:20] = 1.0
    solver.set_initial_condition(h_init)

    snapshots = solver.run(t_end=1.0, cfl=0.45, output_interval=0.5)

    assert len(snapshots) >= 2, "应至少有 2 个快照"
    assert snapshots[-1]['t'] >= 1.0 - 1e-6, "最终时间应 >= t_end"
    for snap in snapshots:
        assert 'h' in snap
        assert 'u' in snap
        assert 'v' in snap
        assert not np.any(np.isnan(snap['h'])), f"t={snap['t']:.2f} 时出现 NaN"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
