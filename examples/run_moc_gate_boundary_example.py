import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

from actuator.gate import Gate
from physics.canal import Canal
from sil_platform.platform import SILTestPlatform


def example_moc_gate_boundary():
    """示例：MOC闸门边界处理测试"""
    print("\n" + "="*60)
    print("示例1: MOC闸门边界处理验证")
    print("="*60)

    # 创建系统：渠道 - 闸门 - 渠道
    canal1 = Canal("上游渠道", 5000, 10000, 100, 5000, n_sections=11)
    gate = Gate("闸门1", width=5.0, opening=2.0)
    canal2 = Canal("下游渠道", 4000, 9000, 100, 4000, n_sections=11)

    # 建立拓扑
    components = [canal1, gate, canal2]

    # 高保真模式
    platform = SILTestPlatform(plant_mode='high_fidelity')
    platform.setup(components)

    # 简单控制
    def step_control(time):
        # 500秒时改变闸门开度
        if time < 500:
            return {'闸门1': 2.0}
        else:
            return {'闸门1': 1.0}

    # 运行测试
    history = platform.run_test(duration=1000, dt=10, control_func=step_control)

    # 可视化
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    time = np.array(history['time'])

    # 上游渠道水深分布
    ax = axes[0, 0]
    canal1_obj = platform.plant_simulator.components['上游渠道']
    for i in [0, 5, 10]:
        depths = [s['上游渠道'].level for s in history['plant_states']]
        ax.plot(time, depths, label=f'节点{i}')
    ax.set_ylabel('水深 (m)')
    ax.set_title('上游渠道水深分布（MOC）')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 下游渠道水深
    ax = axes[0, 1]
    ax.plot(time, [s['下游渠道'].level for s in history['plant_states']], 'b-', linewidth=2)
    ax.set_ylabel('水深 (m)')
    ax.set_title('下游渠道平均水深')
    ax.grid(True, alpha=0.3)

    # 闸门流量
    ax = axes[1, 0]
    flows_up = [s['上游渠道'].flow for s in history['plant_states']]
    flows_down = [s['下游渠道'].flow for s in history['plant_states']]
    ax.plot(time, flows_up, 'b-', linewidth=2, label='上游')
    ax.plot(time, flows_down, 'r-', linewidth=2, label='下游')
    ax.set_xlabel('时间 (s)')
    ax.set_ylabel('流量 (m³/s)')
    ax.set_title('边界流量')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 闸门开度
    ax = axes[1, 1]
    openings = [c.get('闸门1', 2.0) for c in history['controls']]
    ax.plot(time, openings, 'g-', linewidth=2)
    ax.set_xlabel('时间 (s)')
    ax.set_ylabel('开度 (m)')
    ax.set_title('闸门开度控制')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('moc_gate_boundary.png', dpi=100, bbox_inches='tight')
    print("✓ 图表已保存: moc_gate_boundary.png")

if __name__ == "__main__":
    example_moc_gate_boundary()
