import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

from actuator.gate import Gate
from physics.canal import Canal
from physics.tank import Tank
from sil_platform.platform import SILTestPlatform


def example_mode_comparison():
    """示例：高保真vs降阶模式对比"""
    print("\n" + "="*60)
    print("示例2: 高保真 vs 降阶模式对比")
    print("="*60)

    # 创建相同的系统
    def create_system():
        canal = Canal("明渠", 5000, 10000, 100, 3000, n_sections=11)
        gate = Gate("闸门", width=5.0, opening=2.0)
        tank = Tank("水池", 1000, 5000, 100)
        return [canal, gate, tank]

    # 高保真测试
    platform_hf = SILTestPlatform(plant_mode='high_fidelity')
    platform_hf.setup(create_system())

    def simple_control(time):
        return {'闸门': 2.0}

    history_hf = platform_hf.run_test(duration=1800, dt=30, control_func=simple_control)

    # 降阶测试
    platform_ro = SILTestPlatform(plant_mode='reduced')
    platform_ro.setup(create_system())
    history_ro = platform_ro.run_test(duration=1800, dt=30, control_func=simple_control)

    # 对比可视化
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    time = np.array(history_hf['time']) / 60  # 转为分钟

    # 明渠水位
    ax = axes[0, 0]
    levels_hf = [s['明渠'].level for s in history_hf['plant_states']]
    levels_ro = [s['明渠'].level for s in history_ro['plant_states']]
    ax.plot(time, levels_hf, 'b-', linewidth=2, label='高保真')
    ax.plot(time, levels_ro, 'r--', linewidth=2, label='降阶')
    ax.set_ylabel('水位 (m)')
    ax.set_title('明渠水位对比')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 水池水位
    ax = axes[0, 1]
    tank_hf = [s['水池'].level for s in history_hf['plant_states']]
    tank_ro = [s['水池'].level for s in history_ro['plant_states']]
    ax.plot(time, tank_hf, 'b-', linewidth=2, label='高保真')
    ax.plot(time, tank_ro, 'r--', linewidth=2, label='降阶')
    ax.set_ylabel('水位 (m)')
    ax.set_title('水池水位对比')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 误差分析
    ax = axes[1, 0]
    errors = np.array(levels_hf) - np.array(levels_ro)
    ax.plot(time, errors, 'k-', linewidth=2)
    ax.axhline(y=0, color='r', linestyle='--', alpha=0.5)
    ax.set_xlabel('时间 (分钟)')
    ax.set_ylabel('误差 (m)')
    ax.set_title(f'模型误差 (RMSE={np.sqrt(np.mean(errors**2)):.4f}m)')
    ax.grid(True, alpha=0.3)

    # 模式说明
    ax = axes[1, 1]
    ax.text(0.1, 0.8, '高保真模式:', fontsize=12, fontweight='bold')
    ax.text(0.1, 0.7, '  • Saint-Venant方程', fontsize=10)
    ax.text(0.1, 0.6, '  • MOC特征线法', fontsize=10)
    ax.text(0.1, 0.5, '  • 完整内边界处理', fontsize=10)
    ax.text(0.1, 0.35, '降阶模式:', fontsize=12, fontweight='bold')
    ax.text(0.1, 0.25, '  • 积分延迟模型', fontsize=10)
    ax.text(0.1, 0.15, '  • 集总参数', fontsize=10)
    ax.text(0.1, 0.05, '  • 快速计算', fontsize=10)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    plt.tight_layout()
    plt.savefig('mode_comparison.png', dpi=100, bbox_inches='tight')
    print("✓ 图表已保存: mode_comparison.png")

if __name__ == "__main__":
    example_mode_comparison()
