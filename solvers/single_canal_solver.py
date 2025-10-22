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
from typing import List, Optional, Dict, Callable
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.canal_solver import CanalSolver
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
                 method: str = 'preissmann'):
        """
        Args:
            total_length: 渠道总长度 (m)
            structures: 水工建筑物列表
            nx_total: 总空间点数
            B: 渠道宽度 (m)
            S0: 渠底坡度
            n: Manning糙率
            g: 重力加速度 (m/s²)
            method: 数值方法 ('explicit', 'preissmann', 'hll')
        """
        self.total_length = total_length
        self.structures = sorted(structures, key=lambda s: s.position)
        self.nx_total = nx_total
        self.B = B
        self.S0 = S0
        self.n = n
        self.g = g
        self.method = method

        # 当前模拟时间
        self.current_time = 0.0

        # 准备内部结构列表（格式：[(position, structure), ...]）
        internal_structures = [(s.position, s) for s in self.structures]

        # 创建单一求解器
        self.solver = CanalSolver(
            length=total_length,
            nx=nx_total,
            B=B,
            S0=S0,
            n=n,
            g=g,
            method=method,
            internal_structures=internal_structures
        )

    def reset_with_steady_state(self, Q0: float) -> float:
        """
        使用恒定均匀流初始化

        Args:
            Q0: 初始流量 (m³/s)

        Returns:
            恒定均匀流水深 (m)
        """
        self.current_time = 0.0
        return self.solver.reset_with_steady_state(Q0)

    def solve_steady_state(self,
                          Q_target: float,
                          max_iterations: int = 5000,
                          convergence_tol: float = 0.01,
                          check_interval: int = 500,
                          verbose: bool = True) -> Dict:
        """
        优化的稳态求解

        Args:
            Q_target: 目标流量 (m³/s)
            max_iterations: 最大迭代步数
            convergence_tol: 收敛容差（相对误差）
            check_interval: 检查收敛的时间间隔
            verbose: 是否打印详细信息

        Returns:
            收敛信息字典
        """
        dt = 1.0  # 稳态求解时间步长
        t = 0.0

        converged = False
        final_error = 1.0
        iterations_used = 0

        if verbose:
            print(f"开始稳态求解（目标流量: {Q_target} m³/s）...")

        for i in range(max_iterations):
            # 计算下游边界水深（使用正常水深）
            Q_downstream_avg = np.mean(self.solver.Q[-10:])
            h_downstream = compute_steady_uniform_flow(
                Q_downstream_avg, self.B, self.S0, self.n, self.g
            )

            # 执行时间步
            self.solver.step(dt, Q_target, h_downstream, t=t)
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
                    print(f"  t={t:.0f}s: Q_avg={Q_avg:.4f} m³/s, 误差={Q_error*100:.4f}%, {gate_str}")

                if Q_error < convergence_tol:
                    converged = True
                    if verbose:
                        print(f"\n✓ 达到稳态 (i={i}, t={t:.0f}s)")
                    break

        self.current_time = t

        return {
            'converged': converged,
            'iterations': iterations_used,
            'final_time': t,
            'final_error': final_error,
            'Q_target': Q_target,
            'Q_avg': np.mean(self.solver.Q[1:-1]),
            'gate_flows': self.get_gate_flows()
        }

    def step(self, dt: float, Q_upstream: float,
             h_downstream: Optional[float] = None,
             Q_func: Optional[Callable[[float], float]] = None):
        """
        执行一个时间步

        Args:
            dt: 时间步长 (s)
            Q_upstream: 上游边界流量 (m³/s)，如果提供Q_func则忽略
            h_downstream: 下游边界水深 (m) - 如果为None则自动计算
            Q_func: 上游流量时间函数 Q(t) -> float
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
        self.solver.step(dt, Q_up, h_downstream, t=self.current_time)

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

    def clear_history(self):
        """清空历史记录"""
        self.solver.clear_history()
        self.current_time = 0.0

    def __repr__(self) -> str:
        struct_types = [s.__class__.__name__ for s in self.structures]
        return (f"SingleCanalSolver(length={self.total_length}m, "
                f"nx={self.nx_total}, structures={struct_types})")
