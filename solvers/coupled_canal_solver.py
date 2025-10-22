#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
带内部边界条件的耦合渠道求解器

支持在渠道内部设置水工建筑物（闸门、堰等）作为内部边界条件
通过迭代耦合确保流量守恒和水力连续性

作者: Claude
日期: 2025-10-22
"""

import numpy as np
from typing import List, Dict, Optional
import sys
import os

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.canal_solver import CanalSolver
from solvers.gate import HydraulicStructure
from utils.canal_utils import compute_steady_uniform_flow


class CoupledCanalSolver:
    """
    耦合渠道求解器

    管理多段渠道及其之间的水工建筑物，通过迭代耦合求解
    确保流量守恒和水力连续性
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
                 coupling_max_iter: int = 20,
                 coupling_tol: float = 0.01,
                 coupling_relax: float = 0.3):
        """
        Args:
            total_length: 渠道总长度 (m)
            structures: 水工建筑物列表（按位置升序排列）
            nx_total: 总空间点数
            B: 渠道宽度 (m)
            S0: 渠底坡度
            n: Manning糙率
            g: 重力加速度 (m/s²)
            method: 数值方法 ('explicit', 'preissmann', 'hll')
            coupling_max_iter: 耦合最大迭代次数
            coupling_tol: 耦合收敛容差 (m³/s)
            coupling_relax: 耦合松弛因子 (0-1)
        """
        self.total_length = total_length
        self.structures = sorted(structures, key=lambda s: s.position)
        self.nx_total = nx_total
        self.B = B
        self.S0 = S0
        self.n = n
        self.g = g
        self.method = method

        # 耦合参数
        self.coupling_max_iter = coupling_max_iter
        self.coupling_tol = coupling_tol
        self.coupling_relax = coupling_relax

        # 创建渠道段
        self._create_segments()

        # 闸门流量（用于耦合）
        self.structure_flows = [0.0] * len(self.structures)

    def _create_segments(self):
        """创建渠道段"""
        # 确定分段点
        positions = [0.0] + [s.position for s in self.structures] + [self.total_length]

        self.segments = []
        self.segment_lengths = []

        # 按位置创建各段
        for i in range(len(positions) - 1):
            length = positions[i+1] - positions[i]
            self.segment_lengths.append(length)

            # 计算该段的点数（按长度比例分配）
            nx_segment = max(11, int(self.nx_total * length / self.total_length))
            if nx_segment % 2 == 0:  # 确保为奇数
                nx_segment += 1

            segment = CanalSolver(
                length=length,
                nx=nx_segment,
                B=self.B,
                S0=self.S0,
                n=self.n,
                g=self.g,
                method=self.method
            )

            self.segments.append(segment)

    def reset_with_steady_state(self, Q0: float) -> float:
        """
        使用恒定均匀流初始化所有渠道段

        Args:
            Q0: 初始流量 (m³/s)

        Returns:
            恒定均匀流水深 (m)
        """
        h_uniform = compute_steady_uniform_flow(Q0, self.B, self.S0, self.n, self.g)

        for segment in self.segments:
            segment.reset_with_steady_state(Q0)

        # 初始化闸门流量
        self.structure_flows = [Q0] * len(self.structures)

        return h_uniform

    def step_steady(self, dt: float, Q_upstream: float, h_downstream: float,
                   max_iterations: int = 500, verbose: bool = False) -> Dict:
        """
        稳态求解（恒定流）

        通过迭代确保所有渠道段和闸门流量守恒

        Args:
            dt: 时间步长 (s)
            Q_upstream: 上游边界流量 (m³/s)
            h_downstream: 下游边界水深 (m) - 如果为None则自动计算
            max_iterations: 最大迭代次数
            verbose: 是否打印详细信息

        Returns:
            收敛信息字典
        """
        # 如果未指定下游边界，使用均匀流水深
        if h_downstream is None:
            h_downstream = compute_steady_uniform_flow(Q_upstream, self.B, self.S0, self.n, self.g)

        converged = False

        for iter_count in range(max_iterations):
            # 从上游到下游逐段求解
            Q_bc_up = Q_upstream

            for i, segment in enumerate(self.segments):
                # 上游边界流量
                Q_up = Q_bc_up

                # 下游边界条件
                if i == len(self.segments) - 1:
                    # 最后一段：使用给定的下游边界
                    h_down = h_downstream
                else:
                    # 中间段：根据闸门流量反算所需水深
                    structure = self.structures[i]
                    Q_gate = self.structure_flows[i]

                    # 获取下游段的水深作为闸门下游水深
                    h_gate_down = self.segments[i+1].h[0]

                    # 从堰流公式反算所需的上游水深
                    if isinstance(structure, type(structure)) and hasattr(structure, 'opening'):
                        # 平板闸门：Q = Cd * B * e * sqrt(2*g*delta_h)
                        C = structure.Cd * structure.width * structure.opening
                        if Q_gate > 1e-6:
                            delta_h = (Q_gate / C) ** 2 / (2 * structure.g)
                        else:
                            delta_h = 1e-4
                        h_down = h_gate_down + delta_h
                    else:
                        # 其他类型，暂时使用简化处理
                        h_down = h_gate_down + 0.01

                # 更新该段
                segment.step(dt, Q_up, h_down)

                # 计算闸门流量（如果有）
                if i < len(self.structures):
                    structure = self.structures[i]
                    h_up = segment.h[-1]
                    h_dn = self.segments[i+1].h[0]

                    Q_gate_new, _ = structure.calculate_discharge(h_up, h_dn)

                    # 检查收敛
                    Q_gate_old = self.structure_flows[i]
                    if abs(Q_gate_new - Q_gate_old) > self.coupling_tol:
                        # 使用松弛更新
                        self.structure_flows[i] = (
                            Q_gate_old * (1 - self.coupling_relax) +
                            Q_gate_new * self.coupling_relax
                        )
                    else:
                        self.structure_flows[i] = Q_gate_new

                    # 下一段的上游流量
                    Q_bc_up = self.structure_flows[i]

            # 检查全局收敛
            if iter_count > 50:  # 至少迭代50次
                all_converged = True
                for i, structure in enumerate(self.structures):
                    h_up = self.segments[i].h[-1]
                    h_dn = self.segments[i+1].h[0]
                    Q_calc, _ = structure.calculate_discharge(h_up, h_dn)

                    if abs(Q_calc - self.structure_flows[i]) > self.coupling_tol:
                        all_converged = False
                        break

                if all_converged:
                    # 检查流量守恒
                    Q_errors = []
                    for seg in self.segments:
                        Q_avg = np.mean(seg.Q[1:-1])
                        Q_errors.append(abs(Q_avg - Q_upstream) / Q_upstream)

                    if max(Q_errors) < 0.001:  # < 0.1%
                        converged = True
                        if verbose:
                            print(f"✓ 稳态收敛 (iter={iter_count+1})")
                        break

        return {
            'converged': converged,
            'iterations': iter_count + 1,
            'structure_flows': self.structure_flows.copy(),
            'Q_errors': Q_errors if converged else None
        }

    def step(self, dt: float, Q_upstream: float, h_downstream: Optional[float] = None):
        """
        非恒定流时间步进

        采用预估-校正方法进行耦合：
        1. 预估：使用上一时刻的闸门流量设置边界条件
        2. 校正：根据实际水位差更新闸门流量（带松弛）
        3. 不恢复状态，让系统自然演化

        Args:
            dt: 时间步长 (s)
            Q_upstream: 上游边界流量 (m³/s)
            h_downstream: 下游边界水深 (m) - 如果为None则根据流量自动计算
        """
        # 预估：使用上一时刻的闸门流量
        Q_gates_pred = self.structure_flows.copy()

        # 从上游到下游求解各段
        Q_bc_up = Q_upstream

        for i, segment in enumerate(self.segments):
            # 上游流量边界
            Q_up = Q_bc_up

            # 下游边界条件
            if i == len(self.segments) - 1:
                # 最后一段：下游边界
                if h_downstream is None:
                    # 使用当前段的平均流量计算正常水深
                    Q_avg = np.mean(segment.Q[1:-1])
                    h_down = compute_steady_uniform_flow(Q_avg, self.B, self.S0, self.n, self.g)
                else:
                    h_down = h_downstream
            else:
                # 中间段：闸门上游
                # 使用预估的闸门流量反算所需的下游水深
                structure = self.structures[i]
                Q_gate_pred = Q_gates_pred[i]
                h_gate_down = self.segments[i+1].h[0]

                # 从堰流公式反算：给定Q_gate，h_down需要多少才能产生这个流量
                if hasattr(structure, 'opening'):
                    C = structure.Cd * structure.width * structure.opening
                    if Q_gate_pred > 1e-6:
                        delta_h_required = (Q_gate_pred / C) ** 2 / (2 * structure.g)
                    else:
                        delta_h_required = 1e-4
                    h_down = h_gate_down + delta_h_required
                else:
                    h_down = h_gate_down + 0.01

            # 更新该段
            segment.step(dt, Q_up, h_down)

            # 计算闸门流量（校正）
            if i < len(self.structures):
                structure = self.structures[i]
                h_up_actual = segment.h[-1]
                h_dn_actual = self.segments[i+1].h[0]

                # 根据实际水位差计算闸门流量
                Q_gate_calc, _ = structure.calculate_discharge(h_up_actual, h_dn_actual)

                # 松弛更新：允许闸门流量逐渐调整，避免振荡
                # 这是关键：不强制Q_gate等于预估值，而是让它根据实际水位差逐步调整
                alpha = 0.5  # 更大的松弛因子以加快响应
                Q_gate_new = Q_gates_pred[i] * (1 - alpha) + Q_gate_calc * alpha

                # 更新闸门流量记录
                self.structure_flows[i] = Q_gate_new

                # 下一段的上游流量
                Q_bc_up = Q_gate_new

    def get_full_profile(self) -> Dict[str, np.ndarray]:
        """
        获取全渠道剖面数据

        Returns:
            包含x, h, Q的字典
        """
        x_list = []
        h_list = []
        Q_list = []

        x_offset = 0.0
        for i, segment in enumerate(self.segments):
            # 除了最后一段，其他段去掉最后一个点（避免重复）
            if i < len(self.segments) - 1:
                x_list.append(segment.x[:-1] + x_offset)
                h_list.append(segment.h[:-1])
                Q_list.append(segment.Q[:-1])
            else:
                x_list.append(segment.x + x_offset)
                h_list.append(segment.h)
                Q_list.append(segment.Q)

            x_offset += segment.length

        return {
            'x': np.concatenate(x_list),
            'h': np.concatenate(h_list),
            'Q': np.concatenate(Q_list),
        }

    def clear_history(self):
        """清空所有段的历史记录"""
        for segment in self.segments:
            segment.clear_history()

    def __repr__(self) -> str:
        return (f"CoupledCanalSolver(length={self.total_length}m, "
                f"segments={len(self.segments)}, structures={len(self.structures)})")
