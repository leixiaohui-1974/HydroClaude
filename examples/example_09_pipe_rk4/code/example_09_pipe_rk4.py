# -*- coding: utf-8 -*-
import sys
import warnings
warnings.filterwarnings("ignore")
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
from physics.pipe import Pipe

def example_pipe_rk4():
    """示例：管道RK4高精度求解"""
    print("\n" + "="*60)
    print("示例：管道水击RK4高精度求解")
    print("="*60)

    pipe = Pipe(
        "管道1", length=3000, diameter=1.0,
        wave_speed=1000, n_sections=51, method='rk4'
    )

    n_steps = 200
    dt = 0.1
    history = []

    print("\n运行仿真...")
    for step in range(n_steps):
        if step < 100:
            inputs = {'downstream_flow': 5.0}
        else:
            inputs = {'downstream_flow': 0.5}

        state = pipe.update_high_fidelity(dt, inputs)
        history.append(state)

        if step % 50 == 0:
            print(f"  步数 {step}/{n_steps}")

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    time = np.arange(n_steps) * dt

    ax = axes[0, 0]
    pressures = [s.pressure for s in history]
    ax.plot(time, pressures, 'b-', linewidth=2)
    ax.axvline(x=10, color='r', linestyle='--', alpha=0.5, label='阀门关闭')
    ax.set_xlabel('时间 (秒)')
    ax.set_ylabel('压力 (m)')
    ax.set_title('平均压力变化')
    ax.legend()
    ax.grid(True, alpha=0.3)

    ax = axes[0, 1]
    flows = [s.flow for s in history]
    ax.plot(time, flows, 'g-', linewidth=2)
    ax.axvline(x=10, color='r', linestyle='--', alpha=0.5)
    ax.set_xlabel('时间 (秒)')
    ax.set_ylabel('流量 (m^3/s)')
    ax.set_title('平均流量变化')
    ax.grid(True, alpha=0.3)

    ax = axes[1, 0]
    ax.plot(pipe.x, pipe.hydraulic_state.P, 'b-', linewidth=2)
    ax.set_xlabel('距离 (m)')
    ax.set_ylabel('压力水头 (m)')
    ax.set_title('压力空间分布（最终时刻）')
    ax.grid(True, alpha=0.3)

    ax = axes[1, 1]
    ax.plot(pipe.x, pipe.hydraulic_state.Q, 'g-', linewidth=2)
    ax.set_xlabel('距离 (m)')
    ax.set_ylabel('流量 (m^3/s)')
    ax.set_title('流量空间分布（最终时刻）')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('pipe_rk4_waterhammer.png', dpi=150, bbox_inches='tight')
    print("\n 图表已保存: pipe_rk4_waterhammer.png")
    print(f" 最大压力: {np.max(pressures):.2f} m")
    print(f" 压力波动: {np.max(pressures) - np.min(pressures):.2f} m")

if __name__ == "__main__":
    example_pipe_rk4()
