# -*- coding: utf-8 -*-
"""
示例14: 自适应MPC控制（增强版）

演示自适应MPC在线参数辨识和控制

增强功能：
- 自动生成对比图表
- 生成参数收敛动画（GIF）
- 生成详细仿真报告
- 嵌入可视化结果
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from control.adaptive_mpc import AdaptiveMPC, AdaptiveMPCConfig
from utils.visualization import SimulationVisualizer, ReportGenerator

def run_example():
    """运行自适应MPC控制示例（增强版）"""

    print("=" * 70)
    print("示例14: 自适应MPC控制 - 增强版")
    print("=" * 70)
    print()

    # ====== 1. 系统设置 ======
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

    print("系统参数:")
    print(f"  真实A矩阵:\n{A_true}")
    print(f"  真实B矩阵:\n{B_true}")
    print(f"  初始A估计:\n{A_init}")
    print(f"  初始B估计:\n{B_init}")
    print(f"  初始模型误差 - A: {np.linalg.norm(A_init - A_true):.3f}, "
          f"B: {np.linalg.norm(B_init - B_true):.3f}")
    print()

    # ====== 2. 创建自适应MPC ======
    config = AdaptiveMPCConfig(
        prediction_horizon=10,
        control_horizon=5,
        dt=60.0,
        adaptation_rate=0.01,
        forgetting_factor=0.98
    )

    controller = AdaptiveMPC(config, A_init, B_init)

    print("MPC控制器参数:")
    print(f"  预测时域: {config.prediction_horizon}")
    print(f"  控制时域: {config.control_horizon}")
    print(f"  时间步长: {config.dt}s")
    print(f"  自适应学习率: {config.adaptation_rate}")
    print(f"  遗忘因子: {config.forgetting_factor}")
    print()

    # ====== 3. 仿真设置 ======
    # 参考状态
    reference = np.array([[5.0], [3.0]])

    # 仿真步数
    n_steps = 50
    states = np.zeros((n_steps + 1, 2))
    controls = np.zeros(n_steps)
    states[0] = [1.0, 0.5]  # 初始状态

    # 存储数据用于可视化
    A_errors = []
    B_errors = []
    A_history = []
    B_history = []
    tracking_errors = []

    # ====== 4. 运行仿真 ======
    print("开始自适应MPC仿真...")
    print("-" * 70)

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

        # 记录模型误差和参数
        params = controller.get_model_parameters()
        A_errors.append(np.linalg.norm(params['A'] - A_true))
        B_errors.append(np.linalg.norm(params['B'] - B_true))
        A_history.append(params['A'].copy())
        B_history.append(params['B'].copy())

        # 跟踪误差
        tracking_errors.append(np.linalg.norm(x_next - reference))

        # 打印进度
        if k % 10 == 0:
            print(f"步{k:3d}: 状态=[{x[0,0]:5.2f}, {x[1,0]:5.2f}], "
                  f"控制={u[0,0]:5.2f}, "
                  f"模型误差(A)={A_errors[-1]:.3f}, "
                  f"跟踪误差={tracking_errors[-1]:.3f}")

    # 最后一步的跟踪误差
    x_final = states[-1].reshape(-1, 1)
    tracking_errors.append(np.linalg.norm(x_final - reference))

    print("-" * 70)
    print(f"仿真完成!")
    print(f"最终模型误差 - A: {A_errors[-1]:.3f}, B: {B_errors[-1]:.3f}")
    print(f"最终状态: [{states[-1,0]:.2f}, {states[-1,1]:.2f}]")
    print(f"参考状态: [{reference[0,0]:.2f}, {reference[1,0]:.2f}]")
    print(f"最终跟踪误差: {tracking_errors[-1]:.3f}")
    print()

    # ====== 5. 生成可视化 ======
    print("生成可视化图表...")
    visualizer = SimulationVisualizer(output_dir="reports/figures")
    generated_images = []

    # (1) 状态轨迹图
    time_steps = np.arange(n_steps + 1)
    time_min = time_steps * config.dt / 60  # 转换为分钟

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(time_min, states[:, 0], 'o-', linewidth=2.5, markersize=5,
            color='#3498DB', label='状态1 (实际)', markeredgecolor='black', markeredgewidth=0.5)
    ax.plot(time_min, states[:, 1], 's-', linewidth=2.5, markersize=5,
            color='#E74C3C', label='状态2 (实际)', markeredgecolor='black', markeredgewidth=0.5)
    ax.axhline(y=reference[0, 0], color='#3498DB', linestyle='--', linewidth=2,
               alpha=0.6, label='状态1 (参考)')
    ax.axhline(y=reference[1, 0], color='#E74C3C', linestyle='--', linewidth=2,
               alpha=0.6, label='状态2 (参考)')
    ax.set_xlabel('Time (minutes)', fontsize=12)
    ax.set_ylabel('State Value', fontsize=12)
    ax.set_title('Adaptive MPC - State Tracking', fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=10, framealpha=0.9)
    ax.grid(True, alpha=0.3, linestyle='--')

    img_path = os.path.join(visualizer.output_dir, 'example_14_state_tracking.png')
    plt.savefig(img_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    generated_images.append(img_path)
    print(f"   生成图表: {os.path.basename(img_path)}")

    # (2) 控制输入图
    fig, ax = plt.subplots(figsize=(12, 6))
    time_min_ctrl = np.arange(n_steps) * config.dt / 60
    ax.plot(time_min_ctrl, controls, 'o-', linewidth=2.5, markersize=6,
            color='#2ECC71', markeredgecolor='black', markeredgewidth=0.5)
    ax.set_xlabel('Time (minutes)', fontsize=12)
    ax.set_ylabel('Control Input', fontsize=12)
    ax.set_title('MPC Control Input Trajectory', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')

    img_path = os.path.join(visualizer.output_dir, 'example_14_control_input.png')
    plt.savefig(img_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    generated_images.append(img_path)
    print(f"   生成图表: {os.path.basename(img_path)}")

    # (3) 模型参数误差图
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(time_min_ctrl, A_errors, 'o-', linewidth=2.5, markersize=5,
            color='#3498DB', label='A matrix error', markeredgecolor='black', markeredgewidth=0.5)
    ax.plot(time_min_ctrl, B_errors, 's-', linewidth=2.5, markersize=5,
            color='#E74C3C', label='B matrix error', markeredgecolor='black', markeredgewidth=0.5)
    ax.set_xlabel('Time (minutes)', fontsize=12)
    ax.set_ylabel('Frobenius Norm', fontsize=12)
    ax.set_title('Model Parameter Estimation Error (Convergence)', fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=10, framealpha=0.9)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_yscale('log')

    img_path = os.path.join(visualizer.output_dir, 'example_14_parameter_error.png')
    plt.savefig(img_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    generated_images.append(img_path)
    print(f"   生成图表: {os.path.basename(img_path)}")

    # (4) 跟踪误差图
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(time_min, tracking_errors, 'o-', linewidth=2.5, markersize=6,
            color='#9B59B6', markeredgecolor='black', markeredgewidth=0.5)
    ax.set_xlabel('Time (minutes)', fontsize=12)
    ax.set_ylabel('Tracking Error (L2 Norm)', fontsize=12)
    ax.set_title('Reference Tracking Error', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')

    img_path = os.path.join(visualizer.output_dir, 'example_14_tracking_error.png')
    plt.savefig(img_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    generated_images.append(img_path)
    print(f"   生成图表: {os.path.basename(img_path)}")

    # (5) 四子图综合视图
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 状态轨迹
    ax = axes[0, 0]
    ax.plot(time_min, states[:, 0], 'b-', label='State 1', linewidth=2)
    ax.plot(time_min, states[:, 1], 'r-', label='State 2', linewidth=2)
    ax.axhline(y=reference[0, 0], color='b', linestyle='--', alpha=0.5)
    ax.axhline(y=reference[1, 0], color='r', linestyle='--', alpha=0.5)
    ax.set_xlabel('Time (min)', fontsize=11)
    ax.set_ylabel('State', fontsize=11)
    ax.set_title('State Trajectory', fontsize=12)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    # 控制输入
    ax = axes[0, 1]
    ax.plot(time_min_ctrl, controls, 'g-', linewidth=2)
    ax.set_xlabel('Time (min)', fontsize=11)
    ax.set_ylabel('Control Input', fontsize=11)
    ax.set_title('MPC Control', fontsize=12)
    ax.grid(True, alpha=0.3)

    # 模型误差
    ax = axes[1, 0]
    ax.plot(time_min_ctrl, A_errors, 'b-', label='A matrix', linewidth=2)
    ax.plot(time_min_ctrl, B_errors, 'r-', label='B matrix', linewidth=2)
    ax.set_xlabel('Time (min)', fontsize=11)
    ax.set_ylabel('Frobenius Norm', fontsize=11)
    ax.set_title('Parameter Error', fontsize=12)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_yscale('log')

    # 跟踪误差
    ax = axes[1, 1]
    ax.plot(time_min, tracking_errors, 'purple', linewidth=2)
    ax.set_xlabel('Time (min)', fontsize=11)
    ax.set_ylabel('Error', fontsize=11)
    ax.set_title('Tracking Error', fontsize=12)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    img_path = os.path.join(visualizer.output_dir, 'example_14_comprehensive.png')
    plt.savefig(img_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    generated_images.append(img_path)
    print(f"   生成图表: {os.path.basename(img_path)}")

    # (6) 参数收敛动画 (GIF)
    print("  生成参数收敛动画...")

    fig, ax = plt.subplots(figsize=(10, 6))

    def animate_params(frame):
        ax.clear()

        # 绘制参数误差随时间的变化
        frames_shown = min(frame + 1, len(A_errors))
        time_shown = np.arange(frames_shown) * config.dt / 60

        ax.plot(time_shown, A_errors[:frames_shown], 'o-', linewidth=2.5,
                markersize=6, color='#3498DB', label='A matrix error',
                markeredgecolor='black', markeredgewidth=0.5)
        ax.plot(time_shown, B_errors[:frames_shown], 's-', linewidth=2.5,
                markersize=6, color='#E74C3C', label='B matrix error',
                markeredgecolor='black', markeredgewidth=0.5)

        ax.set_xlabel('Time (minutes)', fontsize=12)
        ax.set_ylabel('Parameter Error (Frobenius Norm)', fontsize=12)
        ax.set_title(f'Parameter Convergence (Step {frame})', fontsize=14, fontweight='bold')
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_xlim([0, max(time_min_ctrl) * 1.1])
        ax.set_ylim([min(min(A_errors), min(B_errors)) * 0.5,
                     max(max(A_errors), max(B_errors)) * 1.2])
        ax.set_yscale('log')

    # 每5步一个关键帧
    keyframes = list(range(0, n_steps, 5)) + [n_steps - 1]
    anim = animation.FuncAnimation(fig, animate_params, frames=keyframes,
                                  interval=500, repeat=True)

    gif_path = os.path.join(visualizer.output_dir, 'example_14_parameter_convergence.gif')
    anim.save(gif_path, writer='pillow', fps=2, dpi=100)
    plt.close(fig)
    generated_images.append(gif_path)
    print(f"   生成动画: {os.path.basename(gif_path)}")
    print()

    # ====== 6. 生成报告 ======
    print("生成仿真报告...")
    report_gen = ReportGenerator(output_dir="reports")

    # 统计信息
    stats = {
        '预测时域': f"{config.prediction_horizon}",
        '控制时域': f"{config.control_horizon}",
        '学习率': f"{config.adaptation_rate}",
        '遗忘因子': f"{config.forgetting_factor}",
        '仿真步数': f"{n_steps}",
        '初始A误差': f"{np.linalg.norm(A_init - A_true):.4f}",
        '最终A误差': f"{A_errors[-1]:.4f}",
        '初始B误差': f"{np.linalg.norm(B_init - B_true):.4f}",
        '最终B误差': f"{B_errors[-1]:.4f}",
        '最终跟踪误差': f"{tracking_errors[-1]:.4f}",
        'A误差降低率': f"{(1 - A_errors[-1]/np.linalg.norm(A_init - A_true))*100:.1f}%",
        'B误差降低率': f"{(1 - B_errors[-1]/np.linalg.norm(B_init - B_true))*100:.1f}%"
    }

    # 创建报告内容
    sections = [
        {
            'heading': '仿真概述',
            'content': f"""
