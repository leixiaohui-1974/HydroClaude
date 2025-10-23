#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
集成Anderson加速的明渠求解器

扩展CanalSolver，使用Anderson加速替代Aitken加速

作者: Claude
日期: 2025-10-22
"""

import numpy as np
from typing import List, Tuple, Optional
from solvers.canal_solver import CanalSolver
from solvers.anderson_acceleration import AndersonAcceleration


class CanalSolverAnderson(CanalSolver):
    """
    集成Anderson加速的明渠求解器

    在内部边界条件迭代中使用Anderson加速，
    替代原有的Aitken加速
    """

    def __init__(self,
                 length: float,
                 nx: int,
                 B: float,
                 S0: float,
                 n: float,
                 g: float = 9.81,
                 anderson_m: int = 5,
                 anderson_beta: float = 1.0,
                 anderson_reg: float = 1e-8,
                 anderson_restart: bool = True):
        """
        Args:
            length: 渠道长度 (m)
            nx: 网格点数
            B: 渠道宽度 (m)
            S0: 渠底坡度
            n: 曼宁糙率系数
            g: 重力加速度 (m/s²)
            anderson_m: Anderson加速历史深度
            anderson_beta: Anderson松弛因子
            anderson_reg: Anderson正则化参数
            anderson_restart: 是否自动重启Anderson加速
        """
        super().__init__(length, nx, B, S0, n, g)

        # Anderson加速参数
        self.anderson_m = anderson_m
        self.anderson_beta = anderson_beta
        self.anderson_reg = anderson_reg
        self.anderson_restart = anderson_restart

        # Anderson加速器（稳态求解时初始化）
        self.anderson = None

    def _apply_internal_bc_anderson(self, t: float = 0.0, max_iter: int = 10,
                                   tol: float = 0.01, verbose: bool = False):
        """
        使用Anderson加速应用内部边界条件

        Args:
            t: 当前时间 (s)
            max_iter: 最大迭代次数
            tol: 收敛容差 (m³/s)
            verbose: 是否打印详细信息
        """
        if not self.structure_indices:
            return

        # 初始化Anderson加速器
        if self.anderson is None:
            self.anderson = AndersonAcceleration(
                m=self.anderson_m,
                beta=self.anderson_beta,
                reg=self.anderson_reg,
                restart=self.anderson_restart
            )

        # 提取结构节点的流量向量
        n_structures = len(self.structure_indices)
        Q_struct = np.array([self.Q[idx] for idx in self.structure_indices])

        for iter_count in range(max_iter):
            # 计算目标流量（固定点函数 g(Q)）
            Q_target = np.zeros(n_structures)

            for i, (idx, structure) in enumerate(zip(self.structure_indices, self.structure_objects)):
                # 获取上下游水深
                if idx <= 0 or idx >= self.nx - 1:
                    Q_target[i] = self.Q[idx]  # 边界处保持不变
                    continue

                h_up = self.h[idx - 1]
                h_down = self.h[idx + 1]

                # 计算结构流量
                Q_gate, _ = structure.calculate_discharge(h_up, h_down, t)
                Q_target[i] = Q_gate

            # 计算残差
            residual = Q_target - Q_struct
            residual_norm = np.linalg.norm(residual) / n_structures

            if verbose and iter_count % 100 == 0:
                print(f"    Anderson迭代 {iter_count}: 残差={residual_norm:.6f} m³/s")

            # 检查收敛
            if residual_norm < tol:
                if verbose:
                    print(f"    ✓ Anderson加速收敛 (迭代{iter_count}, 残差={residual_norm:.6f} m³/s)")
                break

            # Anderson加速
            if iter_count == 0:
                # 第一次迭代：直接使用目标值
                Q_struct_new = Q_target
            else:
                # 使用Anderson加速
                Q_struct_new = self.anderson.compute_acceleration(Q_struct, Q_target)

            # 更新结构节点流量
            for i, idx in enumerate(self.structure_indices):
                self.Q[idx] = Q_struct_new[i]

                # 调整邻近节点流量以保持平滑
                if idx > 1:
                    self.Q[idx - 1] = 0.5 * (self.Q[idx - 2] + Q_struct_new[i])
                if idx < self.nx - 2:
                    self.Q[idx + 1] = 0.5 * (Q_struct_new[i] + self.Q[idx + 2])

            # 更新当前流量向量
            Q_struct = Q_struct_new.copy()

        else:
            if verbose:
                print(f"    ⚠ Anderson加速未收敛 (达到最大迭代{max_iter}, 残差={residual_norm:.6f} m³/s)")

    def solve_steady_state_anderson(self,
                                    Q_target: float,
                                    h_downstream: float = None,
                                    max_iter: int = 10000,
                                    tol: float = 0.005,
                                    verbose: bool = True,
                                    internal_bc_max_iter: int = 20) -> bool:
        """
        使用Anderson加速求解稳态

        Args:
            Q_target: 目标流量 (m³/s)
            h_downstream: 下游水深 (m)，None则使用均匀流水深
            max_iter: 最大外层迭代次数
            tol: 收敛容差（相对误差）
            verbose: 是否打印进度
            internal_bc_max_iter: 内部边界条件最大迭代次数

        Returns:
            是否收敛
        """
        # 重置Anderson加速器
        self.anderson = None

        # 设置下游边界
        if h_downstream is None:
            h_downstream = self.compute_normal_depth(Q_target)
        self.h[-1] = h_downstream

        if verbose:
            print(f"开始稳态求解（目标流量: {Q_target} m³/s, Anderson加速）...")

        # 时间步长（隐式法）
        dt = 1.0

        converged = False
        self.steady_iteration_count = 0

        for iter_count in range(max_iter):
            self.steady_iteration_count = iter_count + 1

            # 保存旧值
            h_old = self.h.copy()
            Q_old = self.Q.copy()

            # 执行一步时间推进（隐式）
            self.step(dt, method='implicit')

            # 强制上游流量
            self.Q[0] = Q_target

            # 应用内部边界条件（使用Anderson加速）
            self._apply_internal_bc_anderson(
                t=0.0,
                max_iter=internal_bc_max_iter,
                tol=Q_target * tol,  # 绝对容差
                verbose=False
            )

            # 检查整体收敛
            if iter_count % 500 == 0 or iter_count < 10:
                # 计算平均流量和误差
                Q_avg = np.mean([self.Q[idx] for idx in self.structure_indices]) if self.structure_indices else np.mean(self.Q)
                error = abs(Q_avg - Q_target) / Q_target

                if verbose:
                    if self.structure_indices:
                        Q_gates = [self.Q[idx] for idx in self.structure_indices]
                        Q_str = ", ".join([f"Q{i+1}={Q:.3f}" for i, Q in enumerate(Q_gates)])
                        print(f"  t={iter_count+1}s: Q_avg={Q_avg:.4f} m³/s, 误差={error*100:.4f}%, {Q_str}")
                    else:
                        print(f"  t={iter_count+1}s: Q={Q_avg:.4f} m³/s, 误差={error*100:.4f}%")

                if error < tol:
                    converged = True
                    if verbose:
                        print(f"\n✓ 达到稳态 (i={iter_count}, t={iter_count+1}s)")
                    break

        if not converged and verbose:
            Q_avg = np.mean([self.Q[idx] for idx in self.structure_indices]) if self.structure_indices else np.mean(self.Q)
            error = abs(Q_avg - Q_target) / Q_target
            print(f"\n✗ 未收敛 (i={max_iter}, 误差={error*100:.4f}%)")

        return converged

    def get_anderson_stats(self) -> dict:
        """
        获取Anderson加速统计信息

        Returns:
            包含迭代次数、重启次数等信息的字典
        """
        if self.anderson is None:
            return {
                'iteration': 0,
                'restart_count': 0,
                'active': False
            }

        return {
            'iteration': self.anderson.iteration,
            'restart_count': self.anderson.restart_count,
            'active': True
        }
