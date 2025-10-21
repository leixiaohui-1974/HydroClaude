import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
from physics.canal import Canal

def example_preissmann_vs_fvm():
    """示例：Preissmann vs FVM对比"""
    print("\n" + "="*60)
    print("示例：Preissmann四点格式 vs 有限体积法对比")
    print("="*60)

    length = 5000.0
    width = 10.0
    n_sections = 51
    dt = 10.0
    n_steps = 100

    print("\n运行Preissmann格式...")
    canal_p = Canal(
        "明渠_Preissmann", 5000, 10000, 100, length,
        method='preissmann', n_sections=n_sections
    )

    history_p = []
    for step in range(n_steps):
        canal_p.update_high_fidelity(dt, {})
        history_p.append(canal_p.state)

    print("\n运行有限体积法...")
    canal_f = Canal(
        "明渠_FVM", 5000, 10000, 100, length,
        method='fvm', n_sections=n_sections
    )

    history_f = []
    for step in range(n_steps):
        canal_f.update_high_fidelity(dt, {})
        history_f.append(canal_f.state)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    time = np.arange(n_steps) * dt / 60

    ax = axes[0, 0]
    levels_p = [s.level for s in history_p]
    levels_f = [s.level for s in history_f]
    ax.plot(time, levels_p, 'b-', linewidth=2, label='Preissmann')
    ax.plot(time, levels_f, 'r--', linewidth=2, label='FVM')
    ax.set_xlabel('时间 (分钟)')
    ax.set_ylabel('平均水位 (m)')
    ax.set_title('水位时间历程')
    ax.legend()
    ax.grid(True, alpha=0.3)

    ax = axes[0, 1]
    flows_p = [s.flow for s in history_p]
    flows_f = [s.flow for s in history_f]
    ax.plot(time, flows_p, 'b-', linewidth=2, label='Preissmann')
    ax.plot(time, flows_f, 'r--', linewidth=2, label='FVM')
    ax.set_xlabel('时间 (分钟)')
    ax.set_ylabel('平均流量 (m³/s)')
    ax.set_title('流量时间历程')
    ax.legend()
    ax.grid(True, alpha=0.3)

    ax = axes[1, 0]
    ax.plot(canal_p.x, canal_p.hydraulic_state.h, 'b-', linewidth=2, label='Preissmann')
    ax.plot(canal_f.x, canal_f.hydraulic_state.h, 'r--', linewidth=2, label='FVM')
    ax.set_xlabel('距离 (m)')
    ax.set_ylabel('水深 (m)')
    ax.set_title('水深空间分布（最终时刻）')
    ax.legend()
    ax.grid(True, alpha=0.3)

    ax = axes[1, 1]
    errors = np.array(levels_p) - np.array(levels_f)
    ax.plot(time, errors, 'k-', linewidth=2)
    ax.axhline(y=0, color='r', linestyle='--', alpha=0.5)
    ax.set_xlabel('时间 (分钟)')
    ax.set_ylabel('水位差 (m)')
    rmse = np.sqrt(np.mean(errors**2))
    ax.set_title(f'两种方法差异 (RMSE={rmse:.6f}m)')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('preissmann_vs_fvm.png', dpi=150, bbox_inches='tight')
    print("\n✓ 图表已保存: preissmann_vs_fvm.png")
    print(f"✓ 两种方法的RMSE: {rmse:.6f} m")
    print(f"✓ 最大差异: {np.max(np.abs(errors)):.6f} m")

if __name__ == "__main__":
    example_preissmann_vs_fvm()
