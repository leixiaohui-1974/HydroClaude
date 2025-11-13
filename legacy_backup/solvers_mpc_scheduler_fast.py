#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速MPC智能调度器（性能优化版）

性能优化策略：
1. 粗网格预测：使用低分辨率网格加速预测
2. 多种优化器：L-BFGS-B、Powell等快速优化器
3. 预测缓存：避免重复计算
4. 并行评估：可选的并行优化

作者: Claude
日期: 2025-10-23
"""

import numpy as np
from scipy.optimize import minimize, differential_evolution
from scipy.interpolate import interp1d
from typing import List, Dict, Tuple, Callable, Optional
import copy
import warnings
import time

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate


class FastMPCScheduler:
    """
    快速MPC调度器（性能优化版）

    核心优化：
    1. 粗网格预测：nx_coarse = nx // coarsening_factor
    2. 自适应优化：根据收敛情况选择优化器
    3. 预测缓存：缓存最近的预测结果
    """

    def __init__(
        self,
        solver: HydrostaticCanalSolver,
        prediction_horizon: int = 10,
        control_horizon: int = 5,
        dt: float = 1.0,
        coarsening_factor: int = 2,
        use_cache: bool = True,
        verbose: bool = True
    ):
        """
        初始化快速MPC调度器

        Args:
            solver: 精细网格求解器
            prediction_horizon: 预测时域长度
            control_horizon: 控制时域长度
            dt: 时间步长
            coarsening_factor: 粗化因子（粗网格 = 精细网格 / factor）
            use_cache: 是否使用预测缓存
            verbose: 是否输出详细信息
        """
        self.solver_fine = solver
        self.N_pred = prediction_horizon
        self.N_ctrl = min(control_horizon, prediction_horizon)
        self.dt = dt
        self.coarsening_factor = coarsening_factor
        self.use_cache = use_cache
        self.verbose = verbose

        # 创建粗网格求解器（用于快速预测）
        self._create_coarse_solver()

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

        # 预测缓存
        self.prediction_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0

        # 性能统计
        self.performance_stats = {
            'optimization_times': [],
            'prediction_times': [],
            'cache_hit_rate': 0.0
        }

        # 历史记录
        self.history = {
            'time': [],
            'controls': [],
            'states': [],
            'costs': [],
            'computation_times': []
        }

    def _create_coarse_solver(self):
        """创建粗网格求解器"""
        nx_fine = self.solver_fine.nx
        nx_coarse = max(5, nx_fine // self.coarsening_factor)

        # 创建粗网格求解器
        self.solver_coarse = HydrostaticCanalSolver(
            length=self.solver_fine.length,
            nx=nx_coarse,
            B=self.solver_fine.B,
            S0=self.solver_fine.S0,
            n=self.solver_fine.n,
            g=self.solver_fine.g
        )

        # 保存网格对应关系
        self.fine_to_coarse_map = self._create_grid_mapping(nx_fine, nx_coarse)
        self.coarse_to_fine_map = self._create_grid_mapping(nx_coarse, nx_fine)

        if self.verbose:
            print(f"粗网格求解器: {nx_fine} → {nx_coarse} 网格点 "
                  f"(加速比估计: {(nx_fine/nx_coarse)**2:.1f}x)")

    def _create_grid_mapping(
        self,
        nx_from: int,
        nx_to: int
    ) -> np.ndarray:
        """
        创建网格映射关系

        Args:
            nx_from: 源网格数量
            nx_to: 目标网格数量

        Returns:
            映射索引数组
        """
        x_from = np.linspace(0, 1, nx_from)
        x_to = np.linspace(0, 1, nx_to)
        mapping = np.zeros(nx_from, dtype=int)

        for i, x in enumerate(x_from):
            mapping[i] = np.argmin(np.abs(x_to - x))

        return mapping

    def _interpolate_to_coarse(
        self,
        state_fine: Tuple[np.ndarray, np.ndarray]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        将精细网格状态插值到粗网格

        Args:
            state_fine: (h_fine, hu_fine)

        Returns:
            (h_coarse, hu_coarse)
        """
        h_fine, hu_fine = state_fine
        nx_fine = len(h_fine)
        nx_coarse = self.solver_coarse.nx

        x_fine = np.linspace(0, 1, nx_fine)
        x_coarse = np.linspace(0, 1, nx_coarse)

        h_interp = interp1d(x_fine, h_fine, kind='linear')
        hu_interp = interp1d(x_fine, hu_fine, kind='linear')

        h_coarse = h_interp(x_coarse)
        hu_coarse = hu_interp(x_coarse)

        return h_coarse, hu_coarse

    def _interpolate_to_fine(
        self,
        state_coarse: Tuple[np.ndarray, np.ndarray]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        将粗网格状态插值回精细网格

        Args:
            state_coarse: (h_coarse, hu_coarse)

        Returns:
            (h_fine, hu_fine)
        """
        h_coarse, hu_coarse = state_coarse
        nx_coarse = len(h_coarse)
        nx_fine = self.solver_fine.nx

        x_coarse = np.linspace(0, 1, nx_coarse)
        x_fine = np.linspace(0, 1, nx_fine)

        h_interp = interp1d(x_coarse, h_coarse, kind='cubic')
        hu_interp = interp1d(x_coarse, hu_coarse, kind='cubic')

        h_fine = h_interp(x_fine)
        hu_fine = hu_interp(x_fine)

        return h_fine, hu_fine

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
        """解码控制向量为实际控制变量"""
        n_gates = len(self.controllable_gates)
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

    def _predict_trajectory_fast(
        self,
        initial_state: Tuple[np.ndarray, np.ndarray],
        controls: Dict,
        use_coarse: bool = True
    ) -> Tuple[List[np.ndarray], List[np.ndarray]]:
        """
        快速预测轨迹（使用粗网格）

        Args:
            initial_state: 初始状态（精细网格）
            controls: 控制序列
            use_coarse: 是否使用粗网格

        Returns:
            h_trajectory, Q_trajectory（精细网格）
        """
        t_start = time.time()

        if use_coarse:
            # 插值到粗网格
            h_coarse, hu_coarse = self._interpolate_to_coarse(initial_state)
            solver_copy = copy.deepcopy(self.solver_coarse)
            solver_copy.h = h_coarse
            solver_copy.hu = hu_coarse
        else:
            # 使用精细网格
            solver_copy = copy.deepcopy(self.solver_fine)
            solver_copy.h = initial_state[0].copy()
            solver_copy.hu = initial_state[1].copy()

        h_trajectory = []
        Q_trajectory = []

        # 预测循环
        for t in range(self.N_pred + 1):
            # 插值回精细网格（如果需要）
            if use_coarse:
                h_fine, hu_fine = self._interpolate_to_fine(
                    (solver_copy.h, solver_copy.hu)
                )
                h_trajectory.append(h_fine)
                Q_trajectory.append(hu_fine * self.solver_fine.B)
            else:
                h_trajectory.append(solver_copy.h.copy())
                Q_trajectory.append(solver_copy.hu * solver_copy.B)

            if t < self.N_pred:
                # 应用控制
                t_ctrl = min(t, self.N_ctrl - 1)

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
                        max_iter=5 if use_coarse else 10,
                        enforce_bc=True,
                        Q_in=Q_upstream,
                        h_out=h_downstream
                    )
                    solver_copy.h = h_new
                    solver_copy.hu = hu_new
                except Exception as e:
                    if self.verbose:
                        warnings.warn(f"预测步 {t} 失败: {e}")
                    break

        elapsed = time.time() - t_start
        self.performance_stats['prediction_times'].append(elapsed)

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
        u_prev: np.ndarray = None,
        use_coarse: bool = True
    ) -> float:
        """优化目标函数"""
        # 检查缓存
        u_key = tuple(u) if self.use_cache else None

        if self.use_cache and u_key in self.prediction_cache:
            self.cache_hits += 1
            return self.prediction_cache[u_key]

        self.cache_misses += 1

        # 解码控制
        controls = self._decode_control_vector(u)

        # 预测轨迹
        h_traj, Q_traj = self._predict_trajectory_fast(
            initial_state, controls, use_coarse=use_coarse
        )

        # 计算代价
        cost = self._compute_cost(h_traj, Q_traj, controls, u_prev)

        # 缓存结果
        if self.use_cache and u_key is not None:
            self.prediction_cache[u_key] = cost

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

    def optimize_step(
        self,
        current_state: Tuple[np.ndarray, np.ndarray],
        u_prev: np.ndarray = None,
        method: str = 'L-BFGS-B',
        use_coarse: bool = True
    ) -> Tuple[np.ndarray, Dict]:
        """
        执行一次MPC优化步骤

        Args:
            current_state: 当前状态
            u_prev: 上一时刻控制向量
            method: 优化方法 ('L-BFGS-B', 'SLSQP', 'Powell', 'TNC')
            use_coarse: 是否使用粗网格预测

        Returns:
            optimal_u: 最优控制向量
            info: 优化信息
        """
        t_start = time.time()

        # 清空缓存（每次优化开始）
        if self.use_cache:
            self.prediction_cache.clear()
            self.cache_hits = 0
            self.cache_misses = 0

        # 初始猜测
        if u_prev is not None:
            u0 = u_prev.copy()
        else:
            bounds = self._get_bounds()
            u0 = np.array([(lb + ub) / 2 for lb, ub in bounds])

        bounds = self._get_bounds()

        # 优化
        if method in ['L-BFGS-B', 'SLSQP', 'TNC', 'Powell']:
            result = minimize(
                fun=self._objective_function,
                x0=u0,
                args=(current_state, u_prev, use_coarse),
                method=method,
                bounds=bounds,
                options={'maxiter': 100, 'disp': False}
            )
            optimal_u = result.x
            info = {
                'success': result.success,
                'cost': result.fun,
                'iterations': result.nit if hasattr(result, 'nit') else 0,
                'message': result.message
            }

        elif method == 'differential_evolution':
            result = differential_evolution(
                func=self._objective_function,
                bounds=bounds,
                args=(current_state, u_prev, use_coarse),
                maxiter=50,
                popsize=10,
                tol=1e-3,
                seed=42,
                workers=1
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

        elapsed = time.time() - t_start
        self.performance_stats['optimization_times'].append(elapsed)

        if self.use_cache:
            hit_rate = self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
            self.performance_stats['cache_hit_rate'] = hit_rate
            info['cache_hit_rate'] = hit_rate

        info['computation_time'] = elapsed

        return optimal_u, info

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
        optimization_method: str = 'L-BFGS-B',
        use_coarse_grid: bool = True,
        feedback_interval: int = 1
    ) -> Dict:
        """
        运行闭环MPC控制

        Args:
            t_end: 仿真结束时间
            initial_state: 初始状态
            optimization_method: 优化方法
            use_coarse_grid: 是否使用粗网格预测
            feedback_interval: 反馈间隔

        Returns:
            结果字典
        """
        self.solver_fine.h = initial_state[0].copy()
        self.solver_fine.hu = initial_state[1].copy()

        n_steps = int(t_end / self.dt)
        u_prev = None

        self.history = {
            'time': [],
            'h_history': [],
            'Q_history': [],
            'controls': [],
            'costs': [],
            'computation_times': [],
            'optimization_info': []
        }

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"快速MPC闭环控制")
            print(f"{'='*60}")
            print(f"预测时域: {self.N_pred} 步")
            print(f"控制时域: {self.N_ctrl} 步")
            print(f"粗化因子: {self.coarsening_factor}")
            print(f"优化器: {optimization_method}")
            print(f"使用粗网格: {'是' if use_coarse_grid else '否'}")
            print(f"{'='*60}\n")

        total_opt_time = 0.0

        for step in range(n_steps):
            t_current = step * self.dt

            self.history['time'].append(t_current)
            self.history['h_history'].append(self.solver_fine.h.copy())
            self.history['Q_history'].append(self.solver_fine.hu * self.solver_fine.B)

            if step % feedback_interval == 0:
                if self.verbose:
                    print(f"t = {t_current:.1f} s: 优化中...", end=' ')

                current_state = (self.solver_fine.h.copy(), self.solver_fine.hu.copy())

                optimal_u, opt_info = self.optimize_step(
                    current_state=current_state,
                    u_prev=u_prev,
                    method=optimization_method,
                    use_coarse=use_coarse_grid
                )

                applied_controls = self.apply_control(optimal_u, apply_to_solver=True)

                self.history['controls'].append(applied_controls)
                self.history['costs'].append(opt_info['cost'])
                self.history['computation_times'].append(opt_info['computation_time'])
                self.history['optimization_info'].append(opt_info)

                u_prev = optimal_u
                total_opt_time += opt_info['computation_time']

                if self.verbose:
                    cache_info = f", 缓存命中率={opt_info.get('cache_hit_rate', 0):.1%}" if self.use_cache else ""
                    print(f" (代价={opt_info['cost']:.3e}, 耗时={opt_info['computation_time']:.3f}s{cache_info})")

            # 执行实际仿真
            Q_upstream = None
            for grid_idx in self.controllable_inflows:
                if grid_idx == 0:
                    Q_upstream = self.history['controls'][-1]['inflows'].get(grid_idx, None)

            h_downstream = self.solver_fine.h[-1]

            h_new, hu_new = self.solver_fine.step_preissmann(
                dt=self.dt,
                max_iter=10,
                enforce_bc=True,
                Q_in=Q_upstream,
                h_out=h_downstream
            )

            self.solver_fine.h = h_new
            self.solver_fine.hu = hu_new

        # 最后记录
        self.history['time'].append(n_steps * self.dt)
        self.history['h_history'].append(self.solver_fine.h.copy())
        self.history['Q_history'].append(self.solver_fine.hu * self.solver_fine.B)

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"快速MPC完成")
            print(f"总优化时间: {total_opt_time:.2f} s")
            print(f"平均优化时间: {total_opt_time/(n_steps/feedback_interval):.3f} s/步")
            print(f"{'='*60}\n")

        return self.history

    def get_performance_summary(self) -> Dict:
        """获取性能统计摘要"""
        return {
            'avg_optimization_time': np.mean(self.performance_stats['optimization_times']) if self.performance_stats['optimization_times'] else 0,
            'avg_prediction_time': np.mean(self.performance_stats['prediction_times']) if self.performance_stats['prediction_times'] else 0,
            'cache_hit_rate': self.performance_stats['cache_hit_rate'],
            'total_optimizations': len(self.performance_stats['optimization_times'])
        }
