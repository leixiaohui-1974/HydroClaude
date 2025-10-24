"""
一阶MPC在Saint-Venant高保真模型上的性能测试

测试目标：
1. 验证线性化MPC在非线性Saint-Venant模型上的控制效果
2. 对比线性化模型与高保真模型的性能差异
3. 评估模型失配的影响

系统架构：
┌────────────────────────────────────────────────────────┐
│                  对比测试框架                            │
│                                                          │
│  ┌─────────────────┐          ┌─────────────────┐      │
│  │  一阶MPC控制器   │  u(k)    │  Saint-Venant   │      │
│  │  (线性化模型)    │────────>│  高保真模型      │      │
│  │  K=-0.3, τ=206s │<────────│   (MOC求解)     │      │
│  └─────────────────┘  y(k)    └─────────────────┘      │
│         测试1: 真实模型控制                              │
│                                                          │
│  ┌─────────────────┐          ┌─────────────────┐      │
│  │  一阶MPC控制器   │  u(k)    │   线性化模型    │      │
│  │  (线性化模型)    │────────>│   H(s)=K/(τs+1) │      │
│  │  K=-0.3, τ=206s │<────────│                 │      │
│  └─────────────────┘  y(k)    └─────────────────┘      │
│         测试2: 理想模型控制（基准）                      │
│                                                          │
└────────────────────────────────────────────────────────┘

性能指标：
- MAE（平均绝对误差）
- RMSE（均方根误差）
- 最大超调量
- 调节时间
- 非线性影响分析

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import List, Tuple, Dict
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from physics.canal import Canal
from examples.advanced_examples.linearized_canal_simulator import LinearizedCanalSimulator
from control.first_order_mpc import FirstOrderMPC, FirstOrderMPCConfig


class MPCSaintVenantTest:
    """
    MPC在Saint-Venant高保真模型上的性能测试框架
    """

    def __init__(self):
        """初始化测试环境"""
        # 控制参数
        self.dt = 10.0  # 控制周期 (s)

        # 设定点参数
        self.h_work = 2.5  # 工作点水位 (m)
        self.a_work = 2.0  # 工作点闸门开度 (m)

        # 线性化参数（从之前的测试获得）
        self.K_linear = -0.3  # 增益
        self.tau_linear = 206.1  # 时间常数 (s)

    def create_saint_venant_model(self) -> Canal:
        """
        创建Saint-Venant高保真模型

        使用与线性化模型相同的物理参数
        """
        # 渠道物理参数
        length = 1000.0  # 渠道长度 (m)
        width = 10.0     # 渠道宽度 (m)
        slope = 0.001    # 底坡
        manning_n = 0.025  # 曼宁系数

        # 初始条件
        initial_depth = self.h_work
        initial_flow = 20.0  # 初始流量 (m³/s)

        # 创建Canal对象
        canal = Canal(
            name="test_canal",
            volume_min=0.0,
            volume_max=length * width * 10.0,
            area=width * initial_depth,
            length=length,
            slope=slope,
            n_sections=51,  # 空间离散点数
            method='moc',   # 使用MOC方法
            manning_n=manning_n,
            width=width,
            initial_depth=initial_depth,
            initial_flow=initial_flow
        )

        return canal

    def create_linearized_model(self) -> LinearizedCanalSimulator:
        """创建线性化模型（用于对比）"""
        simulator = LinearizedCanalSimulator(
            h_work=self.h_work,
            a_work=self.a_work,
            dt=self.dt,
            use_linear=True
        )
        return simulator

    def create_mpc_controller(self) -> FirstOrderMPC:
        """创建一阶MPC控制器"""
        config = FirstOrderMPCConfig(
            prediction_horizon=15,
            control_horizon=10,
            dt=self.dt,
            Q=100.0,
            R=1.0,
            Qf=1000.0,
            u_min=0.1,
            u_max=4.0,
            du_max=0.5,
            solver='OSQP',
            verbose=False
        )

        controller = FirstOrderMPC(
            K=self.K_linear,
            tau=self.tau_linear,
            config=config
        )
        return controller

    def gate_opening_to_flow(self, a: float, h: float) -> float:
        """
        闸门开度到流量的转换（闸门方程）

        Q = C_d * a * sqrt(2*g*h)

        Args:
            a: 闸门开度 (m)
            h: 上游水位 (m)

        Returns:
            Q: 流量 (m³/s)
        """
        C_d = 0.6  # 流量系数
        g = 9.81   # 重力加速度

        # 防止负数
        h_effective = max(h - 0.5, 0.1)  # 假设闸底高程0.5m

        Q = C_d * a * np.sqrt(2 * g * h_effective) * 10.0  # 乘以渠道宽度
        return Q

    def run_test_on_saint_venant(self, controller: FirstOrderMPC,
                                  canal: Canal,
                                  total_time: float = 800.0,
                                  disturbance_schedule: List[Tuple[float, float]] = None
                                 ) -> Dict:
        """
        在Saint-Venant模型上运行MPC控制测试

        Args:
            controller: MPC控制器
            canal: Saint-Venant模型
            total_time: 仿真总时间 (s)
            disturbance_schedule: 扰动时间表 [(时刻, 流量), ...]

        Returns:
            result: 测试结果字典
        """
        if disturbance_schedule is None:
            disturbance_schedule = [
                (0, 20.0),
                (200, 25.0),
                (400, 18.0),
                (600, 23.0)
            ]

        # 设定点
        setpoint = self.h_work + 0.3  # 目标水位

        # 仿真步数
        n_steps = int(total_time / self.dt)

        # 记录数组
        time_hist = []
        h_hist = []  # 下游水位
        u_hist = []  # 闸门开度
        Q_in_hist = []  # 入流
        error_hist = []

        # 初始化Canal的时间步长
        canal.dt = self.dt

        # 当前扰动
        current_Q_in = disturbance_schedule[0][1]

        for k in range(n_steps):
            t = k * self.dt

            # 更新扰动
            for t_switch, Q_new in disturbance_schedule:
                if abs(t - t_switch) < self.dt / 2:
                    current_Q_in = Q_new
                    break

            # 获取下游水位（取出口处的水位作为观测）
            h_downstream = canal.hydraulic_state.h[-1]

            # MPC计算控制量（闸门开度）
            u_gate, _ = controller.compute_control(h_downstream, setpoint)

            # 闸门开度转换为出流流量
            Q_out = self.gate_opening_to_flow(u_gate, h_downstream)

            # 设置边界条件
            # 上游边界：恒定入流
            canal.hydraulic_state.Q[0] = current_Q_in

            # 下游边界：出流（通过闸门控制）
            # 这里简化处理：直接设置出流
            canal.hydraulic_state.Q[-1] = Q_out

            # 执行一步MOC求解
            inputs = {
                'Q_in': current_Q_in,
                'Q_out': Q_out
            }
            canal.update_high_fidelity(self.dt, inputs)

            # 记录数据
            time_hist.append(t)
            h_hist.append(h_downstream)
            u_hist.append(u_gate)
            Q_in_hist.append(current_Q_in)
            error_hist.append(abs(h_downstream - setpoint))

        # 计算性能指标
        h_array = np.array(h_hist)
        error_array = np.array(error_hist)

        mae = np.mean(error_array)
        rmse = np.sqrt(np.mean(error_array**2))
        max_error = np.max(error_array)

        # 计算调节时间（误差小于5%的时间）
        settling_threshold = 0.05 * abs(setpoint - self.h_work)
        settling_indices = np.where(error_array < settling_threshold)[0]
        settling_time = settling_indices[0] * self.dt if len(settling_indices) > 0 else total_time

        result = {
            'time': np.array(time_hist),
            'h': h_array,
            'u': np.array(u_hist),
            'Q_in': np.array(Q_in_hist),
            'error': error_array,
            'mae': mae,
            'rmse': rmse,
            'max_error': max_error,
            'settling_time': settling_time,
            'setpoint': setpoint
        }

        return result

    def run_test_on_linearized(self, controller: FirstOrderMPC,
                                simulator: LinearizedCanalSimulator,
                                total_time: float = 800.0,
                                disturbance_schedule: List[Tuple[float, float]] = None
                               ) -> Dict:
        """
        在线性化模型上运行MPC控制测试（基准）

        Args:
            controller: MPC控制器
            simulator: 线性化模型
            total_time: 仿真总时间 (s)
            disturbance_schedule: 扰动时间表

        Returns:
            result: 测试结果字典
        """
        if disturbance_schedule is None:
            disturbance_schedule = [
                (0, 20.0),
                (200, 25.0),
                (400, 18.0),
                (600, 23.0)
            ]

        # 设定点
        setpoint = self.h_work + 0.3

        # 仿真步数
        n_steps = int(total_time / self.dt)

        # 记录数组
        time_hist = []
        h_hist = []
        u_hist = []
        Q_in_hist = []
        error_hist = []

        # 当前扰动
        current_Q_in = disturbance_schedule[0][1]

        for k in range(n_steps):
            t = k * self.dt

            # 更新扰动
            for t_switch, Q_new in disturbance_schedule:
                if abs(t - t_switch) < self.dt / 2:
                    current_Q_in = Q_new
                    simulator.set_disturbance(Q_new)
                    break

            # 获取当前水位
            y = simulator.h

            # MPC计算控制量
            u, _ = controller.compute_control(y, setpoint)

            # 执行控制
            y_next = simulator.step(u)

            # 记录
            time_hist.append(t)
            h_hist.append(y)
            u_hist.append(u)
            Q_in_hist.append(current_Q_in)
            error_hist.append(abs(y - setpoint))

        # 计算性能指标
        h_array = np.array(h_hist)
        error_array = np.array(error_hist)

        mae = np.mean(error_array)
        rmse = np.sqrt(np.mean(error_array**2))
        max_error = np.max(error_array)

        settling_threshold = 0.05 * abs(setpoint - self.h_work)
        settling_indices = np.where(error_array < settling_threshold)[0]
        settling_time = settling_indices[0] * self.dt if len(settling_indices) > 0 else total_time

        result = {
            'time': np.array(time_hist),
            'h': h_array,
            'u': np.array(u_hist),
            'Q_in': np.array(Q_in_hist),
            'error': error_array,
            'mae': mae,
            'rmse': rmse,
            'max_error': max_error,
            'settling_time': settling_time,
            'setpoint': setpoint
        }

        return result

    def visualize_comparison(self, result_sv: Dict, result_lin: Dict,
                            save_path: str = "mpc_saint_venant_comparison.png"):
        """
        可视化Saint-Venant模型和线性化模型的对比结果

        Args:
            result_sv: Saint-Venant模型结果
            result_lin: 线性化模型结果
            save_path: 保存路径
        """
        fig = plt.figure(figsize=(16, 10))

        # 子图1：水位对比
        ax1 = plt.subplot(2, 3, 1)
        ax1.plot(result_sv['time'], result_sv['h'], 'b-', linewidth=2, label='Saint-Venant Model')
        ax1.plot(result_lin['time'], result_lin['h'], 'r--', linewidth=2, label='Linearized Model')
        ax1.axhline(result_sv['setpoint'], color='gray', linestyle=':', label='Setpoint')
        ax1.set_xlabel('Time (s)', fontsize=11)
        ax1.set_ylabel('Water Level (m)', fontsize=11)
        ax1.set_title('Water Level Comparison', fontsize=12, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 子图2：控制量对比
        ax2 = plt.subplot(2, 3, 2)
        ax2.plot(result_sv['time'], result_sv['u'], 'b-', linewidth=2, label='Saint-Venant Model')
        ax2.plot(result_lin['time'], result_lin['u'], 'r--', linewidth=2, label='Linearized Model')
        ax2.set_xlabel('Time (s)', fontsize=11)
        ax2.set_ylabel('Gate Opening (m)', fontsize=11)
        ax2.set_title('Control Input Comparison', fontsize=12, fontweight='bold')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # 子图3：误差对比
        ax3 = plt.subplot(2, 3, 3)
        ax3.plot(result_sv['time'], result_sv['error'] * 100, 'b-', linewidth=2, label='Saint-Venant Model')
        ax3.plot(result_lin['time'], result_lin['error'] * 100, 'r--', linewidth=2, label='Linearized Model')
        ax3.set_xlabel('Time (s)', fontsize=11)
        ax3.set_ylabel('Absolute Error (cm)', fontsize=11)
        ax3.set_title('Tracking Error Comparison', fontsize=12, fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # 子图4：扰动
        ax4 = plt.subplot(2, 3, 4)
        ax4.step(result_sv['time'], result_sv['Q_in'], 'g-', linewidth=2, where='post')
        ax4.set_xlabel('Time (s)', fontsize=11)
        ax4.set_ylabel('Inflow (m³/s)', fontsize=11)
        ax4.set_title('Disturbance (Inflow)', fontsize=12, fontweight='bold')
        ax4.grid(True, alpha=0.3)

        # 子图5：性能指标对比
        ax5 = plt.subplot(2, 3, 5)
        metrics = ['MAE\n(cm)', 'RMSE\n(cm)', 'Max Error\n(cm)', 'Settling\nTime (s)']
        sv_values = [result_sv['mae']*100, result_sv['rmse']*100,
                     result_sv['max_error']*100, result_sv['settling_time']]
        lin_values = [result_lin['mae']*100, result_lin['rmse']*100,
                      result_lin['max_error']*100, result_lin['settling_time']]

        x = np.arange(len(metrics))
        width = 0.35

        ax5.bar(x - width/2, sv_values, width, label='Saint-Venant', color='blue', alpha=0.7)
        ax5.bar(x + width/2, lin_values, width, label='Linearized', color='red', alpha=0.7)
        ax5.set_xticks(x)
        ax5.set_xticklabels(metrics, fontsize=9)
        ax5.set_ylabel('Value', fontsize=11)
        ax5.set_title('Performance Metrics Comparison', fontsize=12, fontweight='bold')
        ax5.legend()
        ax5.grid(True, alpha=0.3, axis='y')

        # 子图6：误差统计分析
        ax6 = plt.subplot(2, 3, 6)

        # 计算模型失配影响
        h_diff = result_sv['h'] - result_lin['h']
        u_diff = result_sv['u'] - result_lin['u']

        ax6_twin = ax6.twinx()
        ax6.plot(result_sv['time'], h_diff * 100, 'b-', linewidth=2, label='Water Level Diff')
        ax6_twin.plot(result_sv['time'], u_diff * 100, 'r-', linewidth=2, label='Control Diff')

        ax6.set_xlabel('Time (s)', fontsize=11)
        ax6.set_ylabel('Water Level Difference (cm)', fontsize=11, color='b')
        ax6_twin.set_ylabel('Gate Opening Difference (cm)', fontsize=11, color='r')
        ax6.set_title('Model Mismatch Analysis', fontsize=12, fontweight='bold')
        ax6.tick_params(axis='y', labelcolor='b')
        ax6_twin.tick_params(axis='y', labelcolor='r')
        ax6.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"✅ 图片已保存: {save_path}")

        return fig

    def print_summary(self, result_sv: Dict, result_lin: Dict):
        """
        打印性能对比总结

        Args:
            result_sv: Saint-Venant模型结果
            result_lin: 线性化模型结果
        """
        print("\n" + "="*80)
        print("MPC在Saint-Venant高保真模型上的性能测试总结")
        print("="*80)

        print("\n【测试1】Saint-Venant高保真模型（MOC求解）")
        print("-" * 80)
        print(f"  MAE           = {result_sv['mae']*100:.2f} cm")
        print(f"  RMSE          = {result_sv['rmse']*100:.2f} cm")
        print(f"  最大误差      = {result_sv['max_error']*100:.2f} cm")
        print(f"  调节时间      = {result_sv['settling_time']:.1f} s")

        print("\n【测试2】线性化模型（基准）")
        print("-" * 80)
        print(f"  MAE           = {result_lin['mae']*100:.2f} cm")
        print(f"  RMSE          = {result_lin['rmse']*100:.2f} cm")
        print(f"  最大误差      = {result_lin['max_error']*100:.2f} cm")
        print(f"  调节时间      = {result_lin['settling_time']:.1f} s")

        print("\n【模型失配影响分析】")
        print("-" * 80)
        mae_diff = (result_sv['mae'] - result_lin['mae']) * 100
        mae_diff_pct = (mae_diff / (result_lin['mae']*100)) * 100

        rmse_diff = (result_sv['rmse'] - result_lin['rmse']) * 100
        settling_diff = result_sv['settling_time'] - result_lin['settling_time']

        print(f"  MAE增加       = {mae_diff:+.2f} cm ({mae_diff_pct:+.1f}%)")
        print(f"  RMSE增加      = {rmse_diff:+.2f} cm")
        print(f"  调节时间变化  = {settling_diff:+.1f} s")

        # 判定
        if mae_diff_pct < 10:
            verdict = "✅ 优秀：模型失配影响极小（<10%）"
        elif mae_diff_pct < 20:
            verdict = "⭕ 良好：模型失配影响可接受（10-20%）"
        elif mae_diff_pct < 30:
            verdict = "⚠️  一般：模型失配影响较大（20-30%）"
        else:
            verdict = "❌ 较差：模型失配影响显著（>30%）"

        print(f"\n  综合评价：{verdict}")

        print("\n【关键发现】")
        print("-" * 80)
        if mae_diff_pct < 15:
            print("  ✅ 线性化假设在工作点附近有效")
            print("  ✅ 一阶MPC可直接应用于实际Saint-Venant系统")
            print("  ✅ 控制性能基本不受非线性影响")
        else:
            print("  ⚠️  非线性效应不可忽略")
            print("  💡 建议：考虑增益调度或多工作点MPC")

        print("\n" + "="*80)


def main():
    """主测试函数"""
    print("="*80)
    print("一阶MPC在Saint-Venant高保真模型上的性能测试")
    print("="*80)
    print("\n测试配置：")
    print("  - 控制器: 一阶MPC (K=-0.3, τ=206s)")
    print("  - 高保真模型: Saint-Venant方程 (MOC求解)")
    print("  - 基准模型: 线性化一阶模型")
    print("  - 仿真时间: 800s")
    print("  - 扰动: 4次阶跃变化 (20→25→18→23 m³/s)")
    print("\n开始测试...\n")

    # 创建测试对象
    test = MPCSaintVenantTest()

    # 创建模型
    print("【步骤1】创建Saint-Venant高保真模型...")
    canal = test.create_saint_venant_model()
    print(f"  ✅ Canal模型创建完成")
    print(f"     - 长度: {canal.length}m")
    print(f"     - 宽度: {canal.parameters['width']}m")
    print(f"     - 离散节点: {canal.n_sections}")
    print(f"     - 求解方法: {canal.method.upper()}")

    print("\n【步骤2】创建线性化模型（基准）...")
    simulator = test.create_linearized_model()
    print(f"  ✅ 线性化模型创建完成")
    print(f"     - K = {test.K_linear}")
    print(f"     - τ = {test.tau_linear}s")

    print("\n【步骤3】创建MPC控制器...")
    controller_sv = test.create_mpc_controller()
    controller_lin = test.create_mpc_controller()
    print(f"  ✅ MPC控制器创建完成")
    print(f"     - 预测时域Np = 15")
    print(f"     - 控制时域Nc = 10")
    print(f"     - 权重Q = 100, R = 1")

    print("\n【步骤4】运行Saint-Venant模型测试...")
    result_sv = test.run_test_on_saint_venant(controller_sv, canal)
    print(f"  ✅ Saint-Venant测试完成")
    print(f"     - MAE = {result_sv['mae']*100:.2f} cm")

    print("\n【步骤5】运行线性化模型测试...")
    result_lin = test.run_test_on_linearized(controller_lin, simulator)
    print(f"  ✅ 线性化模型测试完成")
    print(f"     - MAE = {result_lin['mae']*100:.2f} cm")

    print("\n【步骤6】生成对比可视化...")
    test.visualize_comparison(result_sv, result_lin)

    # 打印详细总结
    test.print_summary(result_sv, result_lin)

    print("\n测试完成！✅")


if __name__ == "__main__":
    main()