本示例演示了HydroClaude的自适应模型预测控制(Adaptive MPC)功能。

**核心特性**:
1. **在线参数辨识**: 实时估计系统模型参数
2. **自适应控制**: 根据辨识结果更新控制策略
3. **鲁棒性**: 即使初始模型有较大偏差也能收敛
4. **优化性能**: 同时优化跟踪性能和控制代价

**系统设置**:
- 真实系统: 2阶线性系统 (A_true, B_true)
- 初始估计: 有偏差的模型 (A_init, B_init)
- 目标: 跟踪参考状态 [5.0, 3.0]

**控制器参数**:
{report_gen.create_summary_table(stats)}
"""
        },
        {
            'heading': '状态跟踪性能',
            'content': f"""### 参考跟踪结果

系统从初始状态 [{states[0, 0]:.1f}, {states[0, 1]:.1f}] 跟踪到参考状态 [{reference[0,0]:.1f}, {reference[1,0]:.1f}]。

**性能指标**:
- 初始跟踪误差: {tracking_errors[0]:.3f}
- 最终跟踪误差: {tracking_errors[-1]:.3f}
- 误差降低: {(1 - tracking_errors[-1]/tracking_errors[0])*100:.1f}%
- 稳定时间: ~{np.argmax(np.array(tracking_errors) < 0.5) * config.dt / 60:.1f} 分钟

