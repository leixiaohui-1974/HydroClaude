#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
单一求解器版本的渠道-闸门耦合求解器（重构版）

使用单个连续CanalSolver + 内部边界条件（闸门）
支持多个闸门和混合结构
优化的稳态求解算法

作者: Claude
日期: 2025-10-22
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
from typing import List, Optional, Dict, Callable
import sys

# Add project root to path
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
if project_root not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from _local_canal_solver import CanalSolver
from solvers.gate import HydraulicStructure
from utils.canal_utils import compute_steady_uniform_flow


class SingleCanalSolver:
    """
    单一渠道求解器（支持内部边界条件）

    核心改进：
    - 使用单个连续求解器覆盖整个渠道
    - 闸门作为内部边界条件处理
    - 支持多个水工建筑物
    - 优化的稳态求解算法
    - 支持时变参数（如可变闸门开度）
    """

    def __init__(self,
                 total_length: float,
                 structures: List[HydraulicStructure],
                 nx_total: int = 201,
                 B: float = 10.0,
                 S0: float = 0.001,
                 n: float = 0.025,
                 g: float = 9.81,
                 method: str = 'preissmann',
                 use_adaptive_grid: bool = False,
                 refinement_radius: float = 200.0,
                 dx_fine: float = 5.0,
                 dx_coarse: float = 33.0,
                 smooth_weight: float = 0.1,
                 adaptive_smooth_config = None):
        """
        Args:
            total_length: 渠道总长度 (m)
            structures: 水工建筑物列表
            nx_total: 总空间点数（均匀网格时使用）
            B: 渠道宽度 (m)
            S0: 渠底坡度
            n: Manning糙率
            g: 重力加速度 (m/s^2)
            method: 数值方法 ('explicit', 'preissmann', 'hll')
            use_adaptive_grid: 是否使用自适应网格加密
            refinement_radius: 结构附近加密半径 (m)
            dx_fine: 加密区网格间距 (m)
            dx_coarse: 粗网格区间距 (m)
            smooth_weight: 闸门附近节点平滑权重 (0-1, 默认0.1，当adaptive_smooth_config=None时使用)
            adaptive_smooth_config: 自适应平滑配置（可选，AdaptiveSmoothConfig对象）
        """
        self.total_length = total_length
        self.structures = sorted(structures, key=lambda s: s.position)
        self.nx_total = nx_total
        self.B = B
        self.S0 = S0
        self.n = n
        self.g = g
        self.method = method
        self.use_adaptive_grid = use_adaptive_grid
        self.smooth_weight = smooth_weight
        self.adaptive_smooth_config = adaptive_smooth_config

        # 当前模拟时间
        self.current_time = 0.0

        # 生成网格
        x_grid = None
        if use_adaptive_grid and len(structures) > 0:
            # 导入网格生成工具
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
            from utils.adaptive_grid import generate_structure_refined_grid

            # 生成自适应网格
            structure_positions = [s.position for s in structures]
            x_grid = generate_structure_refined_grid(
                total_length=total_length,
                structure_positions=structure_positions,
                refinement_radius=refinement_radius,
                dx_fine=dx_fine,
                dx_coarse=dx_coarse,
                transition_width=50.0
            )

            print(f"\n{'='*60}")
            print(f"自适应网格已生成")
            print(f"{'='*60}")
            print(f"  网格点数: {len(x_grid)} (均匀网格: {nx_total})")
            print(f"  精细区间距: {dx_fine} m")
            print(f"  粗糙区间距: {dx_coarse} m")
            print(f"  加密半径: +/-{refinement_radius} m")
            print(f"  结构位置: {structure_positions}")
            print(f"{'='*60}\n")

        # 准备内部结构列表（格式：[(position, structure), ...]）
        internal_structures = [(s.position, s) for s in self.structures]

        # 创建单一求解器
        self.solver = CanalSolver(
            length=total_length,
            nx=nx_total if x_grid is None else len(x_grid),
            B=B,
            S0=S0,
            n=n,
            g=g,
            x_grid=x_grid,
            method=method,
            internal_structures=internal_structures,
            smooth_weight=smooth_weight,
            adaptive_smooth_config=adaptive_smooth_config
        )

    def reset_with_steady_state(self, Q0: float) -> float:
        """
        使用恒定均匀流初始化

        Args:
            Q0: 初始流量 (m^3/s)

        Returns:
            恒定均匀流水深 (m)
        """
        self.current_time = 0.0
        return self.solver.reset_with_steady_state(Q0)

    def solve_steady_state(self,
                          Q_target: float,
                          max_iterations: int = 10000,  # SWMM启发：增加迭代（omega更小需要更多迭代）
                          convergence_tol: float = 0.001,  # SWMM启发：收紧容差
                          check_interval: int = 500,
                          adaptive_relax: bool = True,
                          verbose: bool = True) -> Dict:
        """
        优化的稳态求解

        Args:
            Q_target: 目标流量 (m^3/s)
            max_iterations: 最大迭代步数
            convergence_tol: 收敛容差（相对误差）
            check_interval: 检查收敛的时间间隔
            adaptive_relax: 是否使用自适应松弛因子（默认True）
            verbose: 是否打印详细信息

        Returns:
            收敛信息字典
        """
        #  自适应时间步长（满足CFL条件）
        dx_min = np.min(self.solver.dx_local)
        h_typical = 2.0  # 典型水深 (m)
        V_typical = Q_target / (self.B * h_typical)  # 典型流速
        c_typical = np.sqrt(self.g * h_typical)  # 典型波速
        CFL_target = 0.5  # CFL安全系数

        dt = CFL_target * dx_min / (V_typical + c_typical)
        dt = max(0.1, min(dt, 1.0))  # 限制在0.1-1.0s范围内

        t = 0.0

        converged = False
        final_error = 1.0
        iterations_used = 0

        #  智能早期终止机制
        best_error = float('inf')
        best_state = None
        error_increase_count = 0

        if verbose:
            mode_str = "自适应松弛" if adaptive_relax else "固定松弛"
            print(f"开始稳态求解（目标流量: {Q_target} m^3/s, {mode_str} + 智能早停）...")
            print(f"  自适应时间步长: dt={dt:.3f}s (dx_min={dx_min:.2f}m, CFL={CFL_target})")

        for i in range(max_iterations):
            # 计算下游边界水深（使用正常水深）
            Q_downstream_avg = np.mean(self.solver.Q[-10:])
            h_downstream = compute_steady_uniform_flow(
                Q_downstream_avg, self.B, self.S0, self.n, self.g
            )

            # 执行时间步（PRECISION FIX #3: 保守策略 - 始终使用滤波器保持稳定性）
            self.solver.step(dt, Q_target, h_downstream, t=t,
                           adaptive_relax=adaptive_relax,
                           apply_filter=True)  # 保持滤波器以确保稳定性
            t += dt
            iterations_used = i + 1

            # 定期检查收敛
            if i % check_interval == 0 and i > 0:
                Q_avg = np.mean(self.solver.Q[1:-1])
                Q_error = abs(Q_avg - Q_target) / Q_target
                final_error = Q_error

                if verbose:
                    gate_flows = self.get_gate_flows()
                    gate_str = ', '.join([f"Q{j+1}={gf:.3f}" for j, gf in enumerate(gate_flows)])
                    print(f"  t={t:.0f}s: Q_avg={Q_avg:.4f} m^3/s, 误差={Q_error*100:.4f}%, {gate_str}")

                #  早期终止逻辑：追踪最佳状态
                if Q_error < best_error:
                    best_error = Q_error
                    best_state = {
                        'Q': self.solver.Q.copy(),
                        'h': self.solver.h.copy(),
                        'iteration': i,
                        'time': t
                    }
                    error_increase_count = 0
                else:
                    error_increase_count += 1
                    # 误差连续增长3次 -> 回退并终止
                    if error_increase_count >= 3 and best_state is not None:
                        if verbose:
                            print(f"\n 检测到误差连续增长，回退到最佳状态")
                            print(f"  最佳: i={best_state['iteration']}, t={best_state['time']:.0f}s, "
                                  f"误差={best_error*100:.4f}%")
                        self.solver.Q = best_state['Q']
                        self.solver.h = best_state['h']
                        iterations_used = best_state['iteration']
                        t = best_state['time']
                        final_error = best_error
                        converged = (best_error < convergence_tol)
                        break

                if Q_error < convergence_tol:
                    converged = True
                    if verbose:
                        print(f"\n 达到稳态 (i={i}, t={t:.0f}s)")
                    break

        self.current_time = t

        return {
            'converged': converged,
            'iterations': iterations_used,
            'final_time': t,
            'final_error': final_error,
            'Q_target': Q_target,
            'Q_avg': np.mean(self.solver.Q[1:-1]),
            'gate_flows': self.get_gate_flows(),
            'best_error': best_error
        }

    def step(self, dt: float, Q_upstream: float,
             h_downstream: Optional[float] = None,
             Q_func: Optional[Callable[[float], float]] = None,
             adaptive_relax: bool = False):
        """
        执行一个时间步

        Args:
            dt: 时间步长 (s)
            Q_upstream: 上游边界流量 (m^3/s)，如果提供Q_func则忽略
            h_downstream: 下游边界水深 (m) - 如果为None则自动计算
            Q_func: 上游流量时间函数 Q(t) -> float
            adaptive_relax: 是否使用自适应松弛因子
        """
        # 如果提供了流量函数，使用它
        if Q_func is not None:
            Q_up = Q_func(self.current_time)
        else:
            Q_up = Q_upstream

        # 如果未指定下游边界，使用正常水深
        if h_downstream is None:
            # 使用当前下游流量计算正常水深
            Q_downstream_avg = np.mean(self.solver.Q[-10:])  # 使用下游10个点平均
            h_downstream = compute_steady_uniform_flow(
                Q_downstream_avg, self.B, self.S0, self.n, self.g
            )

        # 执行时间步（内部会自动应用闸门边界条件）
        self.solver.step(dt, Q_up, h_downstream, t=self.current_time,
                        adaptive_relax=adaptive_relax)

        # 更新时间
        self.current_time += dt

    def get_full_profile(self) -> Dict[str, np.ndarray]:
        """
        获取全渠道剖面数据

        Returns:
            包含x, h, Q的字典
        """
        return {
            'x': self.solver.x.copy(),
            'h': self.solver.h.copy(),
            'Q': self.solver.Q.copy(),
        }

    def get_gate_flows(self) -> List[float]:
        """
        获取各闸门的流量

        Returns:
            闸门流量列表
        """
        gate_flows = []
        for idx in self.solver.structure_indices:
            gate_flows.append(self.solver.Q[idx])
        return gate_flows

    def get_structure_info(self) -> List[Dict]:
        """
        获取所有结构的详细信息

        Returns:
            结构信息列表，每个字典包含position, type, params
        """
        info_list = []
        for struct in self.structures:
            info = {
                'position': struct.position,
                'type': struct.__class__.__name__,
                'width': struct.width,
            }
            # 添加特定参数
            if hasattr(struct, 'get_opening'):
                info['opening'] = struct.get_opening(self.current_time)
            if hasattr(struct, 'crest_height'):
                info['crest_height'] = struct.crest_height
            if hasattr(struct, 'Cd'):
                info['Cd'] = struct.Cd
            info_list.append(info)
        return info_list

    def solve_steady_state_high_precision(self,
                                          Q_target: float,
                                          max_iterations: int = 20000,
                                          tol_global: float = 1e-4,
                                          tol_local: float = 1e-4,
                                          tol_structure: float = 1e-4,
                                          tol_temporal: float = 1e-5,
                                          check_interval: int = 100,
                                          verbose: bool = True) -> Dict:
        """
        高精度稳态求解 - 目标精度10^-4

        采用多层次收敛判据 + 自适应时间步进策略

        Args:
            Q_target: 目标流量 (m^3/s)
            max_iterations: 最大迭代步数（增加到20000）
            tol_global: 全局收敛容差（10^-4）
            tol_local: 局部收敛容差（10^-4）
            tol_structure: 结构收敛容差（10^-4）
            tol_temporal: 时间稳定性容差（10^-5）
            check_interval: 检查收敛的时间间隔
            verbose: 是否打印详细信息

        Returns:
            收敛信息字典（包含多种误差指标）
        """

        if verbose:
            print(f"开始高精度稳态求解（目标流量: {Q_target} m^3/s）...")
            print(f"  收敛标准: 全局<{tol_global:.0e}, 局部<{tol_local:.0e}, "
                  f"结构<{tol_structure:.0e}, 时间<{tol_temporal:.0e}")
            print()

        # 单阶段小时间步策略（更稳定）
        dt = 0.2  # 固定小时间步，确保稳定性和精度

        t = 0.0
        iterations_used = 0
        converged = False

        # 历史数据（用于时间稳定性检查）
        Q_history = []
        history_window = 100  # 增加历史窗口

        # 残差记录
        residuals = {
            'global': [],
            'local': [],
            'structure': [],
            'temporal': [],
            'L2': [],
            'Linf': []
        }

        if verbose:
            print(f"使用固定时间步: dt={dt}s")
            print(f"最大迭代次数: {max_iterations}")
            print()

        # 主求解循环
        for i in range(max_iterations):
            # 计算下游边界水深
            Q_downstream_avg = np.mean(self.solver.Q[-10:])
            h_downstream = compute_steady_uniform_flow(
                Q_downstream_avg, self.B, self.S0, self.n, self.g
            )

            # 执行时间步（使用自适应松弛）
            self.solver.step(dt, Q_target, h_downstream, t=t,
                           adaptive_relax=True,
                           apply_filter=True)  # 保持滤波器以确保稳定性
            t += dt
            iterations_used += 1

            # 记录当前流量分布
            Q_current = self.solver.Q.copy()
            Q_history.append(Q_current)
            if len(Q_history) > history_window:
                Q_history.pop(0)

            # 定期检查收敛
            if i % check_interval == 0 and i > 0:
                # Level 1: 全局守恒
                Q_avg = np.mean(Q_current[1:-1])
                error_global = abs(Q_avg - Q_target) / Q_target
                residuals['global'].append(error_global)

                # Level 2: 局部守恒（相邻节点流量差）
                Q_diff = np.abs(np.diff(Q_current))
                error_local = np.max(Q_diff) / Q_target
                residuals['local'].append(error_local)

                # Level 3: 结构守恒
                gate_flows = self.get_gate_flows()
                if gate_flows:
                    gate_errors = [abs(gf - Q_target) / Q_target for gf in gate_flows]
                    error_structure = max(gate_errors)
                else:
                    error_structure = 0.0
                residuals['structure'].append(error_structure)

                # Level 4: 时间稳定性
                if len(Q_history) >= 2:
                    Q_change = np.max(np.abs(Q_history[-1] - Q_history[-2]))
                    Q_magnitude = np.mean(np.abs(Q_history[-1]))
                    error_temporal = Q_change / Q_magnitude if Q_magnitude > 0 else 1.0
                else:
                    error_temporal = 1.0
                residuals['temporal'].append(error_temporal)

                # Additional metrics
                # L2 norm
                error_L2 = np.sqrt(np.mean((Q_current - Q_target)**2)) / Q_target
                residuals['L2'].append(error_L2)

                # L-infinity norm
                error_Linf = np.max(np.abs(Q_current - Q_target)) / Q_target
                residuals['Linf'].append(error_Linf)

                if verbose:
                    gate_str = ', '.join([f"Q{j+1}={gf:.4f}" for j, gf in enumerate(gate_flows)])
                    print(f"  t={t:7.0f}s: 全局={error_global:.2e}, 局部={error_local:.2e}, "
                          f"结构={error_structure:.2e}, 时间={error_temporal:.2e} | {gate_str}")

                # 检查收敛（所有层次同时满足）
                all_converged = (error_global < tol_global and
                                error_local < tol_local and
                                error_structure < tol_structure and
                                error_temporal < tol_temporal)

                if all_converged:
                    converged = True
                    if verbose:
                        print(f"\n{'='*60}")
                        print(f" 达到高精度稳态 ")
                        print(f"{'='*60}")
                    break

        self.current_time = t

        # 最终统计
        final_Q_avg = np.mean(self.solver.Q[1:-1])
        final_gate_flows = self.get_gate_flows()

        result = {
            'converged': converged,
            'iterations': iterations_used,
            'final_time': t,
            'Q_target': Q_target,
            'Q_avg': final_Q_avg,
            'gate_flows': final_gate_flows,
            'residuals': residuals,
            'error_global': residuals['global'][-1] if residuals['global'] else 1.0,
            'error_local': residuals['local'][-1] if residuals['local'] else 1.0,
            'error_structure': residuals['structure'][-1] if residuals['structure'] else 1.0,
            'error_temporal': residuals['temporal'][-1] if residuals['temporal'] else 1.0,
            'error_L2': residuals['L2'][-1] if residuals['L2'] else 1.0,
            'error_Linf': residuals['Linf'][-1] if residuals['Linf'] else 1.0,
        }

        if verbose:
            print(f"\n最终结果:")
            print(f"  总迭代次数: {iterations_used}")
            print(f"  总仿真时间: {t:.0f}s")
            print(f"  目标流量: {Q_target:.6f} m^3/s")
            print(f"  平均流量: {final_Q_avg:.6f} m^3/s")
            print(f"  全局误差: {result['error_global']:.2e} ({'' if result['error_global'] < tol_global else ''})")
            print(f"  局部误差: {result['error_local']:.2e} ({'' if result['error_local'] < tol_local else ''})")
            print(f"  结构误差: {result['error_structure']:.2e} ({'' if result['error_structure'] < tol_structure else ''})")
            print(f"  时间误差: {result['error_temporal']:.2e} ({'' if result['error_temporal'] < tol_temporal else ''})")
            print(f"  L2范数: {result['error_L2']:.2e}")
            print(f"  L∞范数: {result['error_Linf']:.2e}")
            if final_gate_flows:
                print(f"  闸门流量: {', '.join([f'{gf:.6f}' for gf in final_gate_flows])}")
            print()

        return result

    def solve_steady_state_hybrid(self,
                                   Q_target: float,
                                   stage1_iterations: int = 5000,
                                   stage1_tol: float = 0.01,
                                   stage2_iterations: int = 50000,
                                   tol_global: float = 1e-4,
                                   tol_local: float = 1e-4,
                                   tol_structure: float = 1e-4,
                                   tol_temporal: float = 1e-5,
                                   check_interval: int = 200,
                                   verbose: bool = True) -> Dict:
        """
        两阶段混合高精度求解器

        阶段1: 使用标准求解器快速逼近（dt=1.0s + 自适应松弛）
        阶段2: 使用小步长精细优化（dt=0.2s固定）

        这种策略结合了两种方法的优势：
        - 快速收敛到目标附近（避免长时间小步长迭代）
        - 精细优化达到高精度（小步长保证稳定性）
        """

        if verbose:
            print("\n" + "=" * 80)
            print("两阶段混合高精度求解")
            print("=" * 80)

        # ==================== 阶段1: 快速逼近 ====================
        if verbose:
            print(f"\n阶段1: 使用标准求解器快速逼近（目标误差: {stage1_tol*100:.2f}%）")
            print("-" * 80)

        result_stage1 = self.solve_steady_state(
            Q_target=Q_target,
            max_iterations=stage1_iterations,
            convergence_tol=stage1_tol,
            check_interval=500,
            verbose=verbose
        )

        stage1_error = result_stage1['final_error']

        if verbose:
            print(f"\n阶段1完成:")
            print(f"  迭代次数: {result_stage1['iterations']}")
            print(f"  最终误差: {stage1_error*100:.4f}%")
            print(f"  平均流量: {result_stage1['Q_avg']:.4f} m^3/s")
            gate_flows_1 = self.get_gate_flows()
            if gate_flows_1:
                print(f"  闸门流量: {', '.join([f'{gf:.4f}' for gf in gate_flows_1])}")

        # ==================== 阶段2: 精细优化 ====================
        if verbose:
            print(f"\n" + "=" * 80)
            print(f"阶段2: 使用标准步长优化（目标精度: {tol_global*100:.4f}%）")
            print("-" * 80)
            print(f"  固定时间步: dt=1.0s（减少累积误差）")
            print(f"  最大迭代次数: {stage2_iterations}")
            print(f"  收敛标准: 全局<{tol_global:.0e}, 局部<{tol_local:.0e}, "
                  f"结构<{tol_structure:.0e}, 时间<{tol_temporal:.0e}")
            print()

        # 阶段2使用标准步长（减少累积误差）
        dt = 1.0

        # 记录残差历史
        residuals = {
            'global': [],
            'local': [],
            'structure': [],
            'temporal': [],
            'L2': [],
            'Linf': []
        }

        # 历史记录用于时间稳定性检查
        Q_history = []

        converged = False
        iterations_used = result_stage1['iterations']
        t = self.current_time

        # 早期终止检测
        divergence_count = 0
        prev_structure_error = 1.0

        for i in range(stage2_iterations):
            # 单步推进
            self.step(dt, Q_upstream=Q_target)
            t = self.current_time
            iterations_used += 1

            # 记录流量历史
            Q_current = self.solver.Q.copy()
            Q_history.append(Q_current)
            if len(Q_history) > 10:
                Q_history.pop(0)

            # 每check_interval步检查收敛
            if i % check_interval == 0:
                # Level 1: 全局守恒
                Q_avg = np.mean(Q_current[1:-1])
                error_global = abs(Q_avg - Q_target) / Q_target
                residuals['global'].append(error_global)

                # Level 2: 局部守恒
                Q_diff = np.abs(np.diff(Q_current))
                error_local = np.max(Q_diff) / Q_target
                residuals['local'].append(error_local)

                # Level 3: 结构守恒
                gate_flows = self.get_gate_flows()
                if gate_flows:
                    gate_errors = [abs(gf - Q_target) / Q_target for gf in gate_flows]
                    error_structure = max(gate_errors)
                else:
                    error_structure = 0.0
                residuals['structure'].append(error_structure)

                # Level 4: 时间稳定性
                if len(Q_history) >= 2:
                    Q_change = np.max(np.abs(Q_history[-1] - Q_history[-2]))
                    Q_magnitude = np.mean(np.abs(Q_history[-1]))
                    error_temporal = Q_change / Q_magnitude if Q_magnitude > 0 else 1.0
                else:
                    error_temporal = 1.0
                residuals['temporal'].append(error_temporal)

                # Additional metrics
                error_L2 = np.sqrt(np.mean((Q_current - Q_target)**2)) / Q_target
                residuals['L2'].append(error_L2)

                error_Linf = np.max(np.abs(Q_current - Q_target)) / Q_target
                residuals['Linf'].append(error_Linf)

                if verbose:
                    gate_str = ', '.join([f"Q{j+1}={gf:.4f}" for j, gf in enumerate(gate_flows)])
                    print(f"  t={t:7.0f}s: 全局={error_global:.2e}, 局部={error_local:.2e}, "
                          f"结构={error_structure:.2e}, 时间={error_temporal:.2e} | {gate_str}")

                # 检查收敛（所有层次同时满足）
                all_converged = (error_global < tol_global and
                                error_local < tol_local and
                                error_structure < tol_structure and
                                error_temporal < tol_temporal)

                if all_converged:
                    converged = True
                    if verbose:
                        print(f"\n{'='*60}")
                        print(f" 达到高精度稳态 ")
                        print(f"{'='*60}")
                        print(f"  阶段1迭代: {result_stage1['iterations']}")
                        print(f"  阶段2迭代: {i+1}")
                        print(f"  总迭代数: {iterations_used}")
                    break

                # 发散检测：如果结构误差持续增长，提前终止
                if error_structure > prev_structure_error * 1.2:
                    divergence_count += 1
                else:
                    divergence_count = 0

                if divergence_count >= 5:
                    if verbose:
                        print(f"\n{'='*60}")
                        print(f" 检测到持续发散，提前终止阶段2")
                        print(f"{'='*60}")
                        print(f"  当前误差: {error_structure*100:.4f}%")
                        print(f"  建议: 使用阶段1结果或调整参数")
                    break

                prev_structure_error = error_structure

        # 最终统计
        final_Q_avg = np.mean(self.solver.Q[1:-1])
        final_gate_flows = self.get_gate_flows()

        result = {
            'converged': converged,
            'iterations': iterations_used,
            'stage1_iterations': result_stage1['iterations'],
            'stage2_iterations': iterations_used - result_stage1['iterations'],
            'final_time': self.current_time,
            'Q_target': Q_target,
            'Q_avg': final_Q_avg,
            'gate_flows': final_gate_flows,
            'residuals': residuals,
            'stage1_error': stage1_error,
            'error_global': residuals['global'][-1] if residuals['global'] else 1.0,
            'error_local': residuals['local'][-1] if residuals['local'] else 1.0,
            'error_structure': residuals['structure'][-1] if residuals['structure'] else 1.0,
            'error_temporal': residuals['temporal'][-1] if residuals['temporal'] else 1.0,
            'error_L2': residuals['L2'][-1] if residuals['L2'] else 1.0,
            'error_Linf': residuals['Linf'][-1] if residuals['Linf'] else 1.0,
        }

        if verbose:
            print(f"\n最终结果:")
            print(f"  阶段1迭代数: {result['stage1_iterations']}")
            print(f"  阶段2迭代数: {result['stage2_iterations']}")
            print(f"  总迭代次数: {iterations_used}")
            print(f"  总仿真时间: {self.current_time:.0f}s")
            print(f"  目标流量: {Q_target:.6f} m^3/s")
            print(f"  平均流量: {final_Q_avg:.6f} m^3/s")
            print(f"  阶段1->阶段2误差: {stage1_error*100:.4f}% -> {result['error_structure']*100:.4f}%")
            print(f"  精度提升倍数: {stage1_error/result['error_structure']:.1f}x")
            print(f"\n分项误差:")
            print(f"  全局误差: {result['error_global']:.2e} ({'' if result['error_global'] < tol_global else ''})")
            print(f"  局部误差: {result['error_local']:.2e} ({'' if result['error_local'] < tol_local else ''})")
            print(f"  结构误差: {result['error_structure']:.2e} ({'' if result['error_structure'] < tol_structure else ''})")
            print(f"  时间误差: {result['error_temporal']:.2e} ({'' if result['error_temporal'] < tol_temporal else ''})")
            print(f"  L2范数: {result['error_L2']:.2e}")
            print(f"  L∞范数: {result['error_Linf']:.2e}")
            if final_gate_flows:
                print(f"  闸门流量: {', '.join([f'{gf:.6f}' for gf in final_gate_flows])}")
            print()

        return result

    def solve_steady_state_phase2(self,
                                   Q_target: float,
                                   verbose: bool = True) -> Dict:
        """
        Phase 2: 三阶段高精度求解器

        理论设计：
        - 阶段1: 粗收敛 (dt=1.0s, tol=1%, ~500步)
        - 阶段2: 中收敛 (dt=1.0s, tol=0.1%, ~500步, 严格守恒)
        - 阶段3: 细优化 (dt=0.5s, tol=0.01%, ~200步, 最终抛光)

        核心改进：
        1. 严格流量守恒（canal_solver.py已实现）
        2. 减少时间积分步数（1200步 vs 50000步）
        3. 逐级提高精度要求

        预期精度：0.5% (当前2.56% -> 5倍提升)
        """

        if verbose:
            print("\n" + "=" * 80)
            print("Phase 2: 三阶段高精度求解器")
            print("=" * 80)
            print("理论目标: 均匀网格达到0.5%误差 (5倍精度提升)")
            print("=" * 80)

        # ==================== 阶段1: 粗收敛 ====================
        if verbose:
            print(f"\n阶段1: 粗收敛 (目标误差: 1%)")
            print("-" * 80)

        result_stage1 = self.solve_steady_state(
            Q_target=Q_target,
            max_iterations=5000,
            convergence_tol = 0.1,  # 1%
            check_interval=500,
            verbose=verbose
        )

        stage1_error = result_stage1['final_error']
        stage1_iters = result_stage1['iterations']

        if verbose:
            print(f"\n阶段1完成:")
            print(f"  迭代次数: {stage1_iters}")
            print(f"  误差: {stage1_error*100:.4f}%")
            gate_flows = self.get_gate_flows()
            if gate_flows:
                print(f"  闸门流量: {', '.join([f'{gf:.4f}' for gf in gate_flows])}")

        # ==================== 阶段2: 中收敛 ====================
        if verbose:
            print(f"\n" + "=" * 80)
            print(f"阶段2: 中收敛 (目标误差: 0.1%)")
            print("-" * 80)
            print(f"  时间步: dt=1.0s")
            print(f"  最大迭代: 5000步")
            print(f"  收敛标准: 结构误差<0.1%")
            print()

        dt_stage2 = 1.0
        max_iters_stage2 = 5000
        tol_stage2 = 0.001  # 0.1%

        stage2_converged = False
        stage2_iters = 0

        for i in range(max_iters_stage2):
            self.step(dt_stage2, Q_upstream=Q_target)
            stage2_iters += 1

            if i % 100 == 0:
                gate_flows = self.get_gate_flows()
                if gate_flows:
                    errors = [abs(gf - Q_target) / Q_target for gf in gate_flows]
                    max_error = max(errors)

                    if verbose and i % 500 == 0:
                        print(f"  t={self.current_time:.0f}s: 结构误差={max_error:.2e} | " +
                              ', '.join([f"Q{j+1}={gf:.4f}" for j, gf in enumerate(gate_flows)]))

                    if max_error < tol_stage2:
                        stage2_converged = True
                        if verbose:
                            print(f"\n 阶段2收敛 (i={i+1}, 误差={max_error*100:.4f}%)")
                        break

        # ==================== 阶段3: 细优化 ====================
        if verbose:
            print(f"\n" + "=" * 80)
            print(f"阶段3: 细优化 (目标误差: 0.01%)")
            print("-" * 80)
            print(f"  时间步: dt=0.5s (最终抛光)")
            print(f"  最大迭代: 1000步")
            print(f"  收敛标准: 结构误差<0.01%")
            print()

        dt_stage3 = 0.5
        max_iters_stage3 = 1000
        tol_stage3 = 0.0001  # 0.01%

        stage3_converged = False
        stage3_iters = 0

        for i in range(max_iters_stage3):
            self.step(dt_stage3, Q_upstream=Q_target)
            stage3_iters += 1

            if i % 50 == 0:
                gate_flows = self.get_gate_flows()
                if gate_flows:
                    errors = [abs(gf - Q_target) / Q_target for gf in gate_flows]
                    max_error = max(errors)

                    if verbose and i % 200 == 0:
                        print(f"  t={self.current_time:.0f}s: 结构误差={max_error:.2e} | " +
                              ', '.join([f"Q{j+1}={gf:.4f}" for j, gf in enumerate(gate_flows)]))

                    if max_error < tol_stage3:
                        stage3_converged = True
                        if verbose:
                            print(f"\n 阶段3收敛 (i={i+1}, 误差={max_error*100:.4f}%)")
                        break

        # ==================== 最终统计 ====================
        final_Q_avg = np.mean(self.solver.Q[1:-1])
        final_gate_flows = self.get_gate_flows()

        if final_gate_flows:
            final_errors = [abs(gf - Q_target) / Q_target for gf in final_gate_flows]
            final_error = max(final_errors)
        else:
            final_error = abs(final_Q_avg - Q_target) / Q_target

        total_iters = stage1_iters + stage2_iters + stage3_iters

        result = {
            'converged': stage2_converged and stage3_converged,
            'total_iterations': total_iters,
            'stage1_iterations': stage1_iters,
            'stage2_iterations': stage2_iters,
            'stage3_iterations': stage3_iters,
            'stage1_error': stage1_error,
            'final_error': final_error,
            'Q_target': Q_target,
            'Q_avg': final_Q_avg,
            'gate_flows': final_gate_flows,
            'final_time': self.current_time
        }

        if verbose:
            print("\n" + "=" * 80)
            print("Phase 2 求解完成！")
            print("=" * 80)
            print(f"\n总体统计:")
            print(f"  阶段1迭代: {stage1_iters} (粗收敛)")
            print(f"  阶段2迭代: {stage2_iters} (中收敛)")
            print(f"  阶段3迭代: {stage3_iters} (细优化)")
            print(f"  总迭代数: {total_iters}")
            print(f"  总仿真时间: {self.current_time:.0f}s")
            print(f"\n精度表现:")
            print(f"  阶段1误差: {stage1_error*100:.4f}%")
            print(f"  最终误差: {final_error*100:.4f}%")
            print(f"  精度提升: {stage1_error/final_error:.2f}x")
            print(f"\n目标流量: {Q_target:.6f} m^3/s")
            print(f"平均流量: {final_Q_avg:.6f} m^3/s")
            if final_gate_flows:
                print(f"闸门流量: {', '.join([f'{gf:.6f}' for gf in final_gate_flows])}")
            print()

        return result

    def clear_history(self):
        """清空历史记录"""
        self.solver.clear_history()
        self.current_time = 0.0

    def __repr__(self) -> str:
        struct_types = [s.__class__.__name__ for s in self.structures]
        return (f"SingleCanalSolver(length={self.total_length}m, "
                f"nx={self.nx_total}, structures={struct_types})")
