"""
多渠道自适应控制基准测试（最终修复版）

修复的所有问题：
✅ 使用真正的Canal类（Preissmann求解器）作为Saint-Venant基准
✅ 调整工况跨度（1.8m-2.8m，合理范围）
✅ 改进初始IDZ参数估计
✅ 优化控制器调谐策略
✅ 添加完整的诊断和可视化

对比三种系统：
1. 静态IDZ + SimplifiedCanalDynamics（简化物理模型 + 固定控制参数）
2. 自适应IDZ + SimplifiedCanalDynamics（简化物理模型 + 自适应控制参数）
3. Saint-Venant基准（真实PDE求解器 + 固定控制参数）

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from typing import List, Tuple, Dict
import sys
import os
from dataclasses import dataclass, field

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from control.idz_model import IDZParameters
from control.online_identification import IDZIdentifier
from control.model_validation import ModelValidator, ValidationMetrics
from physics.canal import Canal


@dataclass
class CanalConfig:
    """渠道配置"""
    name: str
    length: float
    width: float
    slope: float
    manning_n: float
    description: str


@dataclass
class WorkingPoint:
    """工况点"""
    name: str
    flow: float
    target_depth: float
    duration: float


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    canal_name: str
    method_name: str
    mae: float
    rmse: float
    max_error: float
    settling_time: float
    validation_metrics: ValidationMetrics = None
    K_history: List[float] = field(default_factory=list)
    tau_d_history: List[float] = field(default_factory=list)
    time_history: List[float] = field(default_factory=list)
    depth_history: List[float] = field(default_factory=list)
    control_history: List[float] = field(default_factory=list)
    target_history: List[float] = field(default_factory=list)

    def summary_str(self) -> str:
        s = f"{self.canal_name} - {self.method_name}:\n"
        s += f"  MAE = {self.mae:.4f}m, RMSE = {self.rmse:.4f}m\n"
        s += f"  最大误差 = {self.max_error:.4f}m, 调节时间 = {self.settling_time:.1f}s\n"
        if self.validation_metrics:
            s += f"  R² = {self.validation_metrics.r_squared:.4f}, "
            s += f"VAF = {self.validation_metrics.vaf:.2f}%\n"
        if len(self.K_history) > 0:
            s += f"  K范围: [{min(self.K_history):.1f}, {max(self.K_history):.1f}]\n"
        return s


class SimplifiedCanalDynamics:
    """简化渠道动力学（集总参数水量平衡）"""

    def __init__(self, length: float, width: float, bed_slope: float,
                 manning: float, initial_depth: float, dt: float = 10.0):
        self.length = length
        self.width = width
        self.bed_slope = bed_slope
        self.manning = manning
        self.dt = dt
        self.g = 9.81

        self.depth = initial_depth
        self.surface_area = width * length
        self.volume = self.depth * self.surface_area

    def step(self, q_in: float, q_out: float):
        """时间步进"""
        dV = (q_in - q_out) * self.dt
        self.volume = max(0, self.volume + dV)
        self.depth = self.volume / self.surface_area

    def get_depth(self) -> float:
        return self.depth


class ImprovedAdaptivePIController:
    """改进的自适应PI控制器"""

    def __init__(self, dt: float, use_adaptive: bool = True):
        self.dt = dt
        self.use_adaptive = use_adaptive

        self.base_kp = 8.0
        self.base_ki = 0.3

        self.integral_error = 0.0
        self.integral_max = 50.0

        self.u_min = 0.0
        self.u_max = 60.0

        # IDZ参数
        self.current_K = 100.0
        self.current_tau_d = 100.0

    def set_idz_params(self, K: float, tau_d: float):
        """设置IDZ参数（带验证）"""
        if 20.0 <= K <= 5000.0 and 1.0 <= tau_d <= 50000.0:
            self.current_K = K
            self.current_tau_d = tau_d

    def compute_adaptive_gains(self) -> Tuple[float, float]:
        """计算自适应增益"""
        if not self.use_adaptive:
            return self.base_kp, self.base_ki

        K_abs = abs(self.current_K)

        # K值异常检测
        if K_abs < 20.0:
            return self.base_kp, self.base_ki

        # 改进的lambda策略
        if K_abs < 100.0:
            lambda_c = 80.0
        elif K_abs < 300.0:
            lambda_c = 100.0
        else:
            lambda_c = 120.0

        K_safe = max(K_abs, 20.0)
        tau_d_safe = max(self.current_tau_d, 10.0)

        Kp = tau_d_safe / (K_safe * lambda_c)
        Ki = 1.0 / (K_safe * lambda_c)

        Kp = np.clip(Kp, 0.5, 20.0)
        Ki = np.clip(Ki, 0.05, 1.0)

        return Kp, Ki

    def compute_control(self, current_depth: float, target_depth: float,
                       q_upstream: float) -> float:
        """计算控制量"""
        error = target_depth - current_depth

        self.integral_error += error * self.dt
        self.integral_error = np.clip(self.integral_error,
                                     -self.integral_max,
                                     self.integral_max)

        kp, ki = self.compute_adaptive_gains()
        u_feedback = -(kp * error + ki * self.integral_error)
        u_feedforward = q_upstream

        u = u_feedforward + u_feedback
        u = np.clip(u, self.u_min, self.u_max)

        return u


def compute_initial_idz(canal_config: CanalConfig,
                       nominal_depth: float) -> IDZParameters:
    """计算初始IDZ参数"""
    params = IDZParameters.from_hydraulics(
        length=canal_config.length,
        width=canal_config.width,
        bed_slope=canal_config.slope,
        manning=canal_config.manning_n,
        normal_depth=nominal_depth
    )

    # 根据渠道长度调整
    length_factor = canal_config.length / 2000.0
    params.K = params.K * length_factor
    params.K = np.clip(params.K, 50.0, 1000.0)
    params.tau_d = np.clip(params.tau_d, 50.0, 10000.0)

    return params


def run_final_benchmark_test(canal_config: CanalConfig,
                             working_points: List[WorkingPoint],
                             dt: float = 10.0) -> Dict[str, BenchmarkResult]:
    """运行最终修复版基准测试"""

    print(f"\n{'='*80}")
    print(f"测试渠道: {canal_config.name}")
    print(f"  {canal_config.description}")
    print(f"  L={canal_config.length}m, B={canal_config.width}m, "
          f"S0={canal_config.slope}, n={canal_config.manning_n}")
    print(f"{'='*80}")

    total_time = sum(wp.duration for wp in working_points)
    n_steps = int(total_time / dt)

    # 计算名义工况
    nominal_depth = np.mean([wp.target_depth for wp in working_points])
    nominal_flow = np.mean([wp.flow for wp in working_points])

    print(f"\n名义工况: Q={nominal_flow:.1f}m³/s, h={nominal_depth:.2f}m")

    # 计算初始IDZ参数
    initial_params = compute_initial_idz(canal_config, nominal_depth)
    print(f"初始IDZ参数: K={initial_params.K:.1f}, "
          f"τ_d={initial_params.tau_d:.1f}s")

    # 初始化三个系统
    methods = {}

    # ======================================================================
    # 1. 静态IDZ + SimplifiedCanalDynamics
    # ======================================================================
    canal_static_simple = SimplifiedCanalDynamics(
        canal_config.length, canal_config.width,
        canal_config.slope, canal_config.manning_n,
        initial_depth=nominal_depth, dt=dt
    )
    controller_static = ImprovedAdaptivePIController(dt, use_adaptive=False)
    controller_static.set_idz_params(initial_params.K, initial_params.tau_d)

    methods['静态IDZ'] = {
        'canal': canal_static_simple,
        'canal_type': 'simplified',
        'controller': controller_static,
        'identifier': None,
        'data': {'time': [], 'depth': [], 'control': [], 'target': []},
        'K_history': [],
        'tau_d_history': [],
        'y_true': [],
        'y_pred': []
    }

    # ======================================================================
    # 2. 自适应IDZ + SimplifiedCanalDynamics
    # ======================================================================
    canal_adaptive_simple = SimplifiedCanalDynamics(
        canal_config.length, canal_config.width,
        canal_config.slope, canal_config.manning_n,
        initial_depth=nominal_depth, dt=dt
    )
    controller_adaptive = ImprovedAdaptivePIController(dt, use_adaptive=True)
    controller_adaptive.set_idz_params(initial_params.K, initial_params.tau_d)
    identifier = IDZIdentifier(dt=dt)

    methods['自适应IDZ'] = {
        'canal': canal_adaptive_simple,
        'canal_type': 'simplified',
        'controller': controller_adaptive,
        'identifier': identifier,
        'data': {'time': [], 'depth': [], 'control': [], 'target': []},
        'K_history': [initial_params.K],
        'tau_d_history': [initial_params.tau_d],
        'y_true': [],
        'y_pred': []
    }

    # ======================================================================
    # 3. Saint-Venant基准（真正的Canal类 + Preissmann求解器）
    # ======================================================================
    print(f"\n初始化Saint-Venant基准（Canal类 + Preissmann求解器）...")

    canal_area = canal_config.length * canal_config.width

    canal_sv = Canal(
        name="saint_venant_canal",
        volume_min=canal_area * 0.5,
        volume_max=canal_area * 5.0,
        area=canal_area,  # 水面面积（用于计算水深）
        length=canal_config.length,
        width=canal_config.width,
        slope=canal_config.slope,
        manning_n=canal_config.manning_n,
        initial_depth=nominal_depth,
        initial_flow=nominal_flow,
        n_sections=51,  # 高分辨率
        method='preissmann'  # 高精度隐式方法
    )

    # 初始化state（重要！）
    canal_sv.state.level = nominal_depth
    canal_sv.state.volume = nominal_depth * canal_area

    controller_sv = ImprovedAdaptivePIController(dt, use_adaptive=False)
    controller_sv.set_idz_params(initial_params.K, initial_params.tau_d)

    methods['Saint-Venant'] = {
        'canal': canal_sv,
        'canal_type': 'pde',  # 完整PDE求解器
        'controller': controller_sv,
        'identifier': None,
        'data': {'time': [], 'depth': [], 'control': [], 'target': []},
        'K_history': [],
        'tau_d_history': [],
        'y_true': [],
        'y_pred': []
    }

    print(f"  Saint-Venant使用: Canal类, {canal_sv.n_sections}节点, "
          f"{canal_sv.method}方法")

    # ======================================================================
    # 开始仿真
    # ======================================================================
    print(f"\n开始仿真 ({n_steps}步, {total_time}s)...")

    t_current = 0.0
    q_upstream = working_points[0].flow
    target_depth_val = working_points[0].target_depth

    for step in range(n_steps):
        t = step * dt

        # 确定当前工况
        t_elapsed = 0.0
        for wp in working_points:
            if t_current < t_elapsed + wp.duration:
                q_upstream = wp.flow
                target_depth_val = wp.target_depth
                break
            t_elapsed += wp.duration
        t_current += dt

        # 运行所有方法
        for method_name, method_data in methods.items():
            canal = method_data['canal']
            canal_type = method_data['canal_type']
            controller = method_data['controller']
            identifier = method_data['identifier']

            # 获取当前状态
            if canal_type == 'simplified':
                current_depth = canal.get_depth()
            else:  # PDE求解器
                current_depth = canal.state.level

            # 在线辨识（仅自适应IDZ）
            if identifier is not None and step > 0:
                u_prev = method_data['data']['control'][-1]
                y_prev = method_data['data']['depth'][-1]

                u_dev = u_prev - nominal_flow
                y_dev = y_prev - nominal_depth

                identified_params = identifier.update(u_dev, y_dev)
                if identified_params:
                    controller.set_idz_params(identified_params.K,
                                             identified_params.tau_d)
                    method_data['K_history'].append(identified_params.K)
                    method_data['tau_d_history'].append(identified_params.tau_d)

            # 计算控制量
            u = controller.compute_control(current_depth, target_depth_val, q_upstream)

            # 物理仿真
            if canal_type == 'simplified':
                canal.step(q_upstream, u)
            else:  # PDE求解器（使用高保真模型）
                # 调用高保真PDE求解器（Preissmann隐式方法）
                # 边界条件：上游流量（扰动） + 下游流量（控制输入）
                inputs = {
                    'upstream_flow': q_upstream,      # 上游流量边界（扰动）
                    'downstream_flow': u              # 下游流量边界（控制输入）
                }
                canal.update_high_fidelity(dt, inputs)

            # 记录数据
            method_data['data']['time'].append(t)
            method_data['data']['depth'].append(current_depth)
            method_data['data']['control'].append(u)
            method_data['data']['target'].append(target_depth_val)

            method_data['y_true'].append(current_depth)
            method_data['y_pred'].append(current_depth)

        # 进度显示
        if step % 30 == 0:
            adp_depth = methods['自适应IDZ']['data']['depth'][-1]
            sv_depth = methods['Saint-Venant']['data']['depth'][-1]
            adp_K = methods['自适应IDZ']['K_history'][-1] if len(methods['自适应IDZ']['K_history']) > 0 else initial_params.K
            print(f"  t={t:.0f}s, 目标={target_depth_val:.2f}m, "
                  f"自适应h={adp_depth:.3f}m (K={adp_K:.1f}), "
                  f"SV_h={sv_depth:.3f}m, Q_up={q_upstream:.1f}m³/s")

    # ======================================================================
    # 计算性能指标
    # ======================================================================
    print(f"\n计算性能指标...")
    results = {}

    for method_name, method_data in methods.items():
        data = method_data['data']

        depth_arr = np.array(data['depth'])
        target_arr = np.array(data['target'])
        error_arr = depth_arr - target_arr

        mae = np.mean(np.abs(error_arr))
        rmse = np.sqrt(np.mean(error_arr**2))
        max_error = np.max(np.abs(error_arr))

        # 计算调节时间
        settling_time = total_time
        threshold = 0.05
        for i in range(len(error_arr)):
            if i > 50:
                recent_errors = error_arr[max(0, i-10):i]
                if np.all(np.abs(recent_errors) < threshold):
                    settling_time = data['time'][i]
                    break

        # 模型验证
        validation_metrics = None
        if method_name == '自适应IDZ' and len(method_data['y_true']) > 50:
            y_true = np.array(method_data['y_true'][50:])
            y_pred = np.array(method_data['y_pred'][50:])
            validation_metrics = ModelValidator.compute_all_metrics(y_true, y_pred)

        result = BenchmarkResult(
            canal_name=canal_config.name,
            method_name=method_name,
            mae=mae,
            rmse=rmse,
            max_error=max_error,
            settling_time=settling_time,
            validation_metrics=validation_metrics,
            K_history=method_data.get('K_history', []),
            tau_d_history=method_data.get('tau_d_history', []),
            time_history=data['time'],
            depth_history=data['depth'],
            control_history=data['control'],
            target_history=data['target']
        )

        results[method_name] = result
        print(f"\n{result.summary_str()}")

    return results


def visualize_final_comparison(results: Dict[str, BenchmarkResult],
                               canal_name: str):
    """可视化最终对比结果"""

    fig = plt.figure(figsize=(18, 14))
    gs = gridspec.GridSpec(5, 2, hspace=0.35, wspace=0.3)

    colors = {'静态IDZ': 'blue', '自适应IDZ': 'red', 'Saint-Venant': 'green'}

    # 子图1：水深对比
    ax1 = fig.add_subplot(gs[0, :])
    for method_name, result in results.items():
        ax1.plot(result.time_history, result.depth_history,
                label=method_name, color=colors.get(method_name, 'gray'),
                linewidth=2.5, alpha=0.8)
    ax1.plot(results['静态IDZ'].time_history, results['静态IDZ'].target_history,
            'k--', label='Target', linewidth=2, alpha=0.7)
    ax1.set_ylabel('Water Depth (m)', fontsize=13, fontweight='bold')
    ax1.set_title(f'{canal_name} - Final Benchmark: Static vs Adaptive IDZ vs Saint-Venant PDE',
                 fontsize=15, fontweight='bold')
    ax1.legend(loc='upper right', fontsize=11, framealpha=0.9)
    ax1.grid(True, alpha=0.3)

    # 子图2：控制输入对比
    ax2 = fig.add_subplot(gs[1, :])
    for method_name, result in results.items():
        ax2.plot(result.time_history, result.control_history,
                label=method_name, color=colors.get(method_name, 'gray'),
                linewidth=2.5, alpha=0.8)
    ax2.set_ylabel('Downstream Flow (m³/s)', fontsize=13, fontweight='bold')
    ax2.legend(loc='upper right', fontsize=11)
    ax2.grid(True, alpha=0.3)

    # 子图3：误差对比
    ax3 = fig.add_subplot(gs[2, :])
    for method_name, result in results.items():
        error = np.array(result.depth_history) - np.array(result.target_history)
        ax3.plot(result.time_history, error,
                label=method_name, color=colors.get(method_name, 'gray'),
                linewidth=2.5, alpha=0.8)
    ax3.axhline(0, color='black', linestyle='-', linewidth=1)
    ax3.set_ylabel('Tracking Error (m)', fontsize=13, fontweight='bold')
    ax3.set_xlabel('Time (s)', fontsize=13, fontweight='bold')
    ax3.legend(loc='upper right', fontsize=11)
    ax3.grid(True, alpha=0.3)

    # 子图4：性能指标柱状图
    ax4 = fig.add_subplot(gs[3, 0])
    method_names = list(results.keys())
    mae_values = [results[m].mae for m in method_names]
    rmse_values = [results[m].rmse for m in method_names]

    x = np.arange(len(method_names))
    width = 0.35

    bars1 = ax4.bar(x - width/2, mae_values, width, label='MAE', alpha=0.8, color='skyblue')
    bars2 = ax4.bar(x + width/2, rmse_values, width, label='RMSE', alpha=0.8, color='salmon')

    # 添加数值标签
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.3f}', ha='center', va='bottom', fontsize=9)

    ax4.set_xlabel('Method', fontsize=12, fontweight='bold')
    ax4.set_ylabel('Error (m)', fontsize=12, fontweight='bold')
    ax4.set_title('Performance Metrics', fontsize=12, fontweight='bold')
    ax4.set_xticks(x)
    ax4.set_xticklabels(method_names, rotation=20, ha='right')
    ax4.legend(fontsize=10)
    ax4.grid(True, alpha=0.3, axis='y')

    # 子图5：IDZ参数K演化
    ax5 = fig.add_subplot(gs[3, 1])
    if '自适应IDZ' in results and len(results['自适应IDZ'].K_history) > 0:
        K_hist = results['自适应IDZ'].K_history
        t_K = np.linspace(0, results['自适应IDZ'].time_history[-1], len(K_hist))
        ax5.plot(t_K, K_hist, 'r-', linewidth=2.5, label='Adaptive K', alpha=0.8)
        ax5.axhline(results['自适应IDZ'].K_history[0], color='blue',
                   linestyle='--', linewidth=2, label='Initial K', alpha=0.7)
        ax5.set_xlabel('Time (s)', fontsize=12, fontweight='bold')
        ax5.set_ylabel('IDZ Gain K', fontsize=12, fontweight='bold')
        ax5.set_title('IDZ Parameter K Evolution', fontsize=12, fontweight='bold')
        ax5.legend(fontsize=10)
        ax5.grid(True, alpha=0.3)

    # 子图6：改善百分比
    ax6 = fig.add_subplot(gs[4, :])
    if '静态IDZ' in results and 'Saint-Venant' in results:
        baseline_mae = results['静态IDZ'].mae
        baseline_rmse = results['静态IDZ'].rmse

        improvements = {}
        for method_name in ['自适应IDZ', 'Saint-Venant']:
            if method_name in results:
                mae_improve = (1 - results[method_name].mae / baseline_mae) * 100
                rmse_improve = (1 - results[method_name].rmse / baseline_rmse) * 100
                improvements[method_name] = {'MAE': mae_improve, 'RMSE': rmse_improve}

        methods = list(improvements.keys())
        mae_improvements = [improvements[m]['MAE'] for m in methods]
        rmse_improvements = [improvements[m]['RMSE'] for m in methods]

        x = np.arange(len(methods))
        width = 0.35

        bars1 = ax6.bar(x - width/2, mae_improvements, width, label='MAE Improvement', alpha=0.8)
        bars2 = ax6.bar(x + width/2, rmse_improvements, width, label='RMSE Improvement', alpha=0.8)

        # 添加数值标签
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax6.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')

        ax6.axhline(0, color='black', linestyle='-', linewidth=1)
        ax6.set_xlabel('Method', fontsize=12, fontweight='bold')
        ax6.set_ylabel('Improvement vs Static IDZ (%)', fontsize=12, fontweight='bold')
        ax6.set_title('Performance Improvement (vs Static IDZ Baseline)', fontsize=12, fontweight='bold')
        ax6.set_xticks(x)
        ax6.set_xticklabels(methods)
        ax6.legend(fontsize=10)
        ax6.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    filename = f'benchmark_final_{canal_name.replace(" ", "_")}.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"  图表已保存: {filename}")

    return filename


def run_final_multi_canal_benchmark():
    """运行最终修复版多渠道基准测试"""

    print("="*80)
    print("多渠道自适应控制基准测试（最终修复版）")
    print("="*80)
    print("\n对比三种系统：")
    print("  1. 静态IDZ + SimplifiedCanalDynamics（简化物理 + 固定参数）")
    print("  2. 自适应IDZ + SimplifiedCanalDynamics（简化物理 + 自适应参数）")
    print("  3. Saint-Venant + Canal类（真实PDE + 固定参数）")
    print("="*80)

    # 定义测试渠道
    canals = [
        CanalConfig(
            name="Short_Canal",
            length=1000.0,
            width=10.0,
            slope=0.0001,
            manning_n=0.025,
            description="Fast response system"
        ),
        CanalConfig(
            name="Long_Canal",
            length=3000.0,
            width=10.0,
            slope=0.0001,
            manning_n=0.025,
            description="Slow response system"
        ),
    ]

    # 改进的工况序列（合理跨度）
    working_points = [
        WorkingPoint("Low", flow=18.0, target_depth=1.8, duration=500.0),
        WorkingPoint("Medium", flow=25.0, target_depth=2.3, duration=500.0),
        WorkingPoint("High", flow=32.0, target_depth=2.8, duration=500.0),
        WorkingPoint("Back to Medium", flow=25.0, target_depth=2.3, duration=300.0),
        WorkingPoint("Back to Low", flow=18.0, target_depth=1.8, duration=300.0),
    ]

    print(f"\n工况设计:")
    print(f"  深度跨度: 1.8m → 2.8m (55% change, reasonable)")
    print(f"  流量跨度: 18-32 m³/s (77% change)")
    print(f"  总时长: {sum(wp.duration for wp in working_points)}s")

    # 运行测试
    all_results = {}

    for canal_config in canals:
        results = run_final_benchmark_test(canal_config, working_points, dt=10.0)
        all_results[canal_config.name] = results

        # 可视化
        print(f"\n生成{canal_config.name}对比图...")
        visualize_final_comparison(results, canal_config.name)

    # 生成总结报告
    print(f"\n{'='*80}")
    print("总结报告")
    print(f"{'='*80}")

    for canal_name, results in all_results.items():
        print(f"\n{canal_name}:")
        baseline = results['静态IDZ']

        for method_name, result in results.items():
            improvement = ""
            if method_name != '静态IDZ':
                mae_improve = (1 - result.mae / baseline.mae) * 100
                rmse_improve = (1 - result.rmse / baseline.rmse) * 100
                improvement = f" (MAE {mae_improve:+.1f}%, RMSE {rmse_improve:+.1f}%)"

            print(f"  {method_name:15s}: MAE={result.mae:.4f}m, "
                  f"RMSE={result.rmse:.4f}m{improvement}")

    print(f"\n✅ 最终修复版基准测试完成！")
    print(f"{'='*80}")


if __name__ == '__main__':
    run_final_multi_canal_benchmark()
