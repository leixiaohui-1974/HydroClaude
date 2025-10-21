import matplotlib.pyplot as plt
import numpy as np

# Adjust the import path to be relative to the project root
from physics.canal_hf import CanalHighFidelity

def example_preissmann_vs_fvm():
    """示例：Preissmann vs FVM对比"""
    import matplotlib.pyplot as plt

    print("\n" + "="*60)
    print("示例：Preissmann四点格式 vs 有限体积法对比")
    print("="*60)

    # 系统参数
    length = 5000.0
    width = 10.0
    n_sections = 51
    dt = 10.0
    n_steps = 100

    # Preissmann格式
    print("\n运行Preissmann格式...")
    canal_p = CanalHighFidelity(
        "明渠_Preissmann", length, width, 5000, 10000,
        method='preissmann', n_sections=n_sections
    )

    history_p = []
    for step in range(n_steps):
        # Define boundary conditions for Preissmann.
        # Note: FVM solver in this implementation doesn't use these complex BCs,
        # which might be a source of discrepancy.
        bc_p = {
            'upstream_level': 5.0 + 0.5 * np.sin(2 * np.pi * step / 50),
            'downstream_flow': 5.0
        }
        state = canal_p.step(dt, bc_p)
        history_p.append(state)

    # FVM格式
    print("\n运行有限体积法...")
    canal_f = CanalHighFidelity(
        "明渠_FVM", length, width, 5000, 10000,
        method='fvm', n_sections=n_sections
    )

    history_f = []
    # Set initial upstream boundary for FVM based on the first step of Preissmann's BC
    initial_upstream_level = 5.0 + 0.5 * np.sin(0)
    canal_f.h[0] = initial_upstream_level
    canal_f.A[0] = initial_upstream_level * canal_f.width

    for step in range(n_steps):
        # FVM solver as implemented takes simple boundary conditions,
        # often handled at the flux calculation stage.
        # We will mimic the upstream change by updating the first cell's state.
        upstream_level = 5.0 + 0.5 * np.sin(2 * np.pi * step / 50)
        canal_f.h[0] = upstream_level
        canal_f.A[0] = upstream_level * canal_f.width

        state = canal_f.step(dt, {}) # No complex BC dictionary for FVM solver
        history_f.append(state)

    # 可视化
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    time = np.arange(n_steps) * dt / 60  # 转为分钟

    # 平均水位
    ax = axes[0, 0]
    levels_p = [s['level'] for s in history_p]
    levels_f = [s['level'] for s in history_f]
    ax.plot(time, levels_p, 'b-', linewidth=2, label='Preissmann')
    ax.plot(time, levels_f, 'r--', linewidth=2, label='FVM')
    ax.set_xlabel('时间 (分钟)')
    ax.set_ylabel('平均水位 (m)')
    ax.set_title('水位时间历程')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 平均流量
    ax = axes[0, 1]
    flows_p = [s['flow'] for s in history_p]
    flows_f = [s['flow'] for s in history_f]
    ax.plot(time, flows_p, 'b-', linewidth=2, label='Preissmann')
    ax.plot(time, flows_f, 'r--', linewidth=2, label='FVM')
    ax.set_xlabel('时间 (分钟)')
    ax.set_ylabel('平均流量 (m³/s)')
    ax.set_title('流量时间历程')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 空间分布（最后时刻）
    ax = axes[1, 0]
    x_p, h_p, Q_p = canal_p.get_profile()
    x_f, h_f, Q_f = canal_f.get_profile()
    ax.plot(x_p, h_p, 'b-', linewidth=2, label='Preissmann')
    ax.plot(x_f, h_f, 'r--', linewidth=2, label='FVM')
    ax.set_xlabel('距离 (m)')
    ax.set_ylabel('水深 (m)')
    ax.set_title('水深空间分布（最终时刻）')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 误差分析
    ax = axes[1, 1]
    # Ensure arrays have the same length for comparison
    min_len = min(len(levels_p), len(levels_f))
    errors = np.array(levels_p[:min_len]) - np.array(levels_f[:min_len])
    time_err = time[:min_len]

    ax.plot(time_err, errors, 'k-', linewidth=2)
    ax.axhline(y=0, color='r', linestyle='--', alpha=0.5)
    ax.set_xlabel('时间 (分钟)')
    ax.set_ylabel('水位差 (m)')
    rmse = np.sqrt(np.mean(errors**2)) if len(errors) > 0 else 0
    ax.set_title(f'两种方法差异 (RMSE={rmse:.6f}m)')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('preissmann_vs_fvm.png', dpi=150, bbox_inches='tight')
    print("\n✓ 图表已保存: preissmann_vs_fvm.png")
    if len(errors) > 0:
        print(f"✓ 两种方法的RMSE: {rmse:.6f} m")
        print(f"✓ 最大差异: {np.max(np.abs(errors)):.6f} m")

if __name__ == "__main__":
    try:
        # Add font support for Chinese characters
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
    except:
        print("Warning: Chinese font 'SimHei' not found. Please install it for proper labeling.")

    example_preissmann_vs_fvm()
