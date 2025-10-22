#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
单一求解器版本的渠道-闸门耦合求解器

使用单个连续CanalSolver + 内部边界条件（闸门）
替代之前的两段求解器方法

作者: Claude
日期: 2025-10-22
"""

import numpy as np
from typing import List, Optional, Dict
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
    - 避免两段求解器的固定点问题
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
        return self.solver.reset_with_steady_state(Q0)

    def step(self, dt: float, Q_upstream: float, h_downstream: Optional[float] = None):
        """
        执行一个时间步

        Args:
            dt: 时间步长 (s)
            Q_upstream: 上游边界流量 (m³/s)
            h_downstream: 下游边界水深 (m) - 如果为None则自动计算
        """
        # 如果未指定下游边界，使用正常水深
        if h_downstream is None:
            # 使用当前下游流量计算正常水深
            Q_downstream_avg = np.mean(self.solver.Q[-10:])  # 使用下游10个点平均
            h_downstream = compute_steady_uniform_flow(
                Q_downstream_avg, self.B, self.S0, self.n, self.g
            )

        # 执行时间步（内部会自动应用闸门边界条件）
        self.solver.step(dt, Q_upstream, h_downstream)

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

    def clear_history(self):
        """清空历史记录"""
        self.solver.clear_history()

    def __repr__(self) -> str:
        return (f"SingleCanalSolver(length={self.total_length}m, "
                f"nx={self.nx_total}, structures={len(self.structures)})")
