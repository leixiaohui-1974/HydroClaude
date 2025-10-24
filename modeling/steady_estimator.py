#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
稳态初值估计器

为非稳态计算提供准确的稳态初值

作者: Claude
日期: 2025-10-24
"""

import numpy as np
from typing import Tuple, Dict, Optional
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.canal_utils import compute_steady_uniform_flow


class SteadyEstimator:
    """
    稳态初值估计器

    提供多种初值估计方法：
    - 均匀流估计
    - 逐渐变化流估计
    - 基于稳态求解的精确估计（推荐）
    """

    def __init__(self):
        """初始化估计器"""
        pass

    def estimate_uniform_flow(self, Q: float, B: float, S0: float, n: float) -> float:
        """
        估算均匀流水深

        Args:
            Q: 流量 (m³/s)
            B: 渠道宽度 (m)
            S0: 渠底坡度
            n: Manning糙率

        Returns:
            h_uniform: 均匀流水深 (m)
        """
        h_uniform = compute_steady_uniform_flow(Q, B, S0, n)
        return h_uniform

    def estimate_gradually_varied_flow(self, x: np.ndarray, Q: float, B: float,
                                      S0: float, n: float,
                                      h_downstream: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        估算逐渐变化流水深分布（简化方法）

        Args:
            x: 网格坐标
            Q: 流量 (m³/s)
            B: 渠道宽度 (m)
            S0: 渠底坡度
            n: Manning糙率
            h_downstream: 下游水深 (m)

        Returns:
            h: 水深分布
            hu: 单宽流量分布
        """
        # 使用能量方程进行简单估算
        h_uniform = self.estimate_uniform_flow(Q, B, S0, n)

        # 线性插值从均匀流到下游水深
        h = np.linspace(h_uniform, h_downstream, len(x))

        # 流量保持恒定
        hu = Q / B * np.ones_like(h)

        return h, hu

    def estimate_from_steady_solution(self, solver, Q_target: float,
                                     h_downstream: float,
                                     max_iterations: int = 5000,
                                     convergence_tol: float = 0.001,
                                     verbose: bool = True) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """
        基于稳态求解获取精确初值（推荐方法）

        Args:
            solver: HydrostaticCanalSolver实例
            Q_target: 目标流量 (m³/s)
            h_downstream: 下游水深 (m)
            max_iterations: 最大迭代次数
            convergence_tol: 收敛容差
            verbose: 是否打印详细信息

        Returns:
            h: 稳态水深分布
            hu: 稳态单宽流量分布
            result: 稳态求解结果字典
        """
        if verbose:
            print("\n" + "=" * 80)
            print("稳态初值估计（精确方法）")
            print("=" * 80)

        # 初始猜测：使用均匀流
        h_uniform = self.estimate_uniform_flow(Q_target, solver.B, solver.S0, solver.n)

        if verbose:
            print(f"\n均匀流估计: h = {h_uniform:.3f} m")
            print("\n开始稳态求解...")

        # 设置初值
        solver.h[:] = h_uniform
        solver.hu[:] = Q_target / solver.B

        # 稳态求解
        result = solver.solve_steady_state(
            Q_target=Q_target,
            h_downstream=h_downstream,
            max_iterations=max_iterations,
            convergence_tol=convergence_tol,
            dt=0.5,
            verbose=verbose
        )

        if result['converged']:
            if verbose:
                print(f"\n✓ 稳态求解成功收敛")
                print(f"  迭代次数: {result['iterations']}")
                print(f"  流量误差: {result.get('final_flow_error', 0):.6f}%")
        else:
            print(f"\n⚠ 稳态求解未完全收敛，但可作为初值")
            print(f"  已执行迭代: {result['iterations']}")

        if verbose:
            print("=" * 80)

        return solver.h.copy(), solver.hu.copy(), result

    def validate_initial_condition(self, x: np.ndarray, h: np.ndarray,
                                  hu: np.ndarray, Q_target: float,
                                  B: float) -> Dict:
        """
        验证初值质量

        Args:
            x: 网格坐标
            h: 水深
            hu: 单宽流量
            Q_target: 目标流量
            B: 渠道宽度

        Returns:
            validation: 验证结果
        """
        Q = hu * B
        Q_mean = np.mean(Q)
        Q_error = abs(Q_mean - Q_target) / Q_target * 100

        validation = {
            'Q_mean': Q_mean,
            'Q_target': Q_target,
            'Q_error_percent': Q_error,
            'h_min': np.min(h),
            'h_max': np.max(h),
            'h_mean': np.mean(h),
            'quality': None
        }

        # 评级
        if Q_error < 0.1:
            validation['quality'] = 'Excellent'
        elif Q_error < 1.0:
            validation['quality'] = 'Good'
        elif Q_error < 5.0:
            validation['quality'] = 'Acceptable'
        else:
            validation['quality'] = 'Poor'

        return validation

    def print_validation(self, validation: Dict):
        """打印验证结果"""
        print("\n初值验证:")
        print(f"  流量误差: {validation['Q_error_percent']:.3f}%")
        print(f"  平均流量: {validation['Q_mean']:.3f} m³/s (目标: {validation['Q_target']:.3f})")
        print(f"  水深范围: [{validation['h_min']:.3f}, {validation['h_max']:.3f}] m")
        print(f"  质量评级: {validation['quality']}")

    def __repr__(self) -> str:
        return "SteadyEstimator()"


if __name__ == "__main__":
    # 测试估计器
    print("=" * 80)
    print("稳态初值估计器测试")
    print("=" * 80)

    estimator = SteadyEstimator()

    # 测试1：均匀流估计
    h_uniform = estimator.estimate_uniform_flow(Q=10.0, B=10.0, S0=0.001, n=0.025)
    print(f"\n1. 均匀流估计: h = {h_uniform:.3f} m")

    # 测试2：逐渐变化流估计
    x = np.linspace(0, 10000, 201)
    h, hu = estimator.estimate_gradually_varied_flow(
        x=x, Q=10.0, B=10.0, S0=0.001, n=0.025, h_downstream=2.0
    )
    print(f"\n2. 逐渐变化流估计:")
    print(f"   上游水深: {h[0]:.3f} m")
    print(f"   下游水深: {h[-1]:.3f} m")

    # 验证初值
    validation = estimator.validate_initial_condition(x, h, hu, Q_target=10.0, B=10.0)
    estimator.print_validation(validation)

    print("\n" + "=" * 80)
