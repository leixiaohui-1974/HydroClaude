#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模型预测控制（MPC）智能调度器

基于现有求解器实现水利工程智能调度：
- 使用HydrostaticCanalSolver作为预测模型
- 滚动时域优化控制策略
- 支持多目标约束优化（水位、流量、闸门开度）
- 实时反馈调节

作者: Claude
日期: 2025-10-23
"""

import numpy as np
from scipy.optimize import minimize, differential_evolution
from typing import List, Dict, Tuple, Callable
import copy
import warnings

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate


class MPCScheduler:
    """
    模型预测控制（MPC）调度器

    使用现有的HydrostaticCanalSolver作为预测模型，
    通过优化控制序列（闸门开度、入流流量等）来实现调度目标。

    核心思想：
    1. 使用求解器预测未来状态
    2. 优化控制序列以达到目标
    3. 执行第一个控制动作
    4. 状态反馈，重复上述过程（滚动时域）
    """

    def __init__(
        self,
        solver: HydrostaticCanalSolver,
        prediction_horizon: int = 10,
        control_horizon: int = 5,
        dt: float = 1.0,
        verbose: bool = True
    ):
        """
        初始化MPC调度器

        Args:
            solver: 用于预测的求解器（作为"数字模型"）
            prediction_horizon: 预测时域长度（步数）
            control_horizon: 控制时域长度（步数，≤预测时域）
            dt: 时间步长（秒）
            verbose: 是否输出详细信息
        """
        self.solver = solver
        self.N_pred = prediction_horizon
        self.N_ctrl = min(control_horizon, prediction_horizon)
        self.dt = dt
        self.verbose = verbose

        # 目标和权重
        self.target_depths: Dict[int, float] = {}  # {网格点索引: 目标水深}
        self.target_flows: Dict[int, float] = {}   # {网格点索引: 目标流量}

        self.weight_depth = 1.0
        self.weight_flow = 1.0
        self.weight_control_change = 0.1  # 控制变化惩罚（平滑控制）

        # 控制变量索引
        self.controllable_gates: List[SluiceGate] = []
        self.controllable_inflows: List[int] = []  # 可控入流点索引

        # 约束
        self.gate_opening_bounds: Dict[SluiceGate, Tuple[float, float]] = {}
        self.inflow_bounds: Tuple[float, float] = (0.0, 100.0)

        # 历史记录
        self.history = {
            'time': [],
            'controls': [],
            'states': [],
            'costs': [],
            'targets_achieved': []
        }

    def set_targets(
        self,
        depth_targets: Dict[int, float] = None,
        flow_targets: Dict[int, float] = None
    ):
        """
        设置控制目标

        Args:
            depth_targets: {网格点索引: 目标水深 (m)}
            flow_targets: {网格点索引: 目标流量 (m³/s)}
        """
        if depth_targets is not None:
            self.target_depths = depth_targets
        if flow_targets is not None:
            self.target_flows = flow_targets

    def set_weights(
        self,
        w_depth: float = 1.0,
        w_flow: float = 1.0,
        w_control_change: float = 0.1
    ):
        """设置目标函数权重"""
        self.weight_depth = w_depth
        self.weight_flow = w_flow
        self.weight_control_change = w_control_change

    def add_controllable_gate(
        self,
        gate: SluiceGate,
        opening_min: float = 0.1,
        opening_max: float = 2.0
    ):
        """
        添加可控闸门

        Args:
            gate: 闸门对象
            opening_min: 最小开度 (m)
            opening_max: 最大开度 (m)
        """
        self.controllable_gates.append(gate)
        self.gate_opening_bounds[gate] = (opening_min, opening_max)

    def add_controllable_inflow(
        self,
        grid_index: int = 0,
        Q_min: float = 0.0,
        Q_max: float = 100.0
    ):
        """
        添加可控入流点

        Args:
            grid_index: 网格点索引（通常是0，即上游入口）
            Q_min: 最小流量 (m³/s)
            Q_max: 最大流量 (m³/s)
        """
        self.controllable_inflows.append(grid_index)
        self.inflow_bounds = (Q_min, Q_max)

    def _decode_control_vector(self, u: np.ndarray) -> Dict:
        """
        解码控制向量为实际控制变量

        控制向量结构：
        [gate1_opening_t0, gate1_opening_t1, ..., gate1_opening_t(N_ctrl-1),
         gate2_opening_t0, ...,
         inflow_t0, inflow_t1, ..., inflow_t(N_ctrl-1)]

        Args:
            u: 控制向量

        Returns:
            Dict containing gate openings and inflows over control horizon
        """
        n_gates = len(self.controllable_gates)
        n_inflows = len(self.controllable_inflows)

        controls = {
            'gate_openings': {},  # {gate: [opening_t0, opening_t1, ...]}
            'inflows': {}         # {grid_idx: [Q_t0, Q_t1, ...]}
        }

        idx = 0

        # 解码闸门开度
        for gate in self.controllable_gates:
            openings = u[idx:idx + self.N_ctrl]
            controls['gate_openings'][gate] = openings
            idx += self.N_ctrl

        # 解码入流
        for grid_idx in self.controllable_inflows:
            inflows = u[idx:idx + self.N_ctrl]
            controls['inflows'][grid_idx] = inflows
            idx += self.N_ctrl

        return controls

    def _predict_trajectory(
        self,
        initial_state: Tuple[np.ndarray, np.ndarray],
        controls: Dict
    ) -> Tuple[List[np.ndarray], List[np.ndarray]]:
        """
        使用求解器预测未来轨迹

        Args:
            initial_state: (h_initial, hu_initial)
            controls: 控制序列字典

        Returns:
            h_trajectory: 水深轨迹 [h_0, h_1, ..., h_N]
            Q_trajectory: 流量轨迹 [Q_0, Q_1, ..., Q_N]
        """
        # 创建求解器副本（避免修改原求解器）
        solver_copy = copy.deepcopy(self.solver)
        solver_copy.h = initial_state[0].copy()
        solver_copy.hu = initial_state[1].copy()

        h_trajectory = [solver_copy.h.copy()]
        Q_trajectory = [solver_copy.hu * solver_copy.B]

        # 模拟预测时域
        for t in range(self.N_pred):
            # 确定当前控制（如果超过控制时域，保持最后一个控制）
            t_ctrl = min(t, self.N_ctrl - 1)

            # 应用闸门开度控制
            for gate, openings in controls['gate_openings'].items():
                # 设置闸门开度（通过修改opening_func）
                opening_value = openings[t_ctrl]
                gate.opening_func = lambda t, val=opening_value: val

            # 应用入流控制
            Q_upstream = None
            for grid_idx, inflows in controls['inflows'].items():
                if grid_idx == 0:  # 上游入流
                    Q_upstream = inflows[t_ctrl]

            # 执行一步预测（使用Preissmann隐式格式）
            try:
                # 使用当前边界条件进行预测
                h_downstream = solver_copy.h[-1]  # 简化：使用当前下游水深

                h_new, hu_new = solver_copy.step_preissmann(
                    dt=self.dt,
                    max_iter=10,
                    enforce_bc=True,
                    Q_in=Q_upstream,
                    h_out=h_downstream
                )

                # 更新求解器状态
                solver_copy.h = h_new
                solver_copy.hu = hu_new

                h_trajectory.append(solver_copy.h.copy())
                Q_trajectory.append(solver_copy.hu * solver_copy.B)

            except Exception as e:
                if self.verbose:
                    warnings.warn(f"预测步 {t} 失败: {e}")
                # 如果预测失败，返回当前轨迹
                break

        return h_trajectory, Q_trajectory

    def _compute_cost(
        self,
        h_trajectory: List[np.ndarray],
        Q_trajectory: List[np.ndarray],
        controls: Dict,
        u_prev: np.ndarray = None
    ) -> float:
        """
        计算代价函数

        代价 = Σ(水深偏差² + 流量偏差² + 控制变化²)

        Args:
            h_trajectory: 预测的水深轨迹
            Q_trajectory: 预测的流量轨迹
            controls: 控制序列
            u_prev: 上一时刻的控制向量（用于计算控制变化）

        Returns:
            总代价
        """
        cost = 0.0

        # 1. 跟踪误差（水深目标）
        if self.target_depths:
            for idx, target_h in self.target_depths.items():
                for h in h_trajectory:
                    error = h[idx] - target_h
                    cost += self.weight_depth * error**2

        # 2. 跟踪误差（流量目标）
        if self.target_flows:
            for idx, target_Q in self.target_flows.items():
                for Q in Q_trajectory:
                    error = Q[idx] - target_Q
                    cost += self.weight_flow * error**2

        # 3. 控制平滑性（避免剧烈变化）
        if u_prev is not None:
            # 计算当前控制向量
            u_current = self._encode_controls(controls)

            # 只对第一个控制动作计算变化
            n_controls_per_step = len(self.controllable_gates) + len(self.controllable_inflows)
            u_curr_first = u_current[:n_controls_per_step]
            u_prev_first = u_prev[:n_controls_per_step]

            control_change = np.sum((u_curr_first - u_prev_first)**2)
            cost += self.weight_control_change * control_change

        return cost

    def _encode_controls(self, controls: Dict) -> np.ndarray:
        """将控制字典编码为向量"""
        u = []
        for gate in self.controllable_gates:
            u.extend(controls['gate_openings'][gate])
        for grid_idx in self.controllable_inflows:
            u.extend(controls['inflows'][grid_idx])
        return np.array(u)

    def _objective_function(
        self,
        u: np.ndarray,
        initial_state: Tuple[np.ndarray, np.ndarray],
        u_prev: np.ndarray = None
    ) -> float:
        """
        优化目标函数

        Args:
            u: 控制向量
            initial_state: 初始状态
            u_prev: 上一时刻控制向量

        Returns:
            代价值
        """
        # 解码控制
        controls = self._decode_control_vector(u)

        # 预测轨迹
        h_traj, Q_traj = self._predict_trajectory(initial_state, controls)

        # 计算代价
        cost = self._compute_cost(h_traj, Q_traj, controls, u_prev)

        return cost

    def _get_bounds(self) -> List[Tuple[float, float]]:
        """获取优化变量边界"""
        bounds = []

        # 闸门开度边界
        for gate in self.controllable_gates:
            opening_min, opening_max = self.gate_opening_bounds[gate]
            bounds.extend([(opening_min, opening_max)] * self.N_ctrl)

        # 入流边界
        for _ in self.controllable_inflows:
            Q_min, Q_max = self.inflow_bounds
            bounds.extend([(Q_min, Q_max)] * self.N_ctrl)

        return bounds

    def optimize_step(
        self,
        current_state: Tuple[np.ndarray, np.ndarray],
        u_prev: np.ndarray = None,
        method: str = 'SLSQP'
    ) -> Tuple[np.ndarray, Dict]:
        """
        执行一次MPC优化步骤

        Args:
            current_state: 当前状态 (h, hu)
            u_prev: 上一时刻控制向量
            method: 优化方法 ('SLSQP', 'differential_evolution')

        Returns:
            optimal_u: 最优控制向量
            info: 优化信息
        """
        # 初始猜测（如果有上一时刻控制，则基于它；否则使用中间值）
        if u_prev is not None:
            u0 = u_prev.copy()
        else:
            bounds = self._get_bounds()
            u0 = np.array([(lb + ub) / 2 for lb, ub in bounds])

        # 边界约束
        bounds = self._get_bounds()

        # 优化
        if method == 'SLSQP':
            result = minimize(
                fun=self._objective_function,
                x0=u0,
                args=(current_state, u_prev),
                method='SLSQP',
                bounds=bounds,
                options={'maxiter': 100, 'ftol': 1e-6}
            )
            optimal_u = result.x
            info = {
                'success': result.success,
                'cost': result.fun,
                'iterations': result.nit,
                'message': result.message
            }

        elif method == 'differential_evolution':
            result = differential_evolution(
                func=self._objective_function,
                bounds=bounds,
                args=(current_state, u_prev),
                maxiter=50,
                popsize=10,
                tol=1e-3,
                seed=42
            )
            optimal_u = result.x
            info = {
                'success': result.success,
                'cost': result.fun,
                'iterations': result.nit,
                'message': result.message
            }

        else:
            raise ValueError(f"不支持的优化方法: {method}")

        return optimal_u, info

    def apply_control(
        self,
        optimal_u: np.ndarray,
        apply_to_solver: bool = True
    ) -> Dict:
        """
        应用第一个控制动作

        Args:
            optimal_u: 最优控制向量
            apply_to_solver: 是否应用到实际求解器

        Returns:
            应用的控制值字典
        """
        controls = self._decode_control_vector(optimal_u)

        applied_controls = {
            'gate_openings': {},
            'inflows': {}
        }

        # 应用闸门开度（第一个时间步）
        for gate in self.controllable_gates:
            opening_t0 = controls['gate_openings'][gate][0]
            applied_controls['gate_openings'][gate] = opening_t0

            if apply_to_solver:
                gate.opening_func = lambda t, val=opening_t0: val

        # 应用入流（第一个时间步）
        for grid_idx in self.controllable_inflows:
            inflow_t0 = controls['inflows'][grid_idx][0]
            applied_controls['inflows'][grid_idx] = inflow_t0

        return applied_controls

    def run_closed_loop(
        self,
        t_end: float,
        initial_state: Tuple[np.ndarray, np.ndarray],
        optimization_method: str = 'SLSQP',
        feedback_interval: int = 1
    ) -> Dict:
        """
        运行闭环MPC控制

        Args:
            t_end: 仿真结束时间 (s)
            initial_state: 初始状态 (h, hu)
            optimization_method: 优化方法
            feedback_interval: 反馈间隔（每几个时间步重新优化一次）

        Returns:
            结果字典，包含时间历史、状态历史、控制历史等
        """
        # 初始化
        self.solver.h = initial_state[0].copy()
        self.solver.hu = initial_state[1].copy()

        n_steps = int(t_end / self.dt)
        u_prev = None

        # 清空历史记录
        self.history = {
            'time': [],
            'h_history': [],
            'Q_history': [],
            'controls': [],
            'costs': [],
            'optimization_info': []
        }

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"MPC 闭环控制开始")
            print(f"{'='*60}")
            print(f"预测时域: {self.N_pred} 步 ({self.N_pred * self.dt:.1f} s)")
            print(f"控制时域: {self.N_ctrl} 步 ({self.N_ctrl * self.dt:.1f} s)")
            print(f"总仿真时长: {t_end:.1f} s ({n_steps} 步)")
            print(f"反馈间隔: {feedback_interval} 步")
            print(f"{'='*60}\n")

        # 主循环
        for step in range(n_steps):
            t_current = step * self.dt

            # 记录当前状态
            self.history['time'].append(t_current)
            self.history['h_history'].append(self.solver.h.copy())
            self.history['Q_history'].append(self.solver.hu * self.solver.B)

            # 每隔 feedback_interval 步重新优化
            if step % feedback_interval == 0:
                if self.verbose:
                    print(f"t = {t_current:.1f} s: 优化中...", end=' ')

                # 获取当前状态
                current_state = (self.solver.h.copy(), self.solver.hu.copy())

                # MPC优化
                optimal_u, opt_info = self.optimize_step(
                    current_state=current_state,
                    u_prev=u_prev,
                    method=optimization_method
                )

                # 应用控制
                applied_controls = self.apply_control(optimal_u, apply_to_solver=True)

                # 记录
                self.history['controls'].append(applied_controls)
                self.history['costs'].append(opt_info['cost'])
                self.history['optimization_info'].append(opt_info)

                u_prev = optimal_u

                if self.verbose:
                    print(f" (代价={opt_info['cost']:.3e})")

            # 执行一步实际仿真
            Q_upstream = None
            for grid_idx in self.controllable_inflows:
                if grid_idx == 0:
                    Q_upstream = self.history['controls'][-1]['inflows'].get(grid_idx, None)

            h_downstream = self.solver.h[-1]

            h_new, hu_new = self.solver.step_preissmann(
                dt=self.dt,
                max_iter=10,
                enforce_bc=True,
                Q_in=Q_upstream,
                h_out=h_downstream
            )

            # 更新求解器状态
            self.solver.h = h_new
            self.solver.hu = hu_new

        # 最后一步记录
        self.history['time'].append(n_steps * self.dt)
        self.history['h_history'].append(self.solver.h.copy())
        self.history['Q_history'].append(self.solver.hu * self.solver.B)

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"MPC 闭环控制完成")
            print(f"{'='*60}\n")

        return self.history
