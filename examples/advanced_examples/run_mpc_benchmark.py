"""
MPC控制器基准测试

对比三种控制策略的性能：
1. 传统PID控制
2. 自适应PI控制（基于在线IDZ辨识）
3. 模型预测控制（MPC，使用CVXPY）

测试场景：
- 多个工况点切换（流量20→25→18→23 m³/s）
- 相同的约束条件
- 相同的渠道系统

性能指标：
- MAE、RMSE、最大误差
- 稳态误差
- 控制能耗
- 约束违反次数

作者：HydroClaude Team
日期：2025-10-24
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import yaml
import time

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from control.pid_controller import PIDConfig, PIDController
from control.online_identification import IDZIdentifier, IdentificationMethod
from control.idz_model import IDZParameters
from control.mpc_controller import MPCController, MPCConfig


def imc_tune(idz_params, lambda_factor=2.0):
    """
    简化的IMC整定方法

    Args:
        idz_params: IDZ参数
        lambda_factor: 滤波器时间常数因子

    Returns:
        (Kp, Ki): PI参数
    """
    K = idz_params.K
    tau_d = idz_params.tau_d
    lambda_c = lambda_factor * tau_d

    Kp = tau_d / (K * lambda_c)
    Ki = 1.0 / (K * lambda_c)

    return Kp, Ki


class SimplifiedCanalSimulator:
    """简化渠道模拟器（用于快速基准测试）"""

    def __init__(self, K=100.0, tau_z=200.0, tau_d=300.0, theta=20.0, dt=2.0):
        """
        初始化模拟器

        Args:
            K, tau_z, tau_d, theta: IDZ模型参数
            dt: 采样时间
        """
        self.params = IDZParameters(K=K, tau_z=tau_z, tau_d=tau_d, theta=theta)
        self.dt = dt

        # 使用IDZModel进行高保真仿真
        from control.idz_model import IDZModel
        self.model = IDZModel(self.params, dt=dt)

        # 状态
        self.y = 0.0  # 当前水位偏差（相对于基准）
        self.base_level = 2.2  # 基准水位
        self.u_disturbance = 0.0  # 上游流量扰动

    def reset(self):
        """重置模拟器"""
        self.model.reset()
        self.y = 0.0
        self.u_disturbance = 0.0

    def set_disturbance(self, Q_disturbance):
        """设置上游流量扰动"""
        self.u_disturbance = Q_disturbance

    def step(self, u_control):
        """
        仿真一步

        Args:
            u_control: 控制量（闸门开度）

        Returns:
            y: 当前水位（绝对值）
        """
        # 总输入 = 控制量 + 扰动
        u_total = u_control + self.u_disturbance * 0.01  # 扰动增益

        # IDZ模型仿真
        dy = self.model.step(u_total)

        # 累积到基准水位
        self.y = dy
        y_absolute = self.base_level + self.y

        return y_absolute


def run_benchmark(controller_type="pid", config_path=None, plot_results=True):
    """
    运行基准测试

    Args:
        controller_type: 控制器类型 ("pid", "adaptive_pi", "mpc")
        config_path: 配置文件路径（可选）
        plot_results: 是否绘制结果

    Returns:
        results: 结果字典
    """
    print("=" * 80)
    print(f"基准测试: {controller_type.upper()} 控制器")
    print("=" * 80)

    # 仿真参数
    dt = 2.0
    total_time = 1200.0
    n_steps = int(total_time / dt)

    setpoint = 2.2  # 目标水位

    # 上游流量扰动时间表
    disturbance_schedule = [
        (0, 20.0),
        (300, 25.0),
        (600, 18.0),
        (900, 23.0)
    ]

    # 创建模拟器
    simulator = SimplifiedCanalSimulator(K=100.0, tau_z=200.0, tau_d=300.0, theta=20.0, dt=dt)
    simulator.reset()

    # 创建控制器
    if controller_type == "pid":
        # 传统PID（经验整定）
        controller = PIDController(
            PIDConfig(kp=0.5, ki=0.1, kd=0.0, dt=dt,
                     output_min=0.5, output_max=4.0)
        )
        controller.set_setpoint(setpoint)

    elif controller_type == "adaptive_pi":
        # 自适应PI（IMC整定）
        identifier = IDZIdentifier(dt=dt, method=IdentificationMethod.FORGETTING_RLS, use_scipy=True)

        controller = PIDController(
            PIDConfig(kp=0.5, ki=0.1, kd=0.0, dt=dt,
                     output_min=0.5, output_max=4.0)
        )
        controller.set_setpoint(setpoint)

    elif controller_type == "mpc":
        # MPC（使用观测器）
        idz_params = IDZParameters(K=100.0, tau_z=200.0, tau_d=300.0, theta=20.0)
        mpc_config = MPCConfig(
            prediction_horizon=15,
            control_horizon=10,
            dt=dt,
            Q=100.0,
            R=1.0,
            Qf=1000.0,
            u_min=0.5,
            u_max=4.0,
            du_max=0.3,
            solver='OSQP',
            verbose=False
        )
        controller = MPCController(idz_params, mpc_config, use_observer=True)

    else:
        raise ValueError(f"未知控制器类型: {controller_type}")

    # 记录数据
    time_history = []
    y_history = []
    u_history = []
    setpoint_history = []
    disturbance_history = []
    error_history = []

    # 初始化
    y = setpoint
    u = 2.0
    current_disturbance = 20.0

    print(f"\n开始仿真...")
    print(f"  采样时间: {dt} s")
    print(f"  总时间: {total_time} s ({n_steps} 步)")
    print(f"  目标水位: {setpoint} m")
    print(f"  扰动切换: {len(disturbance_schedule)} 次")

    start_time = time.time()

    # 主循环
    for k in range(n_steps):
        t = k * dt

        # 更新扰动
        for t_switch, Q_new in disturbance_schedule:
            if abs(t - t_switch) < dt / 2:
                current_disturbance = Q_new
                simulator.set_disturbance(Q_new)
                print(f"  t={t:.0f}s: 扰动切换到 Q={Q_new} m³/s")
                break

        # 计算控制量
        if controller_type == "mpc":
            u, diagnostics = controller.compute_control(y, setpoint)
        else:
            u = controller.compute(y)

        # 自适应PI特殊处理：在线辨识和IMC整定
        if controller_type == "adaptive_pi" and k > 20:
            # 每10步更新一次
            if k % 10 == 0:
                try:
                    # 在线辨识
                    identifier.update(y, u)
                    idz_params = identifier.get_parameters()

                    # IMC整定
                    if idz_params is not None and idz_params.K > 0:
                        Kp, Ki = imc_tune(idz_params, lambda_factor=2.0)
                        controller.set_gains(Kp, Ki, 0.0)
                except Exception as e:
                    pass  # 辨识失败时保持当前参数

        # 仿真一步
        y = simulator.step(u)

        # 记录
        time_history.append(t)
        y_history.append(y)
        u_history.append(u)
        setpoint_history.append(setpoint)
        disturbance_history.append(current_disturbance)
        error_history.append(y - setpoint)

        # 显示进度
        if (k + 1) % 100 == 0:
            print(f"    步骤 {k+1}/{n_steps}: y={y:.4f} m, u={u:.4f} m, error={y-setpoint:.4f} m")

    elapsed_time = time.time() - start_time
    print(f"\n仿真完成，耗时 {elapsed_time:.2f} s")

    # 计算性能指标
    y_array = np.array(y_history)
    u_array = np.array(u_history)
    error_array = np.array(error_history)

    mae = np.mean(np.abs(error_array))
    rmse = np.sqrt(np.mean(error_array**2))
    max_error = np.max(np.abs(error_array))

    # 稳态误差（最后10%的数据）
    n_steady = max(int(len(error_array) * 0.1), 10)
    steady_state_error = np.mean(np.abs(error_array[-n_steady:]))

    # 控制能耗（控制增量的累积）
    control_effort = np.sum(np.abs(np.diff(u_array)))

    # 约束违反
    constraint_violations = np.sum((u_array < 0.5) | (u_array > 4.0))

    # 显示结果
    print("\n" + "-" * 80)
    print("性能指标:")
    print("-" * 80)
    print(f"  MAE (平均绝对误差):     {mae:.4f} m")
    print(f"  RMSE (均方根误差):      {rmse:.4f} m")
    print(f"  最大误差:               {max_error:.4f} m")
    print(f"  稳态误差:               {steady_state_error:.4f} m")
    print(f"  控制能耗:               {control_effort:.4f} m")
    print(f"  约束违反次数:           {constraint_violations}")
    print("-" * 80)

    # 组织结果
    results = {
        'controller_type': controller_type,
        'time': np.array(time_history),
        'y': y_array,
        'u': u_array,
        'setpoint': np.array(setpoint_history),
        'disturbance': np.array(disturbance_history),
        'error': error_array,
        'metrics': {
            'mae': mae,
            'rmse': rmse,
            'max_error': max_error,
            'steady_state_error': steady_state_error,
            'control_effort': control_effort,
            'constraint_violations': constraint_violations
        }
    }

    # 绘图
    if plot_results:
        plot_single_result(results)

    return results


def plot_single_result(result):
    """绘制单个控制器的结果"""
    fig, axes = plt.subplots(4, 1, figsize=(14, 12))

    t = result['time'] / 60  # 转换为分钟
    controller_name = result['controller_type'].upper()

    # 子图1：水位
    axes[0].plot(t, result['y'], 'b-', linewidth=2, label='实际水位')
    axes[0].plot(t, result['setpoint'], 'r--', linewidth=2, label='目标水位')
    axes[0].set_ylabel('水位 (m)')
    axes[0].set_title(f'{controller_name} Controller Performance')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # 子图2：控制量
    axes[1].plot(t, result['u'], 'g-', linewidth=2, label='闸门开度')
    axes[1].axhline(y=0.5, color='k', linestyle=':', alpha=0.5, label='约束边界')
    axes[1].axhline(y=4.0, color='k', linestyle=':', alpha=0.5)
    axes[1].set_ylabel('控制量 (m)')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    # 子图3：误差
    axes[2].plot(t, result['error'], 'r-', linewidth=2)
    axes[2].axhline(y=0, color='k', linestyle='-', alpha=0.3)
    axes[2].set_ylabel('误差 (m)')
    axes[2].grid(True, alpha=0.3)

    # 子图4：扰动
    axes[3].plot(t, result['disturbance'], 'orange', linewidth=2, drawstyle='steps-post')
    axes[3].set_xlabel('时间 (min)')
    axes[3].set_ylabel('上游流量 (m³/s)')
    axes[3].grid(True, alpha=0.3)

    plt.tight_layout()
    filename = f"mpc_benchmark_{result['controller_type']}.png"
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"\n✅ 图片已保存: {filename}")


def plot_comparison(results_list):
    """绘制多个控制器的对比图"""
    fig, axes = plt.subplots(3, 1, figsize=(14, 10))

    colors = ['blue', 'green', 'red']
    linestyles = ['-', '--', '-.']

    for i, result in enumerate(results_list):
        t = result['time'] / 60
        label = result['controller_type'].upper()
        color = colors[i % len(colors)]
        ls = linestyles[i % len(linestyles)]

        # 子图1：水位
        axes[0].plot(t, result['y'], color=color, linestyle=ls, linewidth=2, label=label)

        # 子图2：控制量
        axes[1].plot(t, result['u'], color=color, linestyle=ls, linewidth=2, label=label)

        # 子图3：误差
        axes[2].plot(t, result['error'], color=color, linestyle=ls, linewidth=2, label=label)

    # 添加目标水位线
    axes[0].plot(t, results_list[0]['setpoint'], 'k--', linewidth=1, alpha=0.5, label='Setpoint')
    axes[0].set_ylabel('Water Level (m)')
    axes[0].set_title('Controller Comparison')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].axhline(y=0.5, color='k', linestyle=':', alpha=0.5)
    axes[1].axhline(y=4.0, color='k', linestyle=':', alpha=0.5)
    axes[1].set_ylabel('Control Action (m)')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    axes[2].axhline(y=0, color='k', linestyle='-', alpha=0.3)
    axes[2].set_xlabel('Time (min)')
    axes[2].set_ylabel('Error (m)')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    filename = "mpc_benchmark_comparison.png"
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"\n✅ 对比图已保存: {filename}")


def print_comparison_table(results_list):
    """打印性能对比表"""
    print("\n" + "=" * 80)
    print("性能对比表")
    print("=" * 80)

    # 表头
    print(f"{'控制器':<15} {'MAE':<10} {'RMSE':<10} {'Max Error':<12} {'稳态误差':<12} {'控制能耗':<12}")
    print("-" * 80)

    # 数据行
    for result in results_list:
        m = result['metrics']
        controller = result['controller_type'].upper()
        print(f"{controller:<15} {m['mae']:<10.4f} {m['rmse']:<10.4f} {m['max_error']:<12.4f} "
              f"{m['steady_state_error']:<12.4f} {m['control_effort']:<12.2f}")

    print("=" * 80)


def main():
    """主函数"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 25 + "MPC控制器基准测试" + " " * 35 + "║")
    print("╚" + "=" * 78 + "╝")

    # 运行三种控制器的测试
    results = []

    for controller_type in ["pid", "adaptive_pi", "mpc"]:
        result = run_benchmark(controller_type, plot_results=True)
        results.append(result)
        print("\n")

    # 对比图
    plot_comparison(results)

    # 对比表
    print_comparison_table(results)

    print("\n" + "=" * 80)
    print("✅ 基准测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()