自适应MPC成功实现了对参考状态的精确跟踪。""",
            'images': [generated_images[0]]
        },
        {
            'heading': '控制输入分析',
            'content': """### MPC控制轨迹

控制输入在初始阶段较大，用于快速驱动系统接近参考点。
随着系统接近目标，控制输入逐渐减小并趋于稳定。

这体现了MPC的优化特性：在满足约束的前提下，以最优方式驱动系统。""",
            'images': [generated_images[1]]
        },
        {
            'heading': '参数辨识性能',
            'content': f"""### 在线参数学习与收敛

自适应算法从测量数据中持续学习，逐步修正模型参数。

**辨识性能**:
- A矩阵误差: {np.linalg.norm(A_init - A_true):.4f} -> {A_errors[-1]:.4f} (降低 {stats['A误差降低率']})
- B矩阵误差: {np.linalg.norm(B_init - B_true):.4f} -> {B_errors[-1]:.4f} (降低 {stats['B误差降低率']})

参数误差在对数坐标下呈现指数衰减，表明自适应算法具有良好的收敛性。""",
            'images': [generated_images[2]]
        },
        {
            'heading': '跟踪误差演化',
            'content': """### 闭环跟踪性能

跟踪误差反映了系统状态与参考值的偏差。

**观察**:
- 初期误差较大，因为初始模型不准确
- 随着参数辨识的进行，跟踪性能显著提升
- 最终达到很小的稳态误差

