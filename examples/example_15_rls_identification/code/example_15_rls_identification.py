# -*- coding: utf-8 -*-
"""
示例15: RLS参数辨识
演示递推最小二乘在线参数辨识
"""
import sys, os
import warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from identification.rls_identifier import ARXIdentifier

def run_example():
    print("\n" + "="*70)
    print("示例15: RLS参数辨识 - ARX模型")
    print("="*70)

    # 真实系统：ARX(2,2,1)
    # y[k] = 0.8*y[k-1] - 0.3*y[k-2] + 1.5*u[k-1] + 0.7*u[k-2]
    a_true = np.array([0.8, -0.3])
    b_true = np.array([1.5, 0.7])

    print("\n真实系统参数:")
    print(f"  a = {a_true}")
    print(f"  b = {b_true}")

    # 创建ARX辨识器
    identifier = ARXIdentifier(
        na=2,  # 输出阶数
        nb=2,  # 输入阶数
        delay=1,
        forgetting_factor=0.98
    )

    # 生成数据
    n_steps = 200
    u_data = np.random.randn(n_steps) * 0.5  # 随机输入
    y_data = np.zeros(n_steps)

    print("\n生成训练数据...")

    # 系统仿真
    for k in range(2, n_steps):
        y_data[k] = (a_true[0] * y_data[k-1] +
                    a_true[1] * y_data[k-2] +
                    b_true[0] * u_data[k-1] +
                    b_true[1] * u_data[k-2] +
                    np.random.normal(0, 0.01))  # 噪声

    # RLS辨识
    print("运行RLS辨识...")

    a_estimates = []
    b_estimates = []
    errors = []

    for k in range(n_steps):
        result = identifier.update(u_data[k], y_data[k])

        a_estimates.append(result['a_parameters'])
        b_estimates.append(result['b_parameters'])
        errors.append(result['prediction_error'])

        if k in [10, 50, 100, 199]:
            a_est = result['a_parameters']
            b_est = result['b_parameters']
            print(f"\n步{k:3d}:")
            print(f"  a估计 = [{a_est[0]:.3f}, {a_est[1]:.3f}]")
            print(f"  b估计 = [{b_est[0]:.3f}, {b_est[1]:.3f}]")
            print(f"  a误差 = {np.linalg.norm(a_est - a_true):.4f}")
            print(f"  b误差 = {np.linalg.norm(b_est - b_true):.4f}")

    # 最终参数
    a_final = a_estimates[-1]
    b_final = b_estimates[-1]

    print("\n" + "-"*70)
    print("最终辨识结果:")
    print(f"  真实: a={a_true}, b={b_true}")
    print(f"  估计: a=[{a_final[0]:.3f}, {a_final[1]:.3f}], "
          f"b=[{b_final[0]:.3f}, {b_final[1]:.3f}]")
    print(f"  a参数误差: {np.linalg.norm(a_final - a_true):.4f}")
    print(f"  b参数误差: {np.linalg.norm(b_final - b_true):.4f}")

    # 预测测试
    print("\n多步预测测试:")
    y_pred = identifier.predict(u=0.5, steps=10)
    print(f"  未来10步预测: {y_pred[:5]} ...")

    print("\n" + "="*70)
    print("RLS参数辨识完成!")
    print(" 在线递推参数估计")
    print(" 自适应遗忘因子")
    print(" 高精度参数收敛")

    # 可视化
    try:
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))

        # 参数收敛
        ax = axes[0, 0]
        a_est_array = np.array(a_estimates)
        ax.plot(a_est_array[:, 0], label=f'a1 (真值={a_true[0]:.2f})', linewidth=2)
        ax.plot(a_est_array[:, 1], label=f'a2 (真值={a_true[1]:.2f})', linewidth=2)
        ax.axhline(y=a_true[0], color='C0', linestyle='--', alpha=0.5)
        ax.axhline(y=a_true[1], color='C1', linestyle='--', alpha=0.5)
        ax.set_xlabel('迭代次数')
        ax.set_ylabel('参数值')
        ax.set_title('a参数收敛过程')
        ax.legend()
        ax.grid(True, alpha=0.3)

        ax = axes[0, 1]
        b_est_array = np.array(b_estimates)
        ax.plot(b_est_array[:, 0], label=f'b1 (真值={b_true[0]:.2f})', linewidth=2)
        ax.plot(b_est_array[:, 1], label=f'b2 (真值={b_true[1]:.2f})', linewidth=2)
        ax.axhline(y=b_true[0], color='C0', linestyle='--', alpha=0.5)
        ax.axhline(y=b_true[1], color='C1', linestyle='--', alpha=0.5)
        ax.set_xlabel('迭代次数')
        ax.set_ylabel('参数值')
        ax.set_title('b参数收敛过程')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 预测误差
        ax = axes[1, 0]
        ax.plot(np.abs(errors), linewidth=1)
        ax.set_xlabel('迭代次数')
        ax.set_ylabel('预测误差（绝对值）')
        ax.set_title('RLS预测误差')
        ax.grid(True, alpha=0.3)
        ax.set_yscale('log')

        # 输入输出数据
        ax = axes[1, 1]
        time_plot = range(min(100, n_steps))
        ax.plot(time_plot, y_data[:len(time_plot)], 'b-', label='输出y', linewidth=2, alpha=0.7)
        ax.plot(time_plot, u_data[:len(time_plot)], 'r-', label='输入u', linewidth=1, alpha=0.7)
        ax.set_xlabel('时间步')
        ax.set_ylabel('信号值')
        ax.set_title('系统输入输出数据（前100步）')
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig('rls_identification.png', dpi=150, bbox_inches='tight')
        print(f"\n图表已保存: rls_identification.png")
    except Exception as e:
        print(f"\n可视化跳过: {e}")

if __name__ == "__main__":
    run_example()
