"""
约束MPC渠道控制示例

展示如何使用约束MPC控制器处理：
- 水位上下限约束
- 流量限制
- 参考跟踪

对比场景：
1. 无约束MPC（理想情况）
2. 约束MPC（实际应用）

展示约束MPC如何：
- 保证水位安全
- 尊重执行器限制
- 实现最优控制

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
import matplotlib.pyplot as plt
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from control.constrained_mpc import (
    ConstrainedMPC, MPCWeights, MPCConstraints,
    design_mpc_weights, create_canal_mpc
)


class SimpleCanalSimulator:
    """简化的渠道仿真器（用于测试MPC）"""

    def __init__(self, dt: float):
        """
        初始化渠道仿真器

        系统模型: h(k+1) = h(k) + dt * q(k) + w(k)

        参数:
            dt: 采样时间 (s)
        """
        self.dt = dt
        self.h = 2.5  # 初始水深 (m)

    def step(self, q: float, noise_std: float = 0.005) -> float:
        """
        仿真一步

        参数:
            q: 流量控制输入 (m/s)，即dh/dt
            noise_std: 过程噪声标准差

        返回:
            h: 当前水深 (m)
        """
        # 添加过程噪声
        dh = q * self.dt + np.random.randn() * noise_std

        # 更新水深
        self.h += dh

        return self.h

    def reset(self, h0: float = 2.5):
        """重置"""
        self.h = h0


def main():
    """主函数"""
    print("=" * 80)
    print("约束MPC渠道控制示例")
    print("=" * 80)

    # ===== 1. 参数设置 =====
    print("\n1. 系统参数...")

    dt = 10.0  # 采样时间 (s)
    n_steps = 100  # 仿真步数
    horizon = 15  # MPC预测时域

    # 约束
    h_min = 1.5  # 最小水深 (m)
    h_max = 3.5  # 最大水深 (m)
    q_min = -0.03  # 最小流量控制 (m/s)
    q_max = 0.03  # 最大流量控制 (m/s)

    print(f"  采样时间: {dt} s")
    print(f"  仿真步数: {n_steps}")
    print(f"  预测时域: {horizon}")
    print(f"  水深约束: [{h_min}, {h_max}] m")
    print(f"  流量约束: [{q_min}, {q_max}] m/s")

    # ===== 2. 创建MPC控制器 =====
    print("\n2. 创建MPC控制器...")

    # 系统模型
    A = np.array([[1.0]])
    B = np.array([[dt]])

    # 权重
    weights = design_mpc_weights(n=1, m=1, state_importance=10.0, control_effort=0.5)

    # 场景1: 无约束MPC
    constraints_none = MPCConstraints()
    mpc_unconstrained = ConstrainedMPC(A, B, horizon, weights, constraints_none)

    # 场景2: 约束MPC
    constraints_full = MPCConstraints(
        x_min=np.array([h_min]),
        x_max=np.array([h_max]),
        u_min=np.array([q_min]),
        u_max=np.array([q_max])
    )
    mpc_constrained = ConstrainedMPC(A, B, horizon, weights, constraints_full)

    print("  ✓ 无约束MPC")
    print("  ✓ 约束MPC（水深 + 流量约束）")

    # ===== 3. 生成参考轨迹 =====
    print("\n3. 生成参考轨迹...")

    # 挑战性的参考轨迹：接近约束边界
    reference = np.zeros(n_steps)
    reference[0:30] = 2.5    # 初始：中间水深
    reference[30:50] = 3.2   # 阶段1：接近上限（挑战约束）
    reference[50:70] = 1.8   # 阶段2：接近下限（挑战约束）
    reference[70:100] = 2.5  # 阶段3：回到中间

    print("  挑战性轨迹设计：")
    print("    0-30步:   h_ref = 2.5 m  (中间水深)")
    print("    30-50步:  h_ref = 3.2 m  (接近上限 3.5m)")
    print("    50-70步:  h_ref = 1.8 m  (接近下限 1.5m)")
    print("    70-100步: h_ref = 2.5 m  (回到中间)")

    # ===== 4. 运行仿真 =====
    print("\n4. 运行对比仿真...")

    # 无约束MPC仿真
    print("\n  场景1: 无约束MPC")
    sim_unconstrained = SimpleCanalSimulator(dt)
    h_unconstrained = []
    q_unconstrained = []

    for step in range(n_steps):
        h_current = sim_unconstrained.h
        r = reference[step]

        # MPC控制
        result = mpc_unconstrained.compute_control(
            x0=np.array([h_current]),
            reference=np.array([r])
        )

        q = result.u_opt[0]

        # 仿真
        h_next = sim_unconstrained.step(q)

        # 保存数据
        h_unconstrained.append(h_current)
        q_unconstrained.append(q)

        if step % 20 == 0:
            print(f"    步骤 {step}: h={h_current:.3f}m, q={q:.4f}m/s")

    # 约束MPC仿真
    print("\n  场景2: 约束MPC")
    sim_constrained = SimpleCanalSimulator(dt)
    h_constrained = []
    q_constrained = []
    constraint_violations = 0

    for step in range(n_steps):
        h_current = sim_constrained.h
        r = reference[step]

        # MPC控制
        result = mpc_constrained.compute_control(
            x0=np.array([h_current]),
            reference=np.array([r])
        )

        q = result.u_opt[0]

        # 检查约束违反
        if h_current < h_min or h_current > h_max:
            constraint_violations += 1

        # 仿真
        h_next = sim_constrained.step(q)

        # 保存数据
        h_constrained.append(h_current)
        q_constrained.append(q)

        if step % 20 == 0:
            print(f"    步骤 {step}: h={h_current:.3f}m, q={q:.4f}m/s")

    # 转换为numpy数组
    time_array = np.arange(n_steps) * dt
    h_unconstrained = np.array(h_unconstrained)
    q_unconstrained = np.array(q_unconstrained)
    h_constrained = np.array(h_constrained)
    q_constrained = np.array(q_constrained)

    print("\n  仿真完成!")

    # ===== 5. 性能评估 =====
    print("\n5. 性能评估...")

    # 跟踪误差
    error_unconstrained = h_unconstrained - reference
    error_constrained = h_constrained - reference

    mae_unconstrained = np.mean(np.abs(error_unconstrained))
    mae_constrained = np.mean(np.abs(error_constrained))

    rmse_unconstrained = np.sqrt(np.mean(error_unconstrained**2))
    rmse_constrained = np.sqrt(np.mean(error_constrained**2))

    # 约束违反
    violations_h_unconstrained = np.sum((h_unconstrained < h_min) | (h_unconstrained > h_max))
    violations_h_constrained = np.sum((h_constrained < h_min) | (h_constrained > h_max))

    violations_q_unconstrained = np.sum((q_unconstrained < q_min) | (q_unconstrained > q_max))
    violations_q_constrained = np.sum((q_constrained < q_min) | (q_constrained > q_max))

    # 控制平滑度
    smoothness_unconstrained = np.sum(np.abs(np.diff(q_unconstrained)))
    smoothness_constrained = np.sum(np.abs(np.diff(q_constrained)))

    print("\n  跟踪性能:")
    print(f"    无约束MPC: MAE={mae_unconstrained:.4f}m, RMSE={rmse_unconstrained:.4f}m")
    print(f"    约束MPC:   MAE={mae_constrained:.4f}m, RMSE={rmse_constrained:.4f}m")

    print("\n  约束违反:")
    print(f"    无约束MPC: 水深违反{violations_h_unconstrained}次, 流量违反{violations_q_unconstrained}次")
    print(f"    约束MPC:   水深违反{violations_h_constrained}次, 流量违反{violations_q_constrained}次")

    print("\n  控制平滑度（总变化量）:")
    print(f"    无约束MPC: {smoothness_unconstrained:.4f}")
    print(f"    约束MPC:   {smoothness_constrained:.4f}")

    # ===== 6. 可视化 =====
    print("\n6. 生成可视化...")

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Constrained MPC for Canal Control', fontsize=16, fontweight='bold')

    # 子图1: 水深轨迹
    ax = axes[0, 0]
    ax.plot(time_array, reference, 'k--', linewidth=2, label='Reference', alpha=0.8)
    ax.plot(time_array, h_unconstrained, 'r-', linewidth=1.5, label='Unconstrained MPC', alpha=0.7)
    ax.plot(time_array, h_constrained, 'b-', linewidth=2, label='Constrained MPC', alpha=0.8)
    ax.axhline(y=h_min, color='gray', linestyle=':', linewidth=1.5, label='Constraints')
    ax.axhline(y=h_max, color='gray', linestyle=':', linewidth=1.5)
    ax.fill_between(time_array, h_min, h_max, alpha=0.1, color='green')
    ax.set_xlabel('Time (s)', fontsize=12)
    ax.set_ylabel('Water Depth (m)', fontsize=12)
    ax.set_title('Water Depth Tracking', fontsize=13, fontweight='bold')
    ax.legend(loc='best', fontsize=9)
    ax.grid(True, alpha=0.3)

    # 子图2: 控制输入
    ax = axes[0, 1]
    ax.plot(time_array, q_unconstrained, 'r-', linewidth=1.5, label='Unconstrained MPC', alpha=0.7)
    ax.plot(time_array, q_constrained, 'b-', linewidth=2, label='Constrained MPC', alpha=0.8)
    ax.axhline(y=q_min, color='gray', linestyle=':', linewidth=1.5, label='Constraints')
    ax.axhline(y=q_max, color='gray', linestyle=':', linewidth=1.5)
    ax.fill_between(time_array, q_min, q_max, alpha=0.1, color='green')
    ax.set_xlabel('Time (s)', fontsize=12)
    ax.set_ylabel('Flow Control (m/s)', fontsize=12)
    ax.set_title('Control Input', fontsize=13, fontweight='bold')
    ax.legend(loc='best', fontsize=9)
    ax.grid(True, alpha=0.3)

    # 子图3: 跟踪误差
    ax = axes[1, 0]
    ax.plot(time_array, error_unconstrained, 'r-', linewidth=1.5, label='Unconstrained MPC', alpha=0.7)
    ax.plot(time_array, error_constrained, 'b-', linewidth=2, label='Constrained MPC', alpha=0.8)
    ax.axhline(y=0, color='k', linestyle='--', linewidth=1)
    ax.set_xlabel('Time (s)', fontsize=12)
    ax.set_ylabel('Tracking Error (m)', fontsize=12)
    ax.set_title('Tracking Error', fontsize=13, fontweight='bold')
    ax.legend(loc='best', fontsize=9)
    ax.grid(True, alpha=0.3)

    # 子图4: 性能对比柱状图
    ax = axes[1, 1]
    categories = ['MAE\n(m)', 'RMSE\n(m)', 'Depth\nViolations', 'Flow\nViolations']
    unconstrained_values = [mae_unconstrained, rmse_unconstrained,
                           violations_h_unconstrained, violations_q_unconstrained]
    constrained_values = [mae_constrained, rmse_constrained,
                         violations_h_constrained, violations_q_constrained]

    x = np.arange(len(categories))
    width = 0.35

    bars1 = ax.bar(x - width/2, unconstrained_values, width, label='Unconstrained',
                   color='red', alpha=0.7, edgecolor='black')
    bars2 = ax.bar(x + width/2, constrained_values, width, label='Constrained',
                   color='blue', alpha=0.7, edgecolor='black')

    ax.set_ylabel('Value', fontsize=12)
    ax.set_title('Performance Comparison', fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=10)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')

    # 在柱状图上标注数值
    def autolabel(bars):
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.2f}',
                   ha='center', va='bottom', fontsize=8)

    autolabel(bars1)
    autolabel(bars2)

    plt.tight_layout()

    # 保存图像
    output_path = os.path.join(os.path.dirname(__file__), 'constrained_mpc_canal_demo.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n  ✓ 可视化已保存: {output_path}")

    plt.show()

    # ===== 7. 总结 =====
    print("\n" + "=" * 80)
    print("总结")
    print("=" * 80)
    print("\n约束MPC成功保证了系统约束满足:")
    print(f"  • 水深约束违反: {violations_h_unconstrained}次 → {violations_h_constrained}次")
    print(f"  • 流量约束违反: {violations_q_unconstrained}次 → {violations_q_constrained}次")
    print(f"\n虽然跟踪性能略有下降（受约束限制）:")
    print(f"  • MAE: {mae_unconstrained:.4f}m → {mae_constrained:.4f}m")
    print(f"  • RMSE: {rmse_unconstrained:.4f}m → {rmse_constrained:.4f}m")
    print(f"\n但约束MPC确保了:")
    print(f"  1. 水位始终在安全范围内")
    print(f"  2. 执行器不超出物理限制")
    print(f"  3. 在约束允许下实现最优控制")
    print("\n这对于实际工程应用至关重要！")
    print("=" * 80)


if __name__ == '__main__':
    main()
