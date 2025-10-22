"""
检查数值方法的实际收敛性 - 可视化时间序列
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import matplotlib.pyplot as plt
from example_01_canal_stability_test import ImprovedCanalSolver

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def run_and_visualize(method_name):
    """运行并可视化单个方法"""

    # 渠道参数
    solver = ImprovedCanalSolver(
        length=1000.0,
        width=10.0,
        slope=0.0001,
        manning_n=0.025,
        nx=51,
        method=method_name
    )

    # 仿真参数
    dt = 2.0
    step_time = 200.0
    total_time = 600.0
    n_steps = int(total_time / dt)

    # 边界条件函数
    def Q_func(t):
        return 5.0 if t < step_time else 8.0

    def h_func(t):
        return 5.0

    # 记录
    time_list = []
    hu_list = []
    hd_list = []
    Qu_list = []
    Qd_list = []

    # 仿真
    for i in range(n_steps):
        t = i * dt

        Q_up = Q_func(t)
        h_down = h_func(t)

        solver.step(dt, Q_up, h_down)

        time_list.append(t)
        hu_list.append(solver.h[0])
        hd_list.append(solver.h[-1])
        Qu_list.append(solver.Q[0])
        Qd_list.append(solver.Q[-1])

    return np.array(time_list), np.array(hu_list), np.array(hd_list), np.array(Qu_list), np.array(Qd_list)


# 运行三种方法
print("运行三种方法...")
results = {}
for method in ['explicit', 'preissmann', 'hll']:
    print(f"  运行 {method.upper()}...")
    time, hu, hd, Qu, Qd = run_and_visualize(method)
    results[method] = {
        'time': time,
        'hu': hu,
        'hd': hd,
        'Qu': Qu,
        'Qd': Qd
    }

# 绘制对比图
fig, axes = plt.subplots(3, 2, figsize=(16, 12))

methods = ['explicit', 'preissmann', 'hll']
method_names = {
    'explicit': 'EXPLICIT (显式有限差分)',
    'preissmann': 'PREISSMANN (四点隐式)',
    'hll': 'HLL (有限体积)'
}

for idx, method in enumerate(methods):
    data = results[method]

    # 上游水位
    ax = axes[idx, 0]
    ax.plot(data['time'], data['hu'], 'b-', linewidth=1.5, label='上游水位')
    ax.axvline(x=200, color='r', linestyle='--', alpha=0.5, label='阶跃时刻')
    ax.set_xlabel('时间 (s)', fontsize=11)
    ax.set_ylabel('水位 (m)', fontsize=11)
    ax.set_title(f'{method_names[method]} - 上游水位', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()

    # 检查是否有锯齿
    if len(data['hu']) > 50:
        last_100 = data['hu'][-100:]
        variation = np.std(last_100)
        mean_val = np.mean(last_100)
        if mean_val > 0:
            relative_std = variation / mean_val * 100
            ax.text(0.02, 0.98, f'后100步变异系数: {relative_std:.2f}%',
                   transform=ax.transAxes, va='top', fontsize=9,
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # 下游流量
    ax = axes[idx, 1]
    ax.plot(data['time'], data['Qd'], 'g-', linewidth=1.5, label='下游流量')
    ax.axvline(x=200, color='r', linestyle='--', alpha=0.5, label='阶跃时刻')
    ax.set_xlabel('时间 (s)', fontsize=11)
    ax.set_ylabel('流量 (m³/s)', fontsize=11)
    ax.set_title(f'{method_names[method]} - 下游流量', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()

    # 检查是否有锯齿
    if len(data['Qd']) > 50:
        last_100 = data['Qd'][-100:]
        variation = np.std(last_100)
        mean_val = np.mean(last_100)
        if mean_val > 0:
            relative_std = variation / mean_val * 100
            ax.text(0.02, 0.98, f'后100步变异系数: {relative_std:.2f}%',
                   transform=ax.transAxes, va='top', fontsize=9,
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.tight_layout()
plt.savefig('reports/figures/convergence_check.png', dpi=150, bbox_inches='tight')
print("\n保存图片到: reports/figures/convergence_check.png")

# 打印详细分析
print("\n" + "="*80)
print("收敛性详细分析")
print("="*80)

for method in methods:
    data = results[method]
    print(f"\n{method_names[method]}:")
    print(f"{'='*60}")

    # 最后100步的统计
    hu_last = data['hu'][-100:]
    hd_last = data['hd'][-100:]
    Qu_last = data['Qu'][-100:]
    Qd_last = data['Qd'][-100:]

    print(f"\n上游水位 (最后100步):")
    print(f"  均值: {np.mean(hu_last):.4f} m")
    print(f"  标准差: {np.std(hu_last):.4f} m")
    print(f"  变异系数: {np.std(hu_last)/np.mean(hu_last)*100:.3f}%")
    print(f"  范围: [{np.min(hu_last):.4f}, {np.max(hu_last):.4f}] m")

    print(f"\n下游流量 (最后100步):")
    print(f"  均值: {np.mean(Qd_last):.4f} m³/s")
    print(f"  标准差: {np.std(Qd_last):.4f} m³/s")
    print(f"  变异系数: {np.std(Qd_last)/np.mean(Qd_last)*100:.3f}%")
    print(f"  范围: [{np.min(Qd_last):.4f}, {np.max(Qd_last):.4f}] m³/s")

    # 判断是否收敛
    hu_cv = np.std(hu_last)/np.mean(hu_last)*100
    Qd_cv = np.std(Qd_last)/np.mean(Qd_last)*100

    if hu_cv < 1.0 and Qd_cv < 1.0:
        print(f"\n✅ 收敛良好 (变异系数 < 1%)")
    elif hu_cv < 5.0 and Qd_cv < 5.0:
        print(f"\n⚠️  基本收敛 (变异系数 < 5%)")
    else:
        print(f"\n❌ 未收敛或有明显振荡 (变异系数 >= 5%)")

print("\n" + "="*80)
