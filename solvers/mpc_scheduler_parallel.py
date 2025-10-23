#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
并行MPC智能调度器

性能优化策略：
1. 多核并行：使用multiprocessing并行评估目标函数
2. 并行优化器：粒子群、差分进化等天然并行算法
3. 任务队列：批量评估控制候选
4. 内存共享：减少进程间通信开销

作者: Claude
日期: 2025-10-23
"""

import numpy as np
from scipy.optimize import minimize, differential_evolution
from multiprocessing import Pool, cpu_count, Manager
from typing import List, Dict, Tuple, Callable, Optional
import copy
import warnings
import time

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate


class ParallelMPCScheduler:
    """
    并行MPC调度器

    核心优化：
    1. 并行目标函数评估
    2. 并行优化算法（PSO、DE）
    3. 批量预测
    """

    def __init__(
        self,
        solver: HydrostaticCanalSolver,
        prediction_horizon: int = 10,
        control_horizon: int = 5,
        dt: float = 1.0,
        n_workers: int = None,
        verbose: bool = True
    ):
        """
        初始化并行MPC调度器

        Args:
            solver: 求解器
            prediction_horizon: 预测时域
            control_horizon: 控制时域
            dt: 时间步长
            n_workers: 并行工作进程数（None=自动检测）
            verbose: 是否输出详细信息
        """
        self.solver = solver
        self.N_pred = prediction_horizon
        self.N_ctrl = min(control_horizon, prediction_horizon)
        self.dt = dt
        self.n_workers = n_workers if n_workers else max(1, cpu_count() - 1)
        self.verbose = verbose

        # 目标和权重
        self.target_depths: Dict[int, float] = {}
        self.target_flows: Dict[int, float] = {}
        self.weight_depth = 1.0
        self.weight_flow = 1.0
        self.weight_control_change = 0.1

        # 控制变量
        self.controllable_gates: List[SluiceGate] = []
        self.controllable_inflows: List[int] = []
        self.gate_opening_bounds: Dict[SluiceGate, Tuple[float, float]] = {}
        self.inflow_bounds: Tuple[float, float] = (0.0, 100.0)

        # 性能统计
        self.performance_stats = {
            'parallel_evaluations': 0,
            'sequential_evaluations': 0,
            'speedup': 1.0,
            'optimization_times': []
        }

        # 历史记录
        self.history = {
            'time': [],
            'controls': [],
            'costs': [],
            'computation_times': []
        }

        if self.verbose:
            print(f"并行MPC初始化: {self.n_workers} 个工作进程")

    def set_targets(
        self,
        depth_targets: Dict[int, float] = None,
        flow_targets: Dict[int, float] = None
    ):
        """设置控制目标"""
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
        """添加可控闸门"""
        self.controllable_gates.append(gate)
        self.gate_opening_bounds[gate] = (opening_min, opening_max)

    def add_controllable_inflow(
        self,
        grid_index: int = 0,
        Q_min: float = 0.0,
        Q_max: float = 100.0
    ):
        """添加可控入流"""
        self.controllable_inflows.append(grid_index)
        self.inflow_bounds = (Q_min, Q_max)

    def _decode_control_vector(self, u: np.ndarray) -> Dict:
        """解码控制向量"""
        controls = {
            'gate_openings': {},
            'inflows': {}
        }

        idx = 0
        for gate in self.controllable_gates:
            openings = u[idx:idx + self.N_ctrl]
            controls['gate_openings'][gate] = openings
            idx += self.N_ctrl

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
        """预测轨迹"""
        solver_copy = copy.deepcopy(self.solver)
        solver_copy.h = initial_state[0].copy()
        solver_copy.hu = initial_state[1].copy()

        h_trajectory = [solver_copy.h.copy()]
        Q_trajectory = [solver_copy.hu * solver_copy.B]

        for t in range(self.N_pred):
            t_ctrl = min(t, self.N_ctrl - 1)

            # 应用控制
            for gate, openings in controls['gate_openings'].items():
                opening_value = openings[t_ctrl]
                gate.opening_func = lambda t, val=opening_value: val

            Q_upstream = None
            for grid_idx, inflows in controls['inflows'].items():
                if grid_idx == 0:
                    Q_upstream = inflows[t_ctrl]

            # 执行一步
            try:
                h_downstream = solver_copy.h[-1]
                h_new, hu_new = solver_copy.step_preissmann(
                    dt=self.dt,
                    max_iter=10,
                    enforce_bc=True,
                    Q_in=Q_upstream,
                    h_out=h_downstream
                )
                solver_copy.h = h_new
                solver_copy.hu = hu_new

                h_trajectory.append(solver_copy.h.copy())
                Q_trajectory.append(solver_copy.hu * solver_copy.B)
            except Exception as e:
                if self.verbose:
                    warnings.warn(f"预测步 {t} 失败: {e}")
                break

        return h_trajectory, Q_trajectory

    def _compute_cost(
        self,
        h_trajectory: List[np.ndarray],
        Q_trajectory: List[np.ndarray],
        controls: Dict,
        u_prev: np.ndarray = None
    ) -> float:
        """计算代价函数"""
        cost = 0.0

        # 跟踪误差（水深）
        if self.target_depths:
            for idx, target_h in self.target_depths.items():
                for h in h_trajectory:
                    error = h[idx] - target_h
                    cost += self.weight_depth * error**2

        # 跟踪误差（流量）
        if self.target_flows:
            for idx, target_Q in self.target_flows.items():
                for Q in Q_trajectory:
                    error = Q[idx] - target_Q
                    cost += self.weight_flow * error**2

        # 控制平滑性
        if u_prev is not None:
            u_current = self._encode_controls(controls)
            n_controls_per_step = len(self.controllable_gates) + len(self.controllable_inflows)
            u_curr_first = u_current[:n_controls_per_step]
            u_prev_first = u_prev[:n_controls_per_step]
            control_change = np.sum((u_curr_first - u_prev_first)**2)
            cost += self.weight_control_change * control_change

        return cost

    def _encode_controls(self, controls: Dict) -> np.ndarray:
        """编码控制向量"""
        u = []
        for gate in self.controllable_gates:
            u.extend(controls['gate_openings'][gate])
        for grid_idx in self.controllable_inflows:
            u.extend(controls['inflows'][grid_idx])
        return np.array(u)

    def _objective_function_worker(self, args):
        """
        并行工作函数（用于multiprocessing）

        Args:
            args: (u, initial_state, u_prev, solver_config, targets, weights)

        Returns:
            cost
        """
        u, initial_state, u_prev, solver_config, targets, weights = args

        # 重建求解器（每个进程独立）
        from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

        solver = HydrostaticCanalSolver(**solver_config)
        solver.h = initial_state[0].copy()
        solver.hu = initial_state[1].copy()

        # 设置目标和权重
        self.target_depths = targets['depths']
        self.target_flows = targets['flows']
        self.weight_depth = weights['depth']
        self.weight_flow = weights['flow']
        self.weight_control_change = weights['control_change']

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

        for gate in self.controllable_gates:
            opening_min, opening_max = self.gate_opening_bounds[gate]
            bounds.extend([(opening_min, opening_max)] * self.N_ctrl)

        for _ in self.controllable_inflows:
            Q_min, Q_max = self.inflow_bounds
            bounds.extend([(Q_min, Q_max)] * self.N_ctrl)

        return bounds

    def _objective_function_sequential(
        self,
        u: np.ndarray,
        initial_state: Tuple[np.ndarray, np.ndarray],
        u_prev: np.ndarray = None
    ) -> float:
        """串行目标函数（用于梯度优化器）"""
        self.performance_stats['sequential_evaluations'] += 1

        controls = self._decode_control_vector(u)
        h_traj, Q_traj = self._predict_trajectory(initial_state, controls)
        cost = self._compute_cost(h_traj, Q_traj, controls, u_prev)

        return cost

    def optimize_step_parallel_pso(
        self,
        current_state: Tuple[np.ndarray, np.ndarray],
        u_prev: np.ndarray = None,
        n_particles: int = 20,
        n_iterations: int = 30
    ) -> Tuple[np.ndarray, Dict]:
        """
        使用并行粒子群优化（PSO）

        Args:
            current_state: 当前状态
            u_prev: 上一时刻控制
            n_particles: 粒子数量
            n_iterations: 迭代次数

        Returns:
            optimal_u, info
        """
        t_start = time.time()

        bounds = self._get_bounds()
        n_dims = len(bounds)

        # 初始化粒子群
        particles = np.random.uniform(
            low=[b[0] for b in bounds],
            high=[b[1] for b in bounds],
            size=(n_particles, n_dims)
        )

        velocities = np.zeros((n_particles, n_dims))
        personal_best_positions = particles.copy()
        personal_best_costs = np.full(n_particles, np.inf)

        # 准备求解器配置（用于并行）
        solver_config = {
            'length': self.solver.length,
            'nx': self.solver.nx,
            'B': self.solver.B,
            'S0': self.solver.S0,
            'n': self.solver.n,
            'g': self.solver.g
        }

        targets = {
            'depths': self.target_depths,
            'flows': self.target_flows
        }

        weights = {
            'depth': self.weight_depth,
            'flow': self.weight_flow,
            'control_change': self.weight_control_change
        }

        global_best_position = None
        global_best_cost = np.inf

        # PSO参数
        w = 0.7  # 惯性权重
        c1 = 1.5  # 个体学习因子
        c2 = 1.5  # 社会学习因子

        # PSO迭代
        for iteration in range(n_iterations):
            # 并行评估所有粒子
            with Pool(self.n_workers) as pool:
                args_list = [
                    (particles[i], current_state, u_prev, solver_config, targets, weights)
                    for i in range(n_particles)
                ]
                costs = pool.map(self._objective_function_worker, args_list)

            self.performance_stats['parallel_evaluations'] += n_particles

            # 更新个体最优和全局最优
            for i in range(n_particles):
                if costs[i] < personal_best_costs[i]:
                    personal_best_costs[i] = costs[i]
                    personal_best_positions[i] = particles[i].copy()

                if costs[i] < global_best_cost:
                    global_best_cost = costs[i]
                    global_best_position = particles[i].copy()

            # 更新速度和位置
            r1 = np.random.random((n_particles, n_dims))
            r2 = np.random.random((n_particles, n_dims))

            velocities = (w * velocities +
                         c1 * r1 * (personal_best_positions - particles) +
                         c2 * r2 * (global_best_position - particles))

            particles = particles + velocities

            # 边界约束
            for i in range(n_particles):
                for j in range(n_dims):
                    particles[i, j] = np.clip(particles[i, j], bounds[j][0], bounds[j][1])

            if self.verbose and iteration % 10 == 0:
                print(f"  PSO迭代 {iteration}: 最优代价 = {global_best_cost:.3e}")

        elapsed = time.time() - t_start
        self.performance_stats['optimization_times'].append(elapsed)

        # 计算加速比（理论）
        theoretical_speedup = min(self.n_workers, n_particles)
        self.performance_stats['speedup'] = theoretical_speedup

        info = {
            'success': True,
            'cost': global_best_cost,
            'iterations': n_iterations,
            'message': 'PSO并行优化完成',
            'computation_time': elapsed,
            'n_particles': n_particles,
            'speedup_theoretical': theoretical_speedup
        }

        return global_best_position, info

    def optimize_step_parallel_de(
        self,
        current_state: Tuple[np.ndarray, np.ndarray],
        u_prev: np.ndarray = None,
        popsize: int = 15,
        maxiter: int = 50
    ) -> Tuple[np.ndarray, Dict]:
        """
        使用并行差分进化（DE）

        Args:
            current_state: 当前状态
            u_prev: 上一时刻控制
            popsize: 种群大小
            maxiter: 最大迭代次数

        Returns:
            optimal_u, info
        """
        t_start = time.time()

        bounds = self._get_bounds()

        # differential_evolution内置并行支持
        result = differential_evolution(
            func=self._objective_function_sequential,
            bounds=bounds,
            args=(current_state, u_prev),
            strategy='best1bin',
            maxiter=maxiter,
            popsize=popsize,
            tol=1e-3,
            seed=None,
            workers=self.n_workers,  # 并行评估
            updating='deferred',      # 延迟更新（更好的并行性）
            polish=False              # 不进行局部优化（加速）
        )

        elapsed = time.time() - t_start
        self.performance_stats['optimization_times'].append(elapsed)

        info = {
            'success': result.success,
            'cost': result.fun,
            'iterations': result.nit,
            'message': result.message,
            'computation_time': elapsed,
            'n_workers': self.n_workers
        }

        return result.x, info

    def optimize_step(
        self,
        current_state: Tuple[np.ndarray, np.ndarray],
        u_prev: np.ndarray = None,
        method: str = 'parallel_pso'
    ) -> Tuple[np.ndarray, Dict]:
        """
        执行优化步骤

        Args:
            current_state: 当前状态
            u_prev: 上一时刻控制
            method: 'parallel_pso', 'parallel_de', 'SLSQP'

        Returns:
            optimal_u, info
        """
        if method == 'parallel_pso':
            return self.optimize_step_parallel_pso(current_state, u_prev)
        elif method == 'parallel_de':
            return self.optimize_step_parallel_de(current_state, u_prev)
        elif method in ['SLSQP', 'L-BFGS-B']:
            # 串行梯度优化器
            t_start = time.time()

            if u_prev is not None:
                u0 = u_prev.copy()
            else:
                bounds = self._get_bounds()
                u0 = np.array([(lb + ub) / 2 for lb, ub in bounds])

            result = minimize(
                fun=self._objective_function_sequential,
                x0=u0,
                args=(current_state, u_prev),
                method=method,
                bounds=self._get_bounds(),
                options={'maxiter': 100}
            )

            elapsed = time.time() - t_start

            info = {
                'success': result.success,
                'cost': result.fun,
                'iterations': result.nit if hasattr(result, 'nit') else 0,
                'message': result.message,
                'computation_time': elapsed
            }

            return result.x, info
        else:
            raise ValueError(f"不支持的优化方法: {method}")

    def apply_control(
        self,
        optimal_u: np.ndarray,
        apply_to_solver: bool = True
    ) -> Dict:
        """应用第一个控制动作"""
        controls = self._decode_control_vector(optimal_u)

        applied_controls = {
            'gate_openings': {},
            'inflows': {}
        }

        for gate in self.controllable_gates:
            opening_t0 = controls['gate_openings'][gate][0]
            applied_controls['gate_openings'][gate] = opening_t0

            if apply_to_solver:
                gate.opening_func = lambda t, val=opening_t0: val

        for grid_idx in self.controllable_inflows:
            inflow_t0 = controls['inflows'][grid_idx][0]
            applied_controls['inflows'][grid_idx] = inflow_t0

        return applied_controls

    def run_closed_loop(
        self,
        t_end: float,
        initial_state: Tuple[np.ndarray, np.ndarray],
        optimization_method: str = 'parallel_pso',
        feedback_interval: int = 1
    ) -> Dict:
        """
        运行闭环MPC控制

        Args:
            t_end: 仿真结束时间
            initial_state: 初始状态
            optimization_method: 优化方法
            feedback_interval: 反馈间隔

        Returns:
            结果字典
        """
        self.solver.h = initial_state[0].copy()
        self.solver.hu = initial_state[1].copy()

        n_steps = int(t_end / self.dt)
        u_prev = None

        self.history = {
            'time': [],
            'h_history': [],
            'Q_history': [],
            'controls': [],
            'costs': [],
            'computation_times': []
        }

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"并行MPC闭环控制")
            print(f"{'='*60}")
            print(f"预测时域: {self.N_pred} 步")
            print(f"控制时域: {self.N_ctrl} 步")
            print(f"优化方法: {optimization_method}")
            print(f"并行工作进程: {self.n_workers}")
            print(f"{'='*60}\n")

        total_opt_time = 0.0

        for step in range(n_steps):
            t_current = step * self.dt

            self.history['time'].append(t_current)
            self.history['h_history'].append(self.solver.h.copy())
            self.history['Q_history'].append(self.solver.hu * self.solver.B)

            if step % feedback_interval == 0:
                if self.verbose:
                    print(f"t = {t_current:.1f} s: 优化中...", end=' ')

                current_state = (self.solver.h.copy(), self.solver.hu.copy())

                optimal_u, opt_info = self.optimize_step(
                    current_state=current_state,
                    u_prev=u_prev,
                    method=optimization_method
                )

                applied_controls = self.apply_control(optimal_u, apply_to_solver=True)

                self.history['controls'].append(applied_controls)
                self.history['costs'].append(opt_info['cost'])
                self.history['computation_times'].append(opt_info['computation_time'])

                u_prev = optimal_u
                total_opt_time += opt_info['computation_time']

                if self.verbose:
                    print(f"✓ (代价={opt_info['cost']:.3e}, 耗时={opt_info['computation_time']:.3f}s)")

            # 执行实际仿真
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

            self.solver.h = h_new
            self.solver.hu = hu_new

        # 最后记录
        self.history['time'].append(n_steps * self.dt)
        self.history['h_history'].append(self.solver.h.copy())
        self.history['Q_history'].append(self.solver.hu * self.solver.B)

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"并行MPC完成")
            print(f"总优化时间: {total_opt_time:.2f} s")
            print(f"平均优化时间: {total_opt_time/(n_steps/feedback_interval):.3f} s/步")
            if optimization_method in ['parallel_pso', 'parallel_de']:
                speedup = self.performance_stats.get('speedup', 1.0)
                print(f"理论加速比: {speedup:.1f}x")
            print(f"{'='*60}\n")

        return self.history

    def get_performance_summary(self) -> Dict:
        """获取性能统计摘要"""
        return {
            'n_workers': self.n_workers,
            'parallel_evaluations': self.performance_stats['parallel_evaluations'],
            'sequential_evaluations': self.performance_stats['sequential_evaluations'],
            'speedup': self.performance_stats['speedup'],
            'avg_optimization_time': np.mean(self.performance_stats['optimization_times']) if self.performance_stats['optimization_times'] else 0
        }