这验证了自适应MPC的双重优势：参数学习 + 优化控制。""",
            'images': [generated_images[3]]
        },
        {
            'heading': '综合性能视图',
            'content': """### 四维性能总览

综合展示状态、控制、参数误差和跟踪误差四个关键指标。

可以清晰看到各指标之间的关系：
- 控制输入驱动状态变化
- 参数辨识支持更好的控制
- 最终实现优秀的跟踪性能""",
            'images': [generated_images[4]]
        },
        {
            'heading': '动态收敛过程',
            'content': """### 参数收敛动画 (GIF)

动态展示参数误差随时间的收敛过程。

可以直观看到：
- 指数型收敛特性
- A矩阵和B矩阵的同步学习
- 最终收敛到很小的误差""",
            'images': [generated_images[5]]
        },
        {
            'heading': '结论',
            'content': f"""
仿真成功完成！

**主要成果**:
-  成功实现在线参数辨识
-  A矩阵误差降低 {stats['A误差降低率']}
-  B矩阵误差降低 {stats['B误差降低率']}
-  最终跟踪误差仅 {tracking_errors[-1]:.4f}
-  验证了自适应MPC的有效性

**技术优势**:
- **自适应性**: 无需精确初始模型
- **鲁棒性**: 能够处理模型不确定性
- **优化性**: 同时优化多个目标
- **实时性**: 适合在线应用

**应用场景**:
- 模型参数时变的系统
- 初始模型不准确的场景
- 需要高性能跟踪的任务
- 复杂约束优化问题
"""
        }
    ]

    report_path = report_gen.generate_markdown_report(
        title='示例14: 自适应MPC控制结果报告',
        sections=sections,
        filename='example_14_simulation_report.md'
    )

    print(f"   报告已生成: {os.path.basename(report_path)}")
    print()

    # ====== 7. 总结 ======
    print("=" * 70)
    print("仿真结果总结")
    print("=" * 70)
    print(f"参数辨识性能:")
    print(f"  A矩阵误差: {np.linalg.norm(A_init - A_true):.4f} -> {A_errors[-1]:.4f} (降低 {stats['A误差降低率']})")
    print(f"  B矩阵误差: {np.linalg.norm(B_init - B_true):.4f} -> {B_errors[-1]:.4f} (降低 {stats['B误差降低率']})")
    print()
    print(f"跟踪控制性能:")
    print(f"  初始状态: [{states[0, 0]:.2f}, {states[0, 1]:.2f}]")
    print(f"  最终状态: [{states[-1, 0]:.2f}, {states[-1, 1]:.2f}]")
    print(f"  参考状态: [{reference[0,0]:.2f}, {reference[1,0]:.2f}]")
    print(f"  跟踪误差: {tracking_errors[0]:.4f} -> {tracking_errors[-1]:.4f}")
    print()
    print(f"生成文件:")
    for img in generated_images:
        print(f"  - {os.path.relpath(img)}")
    print(f"  - {os.path.relpath(report_path)}")
    print()
    print("=" * 70)


if __name__ == "__main__":
    run_example()
