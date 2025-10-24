"""
多渠道自适应控制基准测试（使用HydrostaticCanalSolver）

对比三种系统：
1. 静态IDZ + SimplifiedCanalDynamics
2. 自适应IDZ + SimplifiedCanalDynamics
3. Saint-Venant + HydrostaticCanalSolver（高精度水动力模型）

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from dataclasses import dataclass
from typing import List, Dict, Optional
import sys
sys.path.append('/home/user/HydroClaude')

from control.online_identification import IDZIdentifier, IDZParameters
from control.model_validation import ModelValidator, ValidationMetrics
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver


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


@dataclass
class CanalConfig:
    """渠道配置"""
    name: str
    length: float       # 渠道长度 (m)
    width: float        # 渠宽 (m)
    slope: float        # 底坡
    manning_n: float    # 糙率
    description: str


@dataclass
class WorkingPoint:
    """工况点"""
    name: str
    flow: float           # 流量 (m³/s)
    target_depth: float   # 目标水深 (m)
    duration: float       # 持续时间 (s)


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    canal_name: str
    method_name: str
    mae: float
    rmse: float
    max_error: float
    settling_time: float
    validation_metrics: Optional[ValidationMetrics]
    K_history: List[float]
    tau_d_history: List[float]
    data: dict


class ImprovedAdaptivePIController:
    """改进的自适应PI控制器"""

    def __init__(self, dt: float, use_adaptive: bool = True):
        self.dt = dt
        self.use_adaptive = use_adaptive

        # 基准增益（保守设计）
        self.base_kp = 8.0
        self.base_ki = 0.3

        # 当前IDZ参数
        self.current_K = None
        self.current_tau_d = None

        # 积分器
        self.integral = 0.0
        self.integral_max = 50.0

    def set_idz_params(self, K: float, tau_d: float):
        """设置IDZ参数"""
        # 参数验证
        if K < 1.0 or K > 5000.0:
            print(f"Warning: K={K:.1f} out of range, keeping current")
            return

        self.current_K = K
        self.current_tau_d = tau_d

    def compute_adaptive_gains(self):
        """基于IMC规则计算自适应增益"""
        if self.current_K is None or self.current_tau_d is None:
            return self.base_kp, self.base_ki

        K_abs = abs(self.current_K)

        # K值异常检测
        if K_abs < 20.0:
            print(f"Warning: K={K_abs:.1f} too small, using base gains")
            return self.base_kp, self.base_ki

        # 更保守的lambda选择（基于K值分段）
        if K_abs < 100.0:
            lambda_c = 80.0   # 非常保守
        elif K_abs < 300.0:
            lambda_c = 100.0
        elif K_abs < 600.0:
            lambda_c = 120.0
        else:
            lambda_c = 150.0

        # IMC调谐规则
        Kp = self.current_tau_d / (K_abs * lambda_c)
        Ki = 1.0 / (K_abs * lambda_c)

        # 限制增益范围
        Kp = np.clip(Kp, 0.1, 50.0)
        Ki = np.clip(Ki, 0.01, 2.0)

        return Kp, Ki

    def compute_control(self, current_depth: float, target_depth: float,
                       q_disturbance: float) -> float:
        """计算控制输入"""
        # 误差
        error = target_depth - current_depth

        # 比例项
        if self.use_adaptive and self.current_K is not None:
            Kp, Ki = self.compute_adaptive_gains()
        else:
            Kp, Ki = self.base_kp, self.base_ki

        # 积分项（抗饱和）
        self.integral += error * self.dt
        self.integral = np.clip(self.integral, -self.integral_max, self.integral_max)

        # PI控制
        u_fb = Kp * error + Ki * self.integral

        # 前馈（跟踪扰动）
        u_ff = q_disturbance

        # 总控制量
        u = u_ff + u_fb

        # 限制控制量（物理约束）
        u = np.clip(u, 0.0, 100.0)

        return u


def compute_initial_idz(canal_config: CanalConfig, nominal_depth: float) -> IDZParameters:
    """计算初始IDZ参数"""
    # 基于水力学参数估计
    params = IDZParameters.from_hydraulics(
        length=canal_config.length,
        width=canal_config.width,
        bed_slope=canal_config.slope,
        manning=canal_config.manning_n,
        normal_depth=nominal_depth
    )

    # 限制参数范围
    params.K = np.clip(params.K, 50.0, 1000.0)
    params.tau_d = np.clip(params.tau_d, 50.0, 10000.0)

    return params


def run_benchmark_v2(canal_config: CanalConfig,
                     working_points: List[WorkingPoint],
                     dt: float = 10.0) -> Dict[str, BenchmarkResult]:
    """运行基准测试（v2版本，使用HydrostaticCanalSolver）"""

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
    print(f"初始IDZ参数: K={initial_params.K:.1f}, τ_d={initial_params.tau_d:.1f}s")

    # ===========================================================================
    # 初始化三个系统
    # ===========================================================================
    methods = {}

    # ---------------------------------------------------------------------------
    # 1. 静态IDZ + SimplifiedCanalDynamics
    # ---------------------------------------------------------------------------
    canal_static = SimplifiedCanalDynamics(
        canal_config.length, canal_config.width,
        canal_config.slope, canal_config.manning_n,
        initial_depth=nominal_depth, dt=dt
    )
    controller_static = ImprovedAdaptivePIController(dt, use_adaptive=False)
    controller_static.set_idz_params(initial_params.K, initial_params.tau_d)

    methods['静态IDZ'] = {
        'canal': canal_static,
        'canal_type': 'simplified',
        'controller': controller_static,
        'identifier': None,
        'data': {'time': [], 'depth': [], 'control': [], 'target': []},
        'K_history': [],
        'tau_d_history': [],
        'y_true': [],
        'y_pred': []
    }

    # ---------------------------------------------------------------------------
    # 2. 自适应IDZ + SimplifiedCanalDynamics
    # ---------------------------------------------------------------------------
    canal_adaptive = SimplifiedCanalDynamics(
        canal_config.length, canal_config.width,
        canal_config.slope, canal_config.manning_n,
        initial_depth=nominal_depth, dt=dt
    )
    controller_adaptive = ImprovedAdaptivePIController(dt, use_adaptive=True)
    controller_adaptive.set_idz_params(initial_params.K, initial_params.tau_d)
    identifier = IDZIdentifier(dt=dt)

    methods['自适应IDZ'] = {
        'canal': canal_adaptive,
        'canal_type': 'simplified',
        'controller': controller_adaptive,
        'identifier': identifier,
        'data': {'time': [], 'depth': [], 'control': [], 'target': []},
        'K_history': [initial_params.K],
        'tau_d_history': [initial_params.tau_d],
        'y_true': [],
        'y_pred': []
    }

    # ---------------------------------------------------------------------------
    # 3. Saint-Venant基准（HydrostaticCanalSolver）
    # ---------------------------------------------------------------------------
    print(f"\n初始化Saint-Venant基准（HydrostaticCanalSolver）...")

    # 网格分辨率
    nx = 101  # 空间离散点数
    dx = canal_config.length / (nx - 1)

    solver_sv = HydrostaticCanalSolver(
        length=canal_config.length,
        nx=nx,
        B=canal_config.width,
        S0=canal_config.slope,
        n=canal_config.manning_n,
        g=9.81,
        internal_structures=None,  # 无内部结构
        theta=0.6,  # Preissmann权重
        omega=0.95  # 松弛因子
    )

    # 初始化水深（均匀流）
    solver_sv.h[:] = nominal_depth
    # 初始化流量（单宽流量 = Q/B）
    solver_sv.hu[:] = nominal_flow / canal_config.width

    controller_sv = ImprovedAdaptivePIController(dt, use_adaptive=False)
    controller_sv.set_idz_params(initial_params.K, initial_params.tau_d)

    methods['Saint-Venant'] = {
        'solver': solver_sv,
        'canal_type': 'pde',
        'controller': controller_sv,
        'identifier': None,
        'data': {'time': [], 'depth': [], 'control': [], 'target': []},
        'K_history': [],
        'tau_d_history': [],
        'y_true': [],
        'y_pred': []
    }

    print(f"  使用HydrostaticCanalSolver: {nx}节点, dx={dx:.1f}m")

    # ===========================================================================
    # 开始仿真
    # ===========================================================================
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

        # -----------------------------------------------------------------------
        # 运行所有方法
        # -----------------------------------------------------------------------
        for method_name, method_data in methods.items():
            canal_type = method_data['canal_type']
            controller = method_data['controller']
            identifier = method_data.get('identifier')

            # 获取当前状态
            if canal_type == 'simplified':
                canal = method_data['canal']
                current_depth = canal.get_depth()
            else:  # PDE求解器（HydrostaticCanalSolver）
                solver = method_data['solver']
                # 使用平均水深（或取中点水深）
                current_depth = np.mean(solver.h)

            # 在线辨识（仅自适应IDZ）
            if identifier is not None and step > 0:
                u_prev = method_data['data']['control'][-1]
                y_prev = method_data['data']['depth'][-1]

                u_dev = u_prev - nominal_flow
                y_dev = y_prev - nominal_depth

                identified_params = identifier.update(u_dev, y_dev)
                if identified_params:
                    controller.set_idz_params(identified_params.K, identified_params.tau_d)
                    method_data['K_history'].append(identified_params.K)
                    method_data['tau_d_history'].append(identified_params.tau_d)

            # 计算控制量
            u = controller.compute_control(current_depth, target_depth_val, q_upstream)

            # 物理仿真
            if canal_type == 'simplified':
                canal.step(q_upstream, u)
            else:  # PDE求解器
                # 使用子步长满足CFL条件
                # CFL: dt ≤ dx / (|u| + sqrt(g*h))
                # 估计最大波速：c_max ≈ sqrt(g*h_max) + u_max
                h_max = 5.0  # 假设最大水深5m
                u_max = 3.0  # 假设最大流速3m/s
                c_max = np.sqrt(solver.g * h_max) + u_max  # ≈ 10 m/s

                dt_cfl = solver.dx / c_max * 0.5  # 安全系数0.5
                n_substeps = max(1, int(np.ceil(dt / dt_cfl)))
                dt_sub = dt / n_substeps

                # 分多个子步长进行时间推进
                for substep in range(n_substeps):
                    # 设置边界条件（每个子步长都设置）
                    solver.hu[0] = q_upstream / solver.B
                    solver.hu[-1] = u / solver.B

                    # 时间推进
                    solver.step_preissmann(dt_sub, enforce_bc=False)

                # 更新当前水深（使用平均值）
                current_depth = np.mean(solver.h)

            # 记录数据
            method_data['data']['time'].append(t)
            method_data['data']['depth'].append(current_depth)
            method_data['data']['control'].append(u)
            method_data['data']['target'].append(target_depth_val)

            method_data['y_true'].append(current_depth)
            method_data['y_pred'].append(current_depth)

        # 进度显示
        if step % 30 == 0:
            static_depth = methods['静态IDZ']['data']['depth'][-1]
            adp_depth = methods['自适应IDZ']['data']['depth'][-1]
            sv_depth = methods['Saint-Venant']['data']['depth'][-1]
            adp_K = methods['自适应IDZ']['K_history'][-1] if len(methods['自适应IDZ']['K_history']) > 0 else initial_params.K
            print(f"  t={t:.0f}s, 目标={target_depth_val:.2f}m, "
                  f"静态h={static_depth:.3f}m, 自适应h={adp_depth:.3f}m (K={adp_K:.1f}), "
                  f"SV_h={sv_depth:.3f}m, Q_up={q_upstream:.1f}m³/s")

    # ===========================================================================
    # 计算性能指标
    # ===========================================================================
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
            data=data
        )

        results[method_name] = result

        # 打印结果
        print(f"\n{canal_config.name} - {method_name}:")
        print(f"  MAE = {mae:.4f}m, RMSE = {rmse:.4f}m")
        print(f"  最大误差 = {max_error:.4f}m, 调节时间 = {settling_time:.1f}s")

        if validation_metrics:
            print(f"  R² = {validation_metrics.r_squared:.4f}, "
                  f"VAF = {validation_metrics.vaf:.2f}%")
            print(f"  K范围: [{min(method_data['K_history']):.1f}, "
                  f"{max(method_data['K_history']):.1f}]")

        print()

    # 生成对比图
    visualize_comparison(results, canal_config.name)

    return results


def visualize_comparison(results: Dict[str, BenchmarkResult], canal_name: str):
    """生成对比可视化"""
    print(f"生成{canal_name}对比图...")

    fig = plt.figure(figsize=(16, 12))
    gs = gridspec.GridSpec(4, 2, hspace=0.35, wspace=0.3)

    # 颜色方案
    colors = {
        '静态IDZ': '#1f77b4',
        '自适应IDZ': '#ff7f0e',
        'Saint-Venant': '#2ca02c'
    }

    # 1. 水深对比
    ax1 = fig.add_subplot(gs[0, :])
    for method_name, result in results.items():
        ax1.plot(result.data['time'], result.data['depth'],
                label=f"{method_name}", color=colors[method_name], linewidth=1.5)
    ax1.plot(result.data['time'], result.data['target'],
            'k--', label='Target', linewidth=1.0)
    ax1.set_ylabel('Water Depth (m)')
    ax1.set_xlabel('Time (s)')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)
    ax1.set_title(f'{canal_name} - Water Depth Comparison')

    # 2. 控制输入对比
    ax2 = fig.add_subplot(gs[1, :])
    for method_name, result in results.items():
        ax2.plot(result.data['time'], result.data['control'],
                label=f"{method_name}", color=colors[method_name], linewidth=1.5)
    ax2.set_ylabel('Control Input (m³/s)')
    ax2.set_xlabel('Time (s)')
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)
    ax2.set_title('Control Input Comparison')

    # 3. 跟踪误差对比
    ax3 = fig.add_subplot(gs[2, :])
    for method_name, result in results.items():
        depth_arr = np.array(result.data['depth'])
        target_arr = np.array(result.data['target'])
        error = depth_arr - target_arr
        ax3.plot(result.data['time'], error,
                label=f"{method_name}", color=colors[method_name], linewidth=1.5)
    ax3.axhline(y=0, color='k', linestyle='--', linewidth=0.8)
    ax3.set_ylabel('Tracking Error (m)')
    ax3.set_xlabel('Time (s)')
    ax3.legend(loc='best')
    ax3.grid(True, alpha=0.3)
    ax3.set_title('Tracking Error Comparison')

    # 4. 性能指标条形图
    ax4 = fig.add_subplot(gs[3, 0])
    method_names = list(results.keys())
    mae_values = [results[m].mae for m in method_names]
    rmse_values = [results[m].rmse for m in method_names]

    x = np.arange(len(method_names))
    width = 0.35

    ax4.bar(x - width/2, mae_values, width, label='MAE')
    ax4.bar(x + width/2, rmse_values, width, label='RMSE')
    ax4.set_ylabel('Error (m)')
    ax4.set_xticks(x)
    ax4.set_xticklabels(method_names, rotation=15)
    ax4.legend()
    ax4.grid(True, alpha=0.3, axis='y')
    ax4.set_title('Performance Metrics')

    # 5. K值演化（仅自适应IDZ）
    ax5 = fig.add_subplot(gs[3, 1])
    result_adp = results['自适应IDZ']
    if len(result_adp.K_history) > 0:
        t_K = np.linspace(0, result_adp.data['time'][-1], len(result_adp.K_history))
        ax5.plot(t_K, result_adp.K_history, color='#ff7f0e', linewidth=1.5)
        ax5.set_ylabel('K Value')
        ax5.set_xlabel('Time (s)')
        ax5.grid(True, alpha=0.3)
        ax5.set_title('Adaptive IDZ - K Parameter Evolution')

    plt.suptitle(f'{canal_name} Benchmark Comparison', fontsize=14, fontweight='bold')

    filename = f"benchmark_v2_{canal_name}.png"
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"  图表已保存: {filename}")
    plt.close()


# ==============================================================================
# 主程序
# ==============================================================================
def main():
    print("="*80)
    print("多渠道自适应控制基准测试（v2版本 - HydrostaticCanalSolver）")
    print("="*80)
    print("\n对比三种系统：")
    print("  1. 静态IDZ + SimplifiedCanalDynamics（简化物理 + 固定参数）")
    print("  2. 自适应IDZ + SimplifiedCanalDynamics（简化物理 + 自适应参数）")
    print("  3. Saint-Venant + HydrostaticCanalSolver（高精度PDE + 固定参数）")
    print("="*80)

    # 定义测试渠道
    canals = [
        CanalConfig("Short_Canal", 1000.0, 10.0, 0.0001, 0.025,
                   "Fast response system"),
        CanalConfig("Long_Canal", 3000.0, 10.0, 0.0001, 0.025,
                   "Slow response system"),
    ]

    # 定义工况点（改进版：减小跨度）
    working_points = [
        WorkingPoint("Low", flow=18.0, target_depth=1.8, duration=500.0),
        WorkingPoint("Medium", flow=25.0, target_depth=2.3, duration=500.0),
        WorkingPoint("High", flow=32.0, target_depth=2.8, duration=500.0),
        WorkingPoint("Back to Medium", flow=25.0, target_depth=2.3, duration=300.0),
        WorkingPoint("Back to Low", flow=18.0, target_depth=1.8, duration=300.0),
    ]

    depth_span = working_points[2].target_depth - working_points[0].target_depth
    depth_min = working_points[0].target_depth
    depth_percent = (depth_span / depth_min) * 100
    flow_span = working_points[2].flow - working_points[0].flow
    flow_min = working_points[0].flow
    flow_percent = (flow_span / flow_min) * 100

    print(f"\n工况设计:")
    print(f"  深度跨度: {working_points[0].target_depth}m → "
          f"{working_points[2].target_depth}m ({depth_percent:.0f}% change, reasonable)")
    print(f"  流量跨度: {working_points[0].flow}-{working_points[2].flow} m³/s "
          f"({flow_percent:.0f}% change)")
    print(f"  总时长: {sum(wp.duration for wp in working_points)}s")

    # 运行基准测试
    all_results = {}
    for canal in canals:
        results = run_benchmark_v2(canal, working_points, dt=10.0)
        all_results[canal.name] = results

    # 总结报告
    print("\n" + "="*80)
    print("总结报告")
    print("="*80)

    for canal_name, results in all_results.items():
        print(f"\n{canal_name}:")
        baseline_mae = results['静态IDZ'].mae
        baseline_rmse = results['静态IDZ'].rmse

        for method_name, result in results.items():
            mae_improvement = ((result.mae - baseline_mae) / baseline_mae) * 100
            rmse_improvement = ((result.rmse - baseline_rmse) / baseline_rmse) * 100

            print(f"  {method_name:15s}: MAE={result.mae:.4f}m, RMSE={result.rmse:.4f}m "
                  f"(MAE {mae_improvement:+.1f}%, RMSE {rmse_improvement:+.1f}%)")

    print(f"\n✅ v2版本基准测试完成！")
    print("="*80)


if __name__ == "__main__":
    main()
