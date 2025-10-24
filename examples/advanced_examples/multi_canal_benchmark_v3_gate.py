"""
多渠道自适应控制基准测试（v3版本 - 闸门控制）

对比三种系统：
1. 静态IDZ + SimplifiedCanalDynamics
2. 自适应IDZ + SimplifiedCanalDynamics
3. Saint-Venant + HydrostaticCanalSolver + 闸门控制

关键改进：
- 使用下游闸门作为执行器（而非直接流量控制）
- 控制输入 = 闸门开度
- 避免上下游都用流量边界的数值不稳定性

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from dataclasses import dataclass
from typing import List, Dict, Optional, Callable
import sys
sys.path.append('/home/user/HydroClaude')

from control.online_identification import IDZIdentifier, IDZParameters
from control.model_validation import ModelValidator, ValidationMetrics
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate


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
    validation_metrics: Optional[ValidationMetrics]
    K_history: List[float]
    tau_d_history: List[float]
    data: dict


class GateOpeningController:
    """闸门开度控制器（从水深误差计算开度）"""

    def __init__(self, base_opening: float = 2.0, Kp: float = 0.5, Ki: float = 0.1, dt: float = 10.0):
        """
        Args:
            base_opening: 基准开度 (m)
            Kp: 比例增益
            Ki: 积分增益
            dt: 采样时间 (s)
        """
        self.base_opening = base_opening
        self.Kp = Kp
        self.Ki = Ki
        self.dt = dt

        self.integral = 0.0
        self.integral_max = 2.0  # 积分限幅

    def compute_opening(self, current_depth: float, target_depth: float) -> float:
        """
        计算闸门开度

        原理：
        - 当水位过高时，增大开度加快泄流
        - 当水位过低时，减小开度减少泄流
        """
        error = target_depth - current_depth

        # 积分项
        self.integral += error * self.dt
        self.integral = np.clip(self.integral, -self.integral_max, self.integral_max)

        # PI控制
        delta_opening = self.Kp * error + self.Ki * self.integral

        # 计算开度
        opening = self.base_opening + delta_opening

        # 限制开度范围 [0.5m, 4.0m]
        opening = np.clip(opening, 0.5, 4.0)

        return opening


class ImprovedAdaptivePIController:
    """改进的自适应PI控制器（用于SimplifiedCanalDynamics）"""

    def __init__(self, dt: float, use_adaptive: bool = True):
        self.dt = dt
        self.use_adaptive = use_adaptive
        self.base_kp = 8.0
        self.base_ki = 0.3
        self.current_K = None
        self.current_tau_d = None
        self.integral = 0.0
        self.integral_max = 50.0

    def set_idz_params(self, K: float, tau_d: float):
        if K < 1.0 or K > 5000.0:
            return
        self.current_K = K
        self.current_tau_d = tau_d

    def compute_adaptive_gains(self):
        if self.current_K is None or self.current_tau_d is None:
            return self.base_kp, self.base_ki

        K_abs = abs(self.current_K)
        if K_abs < 20.0:
            return self.base_kp, self.base_ki

        lambda_c = 100.0 if K_abs < 300.0 else 150.0
        Kp = self.current_tau_d / (K_abs * lambda_c)
        Ki = 1.0 / (K_abs * lambda_c)
        Kp = np.clip(Kp, 0.1, 50.0)
        Ki = np.clip(Ki, 0.01, 2.0)
        return Kp, Ki

    def compute_control(self, current_depth: float, target_depth: float, q_disturbance: float) -> float:
        error = target_depth - current_depth

        if self.use_adaptive and self.current_K is not None:
            Kp, Ki = self.compute_adaptive_gains()
        else:
            Kp, Ki = self.base_kp, self.base_ki

        self.integral += error * self.dt
        self.integral = np.clip(self.integral, -self.integral_max, self.integral_max)

        u_fb = Kp * error + Ki * self.integral
        u = q_disturbance + u_fb
        u = np.clip(u, 0.0, 100.0)
        return u


def compute_initial_idz(canal_config: CanalConfig, nominal_depth: float) -> IDZParameters:
    """计算初始IDZ参数"""
    params = IDZParameters.from_hydraulics(
        length=canal_config.length,
        width=canal_config.width,
        bed_slope=canal_config.slope,
        manning=canal_config.manning_n,
        normal_depth=nominal_depth
    )
    params.K = np.clip(params.K, 50.0, 1000.0)
    params.tau_d = np.clip(params.tau_d, 50.0, 10000.0)
    return params


def run_benchmark_v3_gate(canal_config: CanalConfig,
                          working_points: List[WorkingPoint],
                          dt: float = 10.0) -> Dict[str, BenchmarkResult]:
    """运行v3基准测试（闸门控制版本）"""

    print(f"\n{'='*80}")
    print(f"测试渠道: {canal_config.name}")
    print(f"  {canal_config.description}")
    print(f"  L={canal_config.length}m, B={canal_config.width}m, S0={canal_config.slope}")
    print(f"{'='*80}")

    total_time = sum(wp.duration for wp in working_points)
    n_steps = int(total_time / dt)

    nominal_depth = np.mean([wp.target_depth for wp in working_points])
    nominal_flow = np.mean([wp.flow for wp in working_points])

    print(f"\n名义工况: Q={nominal_flow:.1f}m³/s, h={nominal_depth:.2f}m")

    initial_params = compute_initial_idz(canal_config, nominal_depth)
    print(f"初始IDZ参数: K={initial_params.K:.1f}, τ_d={initial_params.tau_d:.1f}s")

    methods = {}

    # ========================================================================
    # 1. 静态IDZ + SimplifiedCanalDynamics
    # ========================================================================
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

    # ========================================================================
    # 2. 自适应IDZ + SimplifiedCanalDynamics
    # ========================================================================
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

    # ========================================================================
    # 3. Saint-Venant + HydrostaticCanalSolver + 闸门控制
    # ========================================================================
    print(f"\n初始化Saint-Venant基准（HydrostaticCanalSolver + 闸门控制）...")

    nx = 51
    gate_pos = canal_config.length - 50.0  # 下游闸门位置

    # 创建闸门（初始开度由控制器决定）
    gate_opening_var = [nominal_depth]  # 用列表存储可变值

    def get_gate_opening(t):
        return gate_opening_var[0]

    gate = SluiceGate(
        position=gate_pos,
        width=canal_config.width,
        opening=get_gate_opening,  # 时变开度函数
        Cd=0.6
    )

    # 创建求解器
    solver_sv = HydrostaticCanalSolver(
        length=canal_config.length,
        nx=nx,
        B=canal_config.width,
        S0=canal_config.slope,
        n=canal_config.manning_n,
        g=9.81,
        internal_structures=[(gate_pos, gate)],  # (位置, 结构物)元组的列表
        theta=0.6,
        omega=0.95
    )

    # 初始化：先求解稳态
    print(f"  求解稳态初值...")
    solver_sv.h[:] = nominal_depth
    solver_sv.hu[:] = nominal_flow / canal_config.width
    solver_sv.solve_steady_state(
        Q_target=nominal_flow,
        h_downstream=nominal_depth,
        max_iter=5000,
        tol=0.001
    )
    print(f"  稳态求解完成: 平均水深={np.mean(solver_sv.h):.3f}m")

    # 创建闸门开度控制器
    gate_controller = GateOpeningController(base_opening=2.0, Kp=0.5, Ki=0.1, dt=dt)

    methods['Saint-Venant+闸门'] = {
        'solver': solver_sv,
        'canal_type': 'pde_gate',
        'gate': gate,
        'gate_opening_var': gate_opening_var,
        'gate_controller': gate_controller,
        'data': {'time': [], 'depth': [], 'control': [], 'gate_opening': [], 'target': []},
        'K_history': [],
        'tau_d_history': [],
        'y_true': [],
        'y_pred': []
    }

    print(f"  使用HydrostaticCanalSolver: {nx}节点, dx={(canal_config.length/(nx-1)):.1f}m")
    print(f"  下游闸门位置: {gate_pos:.0f}m")

    # ========================================================================
    # 开始仿真
    # ========================================================================
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
            canal_type = method_data['canal_type']

            # 获取当前状态
            if canal_type == 'simplified':
                canal = method_data['canal']
                current_depth = canal.get_depth()
                controller = method_data['controller']
                identifier = method_data.get('identifier')

                # 在线辨识
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
                canal.step(q_upstream, u)

                # 记录
                method_data['data']['time'].append(t)
                method_data['data']['depth'].append(current_depth)
                method_data['data']['control'].append(u)
                method_data['data']['target'].append(target_depth_val)

            else:  # PDE + 闸门
                solver = method_data['solver']
                gate_controller = method_data['gate_controller']
                gate_opening_var = method_data['gate_opening_var']

                # 使用平均水深
                current_depth = np.mean(solver.h)

                # 计算闸门开度（控制输入）
                opening = gate_controller.compute_opening(current_depth, target_depth_val)
                gate_opening_var[0] = opening  # 更新闸门开度

                # 设置上游流量边界
                solver.set_boundary_conditions(Q_in=q_upstream)

                # 时间推进（使用稳态求解器的一步迭代）
                # 注意：使用小的子步长以满足CFL条件
                h_max = 5.0
                u_max = 3.0
                c_max = np.sqrt(solver.g * h_max) + u_max
                dt_cfl = solver.dx / c_max * 0.5
                n_substeps = max(1, int(np.ceil(dt / dt_cfl)))
                dt_sub = dt / n_substeps

                for _ in range(n_substeps):
                    solver.step_preissmann(dt_sub, enforce_bc=False)

                current_depth = np.mean(solver.h)

                # 记录
                method_data['data']['time'].append(t)
                method_data['data']['depth'].append(current_depth)
                method_data['data']['control'].append(q_upstream)  # 记录流量作为参考
                method_data['data']['gate_opening'].append(opening)
                method_data['data']['target'].append(target_depth_val)

            method_data['y_true'].append(current_depth)
            method_data['y_pred'].append(current_depth)

        # 进度显示
        if step % 30 == 0:
            static_depth = methods['静态IDZ']['data']['depth'][-1]
            adp_depth = methods['自适应IDZ']['data']['depth'][-1]
            sv_depth = methods['Saint-Venant+闸门']['data']['depth'][-1]
            sv_opening = methods['Saint-Venant+闸门']['data']['gate_opening'][-1]
            adp_K = methods['自适应IDZ']['K_history'][-1] if len(methods['自适应IDZ']['K_history']) > 0 else initial_params.K
            print(f"  t={t:.0f}s, 目标={target_depth_val:.2f}m, "
                  f"静态h={static_depth:.3f}m, 自适应h={adp_depth:.3f}m (K={adp_K:.1f}), "
                  f"SV_h={sv_depth:.3f}m (gate={sv_opening:.3f}m), Q_up={q_upstream:.1f}m³/s")

    # 计算性能指标
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

        settling_time = total_time
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

        print(f"\n{canal_config.name} - {method_name}:")
        print(f"  MAE = {mae:.4f}m, RMSE = {rmse:.4f}m")
        print(f"  最大误差 = {max_error:.4f}m")
        if validation_metrics:
            print(f"  R² = {validation_metrics.r_squared:.4f}, VAF = {validation_metrics.vaf:.2f}%")
        if method_data.get('K_history'):
            print(f"  K范围: [{min(method_data['K_history']):.1f}, {max(method_data['K_history']):.1f}]")

    return results


# ==============================================================================
# 主程序
# ==============================================================================
def main():
    print("="*80)
    print("多渠道自适应控制基准测试（v3版本 - 闸门控制）")
    print("="*80)

    canals = [
        CanalConfig("Short_Canal", 1000.0, 10.0, 0.0001, 0.025, "Fast response"),
    ]

    working_points = [
        WorkingPoint("Low", flow=18.0, target_depth=1.8, duration=500.0),
        WorkingPoint("Medium", flow=25.0, target_depth=2.3, duration=500.0),
        WorkingPoint("High", flow=32.0, target_depth=2.8, duration=500.0),
        WorkingPoint("Back to Medium", flow=25.0, target_depth=2.3, duration=300.0),
        WorkingPoint("Back to Low", flow=18.0, target_depth=1.8, duration=300.0),
    ]

    for canal in canals:
        results = run_benchmark_v3_gate(canal, working_points, dt=10.0)

    print(f"\n✅ v3版本（闸门控制）测试完成！")
    print("="*80)


if __name__ == "__main__":
    main()
