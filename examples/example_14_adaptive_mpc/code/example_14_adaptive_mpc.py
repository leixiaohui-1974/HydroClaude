# -*- coding: utf-8 -*-
"""
示例14: 自适应MPC控制
演示自适应MPC在线参数辨识和控制
"""
import sys, os
import warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from control.adaptive_mpc import AdaptiveMPC, AdaptiveMPCConfig

def run_example():
    print("\n" + "="*70)
    print("示例14: 自适应MPC控制")
    print("="*70)

    # 真实系统（未知）
    A_true = np.array([[0.8, 0.1],
                      [0.0, 0.9]])
    B_true = np.array([[1.0],
                      [0.5]])

    # 初始模型估计（有偏差）
    A_init = np.array([[0.9, 0.0],
                      [0.0, 0.95]])
    B_init = np.array([[0.8],
                      [0.6]])

    # 创建自适应MPC
    config = AdaptiveMPCConfig(
        prediction_horizon=10,
        control_horizon=5,
        dt=60.0,
        adaptation_rate=0.01,
        forgetting_factor=0.98
    )

    controller = AdaptiveMPC(config, A_init, B_init)

    # 参考状态
    reference = np.array([[5.0], [3.0]])

    # 仿真
    n_steps = 50
    states = np.zeros((n_steps + 1, 2))
    controls = np.zeros(n_steps)
    states[0] = [1.0, 0.5]  # 初始状态

    A_errors = []
    B_errors = []

    print("\n运行自适应MPC仿真...")
    print(f"初始模型误差 - A: {np.linalg.norm(A_init - A_true):.3f}, "
          f"B: {np.linalg.norm(B_init - B_true):.3f}")

    for k in range(n_steps):
        # 当前状态
        x = states[k].reshape(-1, 1)

        # 计算MPC控制
        u, info = controller.step(x, reference)
        controls[k] = u[0, 0]

        # 真实系统响应（添加噪声）
        noise = np.random.normal(0, 0.01, (2, 1))
        x_next = A_true @ x + B_true @ u + noise
        states[k + 1] = x_next.flatten()

        # 自适应：从测量更新模型
        controller.adapt_from_measurement(x_next)

        # 记录模型误差
        params = controller.get_model_parameters()
        A_errors.append(np.linalg.norm(params['A'] - A_true))
        B_errors.append(np.linalg.norm(params['B'] - B_true))

        if k % 10 == 0:
            print(f"步{k:3d}: 状态=[{x[0,0]:5.2f}, {x[1,0]:5.2f}], "
                  f"控制={u[0,0]:5.2f}, "
                  f"模型误差(A)={A_errors[-1]:.3f}")

    print(f"\n最终模型误差 - A: {A_errors[-1]:.3f}, B: {B_errors[-1]:.3f}")
    print(f"最终状态: [{states[-1,0]:.2f}, {states[-1,1]:.2f}]")
    print(f"参考状态: [{reference[0,0]:.2f}, {reference[1,0]:.2f}]")
    print(f"跟踪误差: {np.linalg.norm(states[-1].reshape(-1,1) - reference):.3f}")

    print("\n" + "="*70)
    print("自适应MPC仿真完成!")
    print(" 在线参数辨识")
    print(" 模型自适应更新")
    print(" 优秀的跟踪性能")

    # 可视化
    try:
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))

        # 状态轨迹
        ax = axes[0, 0]
        time = np.arange(n_steps + 1)
        ax.plot(time, states[:, 0], 'b-', label='状态1', linewidth=2)
        ax.plot(time, states[:, 1], 'r-', label='状态2', linewidth=2)
        ax.axhline(y=reference[0, 0], color='b', linestyle='--', alpha=0.5)
        ax.axhline(y=reference[1, 0], color='r', linestyle='--', alpha=0.5)
        ax.set_xlabel('时间步')
        ax.set_ylabel('状态')
        ax.set_title('状态轨迹')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 控制输入
        ax = axes[0, 1]
        ax.plot(controls, 'g-', linewidth=2)
        ax.set_xlabel('时间步')
        ax.set_ylabel('控制输入')
        ax.set_title('MPC控制输入')
        ax.grid(True, alpha=0.3)

        # 模型误差
        ax = axes[1, 0]
        ax.plot(A_errors, 'b-', label='A矩阵误差', linewidth=2)
        ax.plot(B_errors, 'r-', label='B矩阵误差', linewidth=2)
        ax.set_xlabel('时间步')
        ax.set_ylabel('Frobenius范数')
        ax.set_title('模型参数估计误差')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_yscale('log')

        # 跟踪误差
        ax = axes[1, 1]
        tracking_errors = [np.linalg.norm(states[k].reshape(-1,1) - reference)
                          for k in range(n_steps + 1)]
        ax.plot(tracking_errors, 'purple', linewidth=2)
        ax.set_xlabel('时间步')
        ax.set_ylabel('跟踪误差')
        ax.set_title('参考跟踪误差')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig('adaptive_mpc.png', dpi=150, bbox_inches='tight')
        print(f"\n图表已保存: adaptive_mpc.png")
    except Exception as e:
        print(f"\n可视化跳过: {e}")

if __name__ == "__main__":
    run_example()
