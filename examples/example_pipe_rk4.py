import matplotlib.pyplot as plt
import numpy as np

# Adjust the import path to be relative to the project root
from physics.pipe_hf import PipeHighFidelity

def example_pipe_rk4():
    """示例：管道RK4高精度求解"""
    import matplotlib.pyplot as plt

    print("\n" + "="*60)
    print("示例：管道水击RK4高精度求解")
    print("="*60)

    # 创建管道
    pipe = PipeHighFidelity(
        "管道1", length=3000, diameter=1.0,
        wave_speed=1000, n_sections=51, method='rk4'
    )

    # 仿真：阀门突然关闭
    n_steps = 200
    dt = 0.1
    history = []

    print("\n运行仿真...")
    for step in range(n_steps):
        # 模拟阀门关闭
        if step < 100:
            # Steady state with a constant flow
            bc = {'upstream_pressure': 50.0, 'downstream_flow': 5.0}
        else:
            # Valve slam shut simulation
            bc = {'upstream_pressure': 50.0, 'downstream_flow': 0.05} # Abruptly reduce flow

        state = pipe.step(dt, bc)
        history.append(state)

        if step % 50 == 0:
            print(f"  步数 {step}/{n_steps}")

    # 可视化
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    time = np.arange(n_steps) * dt

    # 平均压力
    ax = axes[0, 0]
    pressures = [s['pressure'] for s in history]
    ax.plot(time, pressures, 'b-', linewidth=2)
    ax.axvline(x=10, color='r', linestyle='--', alpha=0.5, label='阀门关闭')
    ax.set_xlabel('时间 (秒)')
    ax.set_ylabel('压力 (m)')
    ax.set_title('平均压力变化')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 平均流量
    ax = axes[0, 1]
    flows = [s['flow'] for s in history]
    ax.plot(time, flows, 'g-', linewidth=2)
    ax.axvline(x=10, color='r', linestyle='--', alpha=0.5)
    ax.set_xlabel('时间 (秒)')
    ax.set_ylabel('流量 (m³/s)')
    ax.set_title('平均流量变化')
    ax.grid(True, alpha=0.3)

    # 压力分布
    ax = axes[1, 0]
    x, H, Q = pipe.get_profile()
    ax.plot(x, H, 'b-', linewidth=2)
    ax.set_xlabel('距离 (m)')
    ax.set_ylabel('压力水头 (m)')
    ax.set_title('压力空间分布（最终时刻）')
    ax.grid(True, alpha=0.3)

    # 流量分布
    ax = axes[1, 1]
    ax.plot(x, Q, 'g-', linewidth=2)
    ax.set_xlabel('距离 (m)')
    ax.set_ylabel('流量 (m³/s)')
    ax.set_title('流量空间分布（最终时刻）')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('pipe_rk4_waterhammer.png', dpi=150, bbox_inches='tight')
    print("\n✓ 图表已保存: pipe_rk4_waterhammer.png")
    print(f"✓ 最大压力: {np.max(pressures):.2f} m")
    print(f"✓ 压力波动: {np.max(pressures) - np.min(pressures):.2f} m")
