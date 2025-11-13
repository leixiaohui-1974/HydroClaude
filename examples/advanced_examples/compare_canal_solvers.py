# -*- coding: utf-8 -*-
"""
对比不同Saint-Venant求解器的精度

测试三种求解方法
1. MOC (Method of Characteristics) - 特征线法
2. Preissmann - 四点隐式格式
3. FVM (Finite Volume Method) - 有限体积法

测试场景
- 简单的流量平衡测试
- 验证质量守恒
- 对比数值精度

作者HydroClaude Team
日期2025-10-24
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive mode
import matplotlib.pyplot as plt
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from physics.canal import Canal


def test_solver(method: str, dt: float = 10.0, n_steps: int = 50):
    """
    测试指定求解器

    Args:
        method: 'moc', 'preissmann', 或 'fvm'
        dt: 时间步长
        n_steps: 步数
    """
    # 创建Canal
    canal = Canal(
        name=f"test_{method}",
        volume_min=0.0,
        volume_max=1000 * 10 * 10,
        area=10 * 2.5,
        length=1000.0,
        slope=0.001,
        n_sections=51,
        method=method,
        manning_n=0.025,
        width=10.0,
        initial_depth=2.5,
        initial_flow=20.0,
        h_max=10.0  # 增加上限避免约束
    )

    # 测试参数
    Q_in = 22.0   # 入流
    Q_out = 20.0  # 出流

    # 记录数据
    time_hist = []
    h_upstream = []
    h_downstream = []
    h_mid = []
    volume_hist = []

    initial_volume = np.mean(canal.hydraulic_state.h) * 10 * 1000

    for k in range(n_steps):
        t = k * dt

        # 更新
        if method == 'moc':
            inputs = {'Q_in': Q_in, 'Q_out': Q_out}
        elif method == 'preissmann':
            inputs = {
                'upstream_flow': Q_in,
                'downstream_flow': Q_out
            }
        elif method == 'fvm':
            inputs = {}  # FVM可能有不同的接口

        try:
            canal.update_high_fidelity(dt, inputs)
        except Exception as e:
            print(f"  [X] {method}在t={t}s失败: {e}")
            return None

        # 记录
        time_hist.append(t)
        h_upstream.append(canal.hydraulic_state.h[0])
        h_downstream.append(canal.hydraulic_state.h[-1])
        h_mid.append(canal.hydraulic_state.h[len(canal.hydraulic_state.h)//2])

        # 计算总体积
        current_volume = np.mean(canal.hydraulic_state.h) * 10 * 1000
        volume_hist.append(current_volume)

    # 最终体积变化
    volume_added = (Q_in - Q_out) * dt * n_steps
    expected_volume = initial_volume + volume_added
    actual_volume = volume_hist[-1]
    volume_error = abs(actual_volume - expected_volume)
    volume_error_pct = volume_error / volume_added * 100 if volume_added > 0 else 0

    # 理论水位变化
    area_total = 10 * 1000
    expected_delta_h = volume_added / area_total
    actual_delta_h = np.mean(canal.hydraulic_state.h) - 2.5
    h_error = abs(actual_delta_h - expected_delta_h)
    h_error_pct = h_error / expected_delta_h * 100 if expected_delta_h > 0 else 0

    result = {
        'method': method,
        'time': np.array(time_hist),
        'h_upstream': np.array(h_upstream),
        'h_downstream': np.array(h_downstream),
        'h_mid': np.array(h_mid),
        'volume': np.array(volume_hist),
        'expected_delta_h': expected_delta_h,
        'actual_delta_h': actual_delta_h,
        'h_error': h_error,
        'h_error_pct': h_error_pct,
        'volume_error_pct': volume_error_pct,
        'final_h_profile': canal.hydraulic_state.h.copy(),
        'final_Q_profile': canal.hydraulic_state.Q.copy(),
        'x': canal.x
    }

    return result


def main():
    print("="*80)
    print("Saint-Venant求解器精度对比")
    print("="*80)

    print("\n测试配置")
    print("  - 渠道长度: 1000m")
    print("  - 渠道宽度: 10m")
    print("  - 初始水深: 2.5m")
    print("  - 入流: 22 m^3/s")
    print("  - 出流: 20 m^3/s")
    print("  - 净入流: 2 m^3/s")
    print("  - 仿真时间: 500s")
    print("  - 理论h: 0.100m")

    methods = ['preissmann']  # Only preissmann is supported by Canal class
    results = {}

    for method in methods:
        print(f"\n{'='*80}")
        print(f"测试 {method.upper()} 求解器")
        print(f"{'='*80}")
        result = test_solver(method)
        if result:
            results[method] = result
            print(f"  [OK] 测试完成")
            print(f"     理论h: {result['expected_delta_h']:.4f}m")
            print(f"     实际h: {result['actual_delta_h']:.4f}m")
            print(f"     误差: {result['h_error']:.4f}m ({result['h_error_pct']:.1f}%)")
            print(f"     质量守恒误差: {result['volume_error_pct']:.1f}%")

    # 可视化对比
    if len(results) > 0:
        visualize_comparison(results)
        print(f"\n[OK] 对比图已保存: solver_comparison.png")

    # 排名
    print(f"\n{'='*80}")
    print("求解器精度排名")
    print(f"{'='*80}")
    sorted_results = sorted(results.items(), key=lambda x: x[1]['h_error'])
    for rank, (method, result) in enumerate(sorted_results, 1):
        print(f"  {rank}. {method.upper()}: 误差={result['h_error']*100:.2f}cm ({result['h_error_pct']:.1f}%)")

    print("="*80)


def visualize_comparison(results):
    """可视化对比"""
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))

    # 子图1: 上游水位演化
    ax1 = axes[0, 0]
    for method, result in results.items():
        ax1.plot(result['time'], result['h_upstream'], label=method.upper(), linewidth=2)
    ax1.axhline(2.5, color='gray', linestyle=':', label='Initial')
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Upstream h (m)')
    ax1.set_title('Upstream Water Level')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 子图2: 下游水位演化
    ax2 = axes[0, 1]
    for method, result in results.items():
        ax2.plot(result['time'], result['h_downstream'], label=method.upper(), linewidth=2)
    ax2.axhline(2.5, color='gray', linestyle=':', label='Initial')
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Downstream h (m)')
    ax2.set_title('Downstream Water Level')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 子图3: 中点水位演化
    ax3 = axes[0, 2]
    for method, result in results.items():
        ax3.plot(result['time'], result['h_mid'], label=method.upper(), linewidth=2)
    ax3.axhline(2.5, color='gray', linestyle=':', label='Initial')
    ax3.set_xlabel('Time (s)')
    ax3.set_ylabel('Midpoint h (m)')
    ax3.set_title('Midpoint Water Level')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # 子图4: 最终水位分布
    ax4 = axes[1, 0]
    for method, result in results.items():
        ax4.plot(result['x'], result['final_h_profile'], label=method.upper(), linewidth=2)
    ax4.axhline(2.5, color='gray', linestyle=':', label='Initial')
    ax4.set_xlabel('Distance (m)')
    ax4.set_ylabel('Water Level (m)')
    ax4.set_title('Final Water Level Profile')
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    # 子图5: 最终流量分布
    ax5 = axes[1, 1]
    for method, result in results.items():
        ax5.plot(result['x'], result['final_Q_profile'], label=method.upper(), linewidth=2)
    ax5.axhline(22, color='b', linestyle=':', alpha=0.5)
    ax5.axhline(20, color='r', linestyle=':', alpha=0.5)
    ax5.set_xlabel('Distance (m)')
    ax5.set_ylabel('Flow Rate (m^3/s)')
    ax5.set_title('Final Flow Rate Profile')
    ax5.legend()
    ax5.grid(True, alpha=0.3)

    # 子图6: 精度对比
    ax6 = axes[1, 2]
    methods = list(results.keys())
    errors = [results[m]['h_error']*100 for m in methods]
    expected = [results[m]['expected_delta_h']*100 for m in methods]

    x = np.arange(len(methods))
    width = 0.35

    bars1 = ax6.bar(x - width/2, expected, width, label='Expected h', color='green', alpha=0.6)
    bars2 = ax6.bar(x + width/2, errors, width, label='Error', color='red', alpha=0.6)

    ax6.set_ylabel('Value (cm)')
    ax6.set_xticks(x)
    ax6.set_xticklabels([m.upper() for m in methods])
    ax6.set_title('Accuracy Comparison')
    ax6.legend()
    ax6.grid(True, alpha=0.3, axis='y')

    for bar in bars1:
        height = bar.get_height()
        ax6.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}', ha='center', va='bottom', fontsize=9)
    for bar in bars2:
        height = bar.get_height()
        ax6.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}', ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    plt.savefig('solver_comparison.png', dpi=150, bbox_inches='tight')


if __name__ == "__main__":
    main()
