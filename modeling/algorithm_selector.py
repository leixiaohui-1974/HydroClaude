#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最优算法选择器

根据问题特征自动选择最优的数值算法

作者: Claude
日期: 2025-10-24
"""

import numpy as np
from typing import Dict, Optional


class AlgorithmSelector:
    """
    最优算法选择器

    根据以下特征自动选择算法：
    - 问题类型（稳态/非稳态）
    - 渠道长度和网格分辨率
    - 是否有结构物
    - Courant数
    - 预期精度要求
    """

    def __init__(self):
        """初始化算法选择器"""
        self.recommended_algorithm = None
        self.recommendation_reason = []

    def select_steady_solver(self, length: float, nx: int,
                            has_structures: bool = False,
                            accuracy_requirement: str = 'high') -> Dict:
        """
        选择稳态求解算法

        Args:
            length: 渠道长度 (m)
            nx: 网格点数
            has_structures: 是否有结构物
            accuracy_requirement: 精度要求 ('low', 'medium', 'high')

        Returns:
            recommendation: 算法推荐字典
        """
        dx = length / (nx - 1)

        recommendation = {
            'solver': None,
            'method': None,
            'theta': 0.6,
            'omega': 0.95,
            'dt': 0.5,
            'reasons': []
        }

        # 判据1：根据网格分辨率
        if dx > 500:
            recommendation['reasons'].append(
                f"粗网格 (dx={dx:.0f}m): 建议使用隐式方法以提高稳定性"
            )
            use_implicit = True
        else:
            use_implicit = False

        # 判据2：根据结构物
        if has_structures:
            recommendation['reasons'].append(
                "存在结构物: 建议使用Preissmann隐式方法处理内部边界"
            )
            use_implicit = True

        # 判据3：根据精度要求
        if accuracy_requirement == 'high':
            recommendation['reasons'].append(
                "高精度要求: 建议使用Preissmann方法（Phase 2静水重构）"
            )
            recommendation['solver'] = 'HydrostaticCanalSolver'
            recommendation['method'] = 'preissmann'
            recommendation['theta'] = 0.6  # 轻微隐式
            recommendation['omega'] = 0.95  # 较强松弛

        elif use_implicit:
            recommendation['solver'] = 'HydrostaticCanalSolver'
            recommendation['method'] = 'preissmann'
            recommendation['theta'] = 0.7
            recommendation['omega'] = 0.9

        else:
            recommendation['solver'] = 'HydrostaticCanalSolver'
            recommendation['method'] = 'explicit'
            recommendation['reasons'].append(
                f"细网格 (dx={dx:.0f}m) + 无结构物: 可使用显式方法"
            )

        # 根据CFL条件推荐时间步长
        c_max = 10.0  # 估计最大波速 (m/s)
        dt_cfl = 0.5 * dx / c_max
        recommendation['dt'] = min(1.0, dt_cfl)

        if recommendation['dt'] < dt_cfl:
            recommendation['reasons'].append(
                f"根据CFL条件，建议dt≤{dt_cfl:.2f}s"
            )

        return recommendation

    def select_unsteady_solver(self, length: float, nx: int, dt: float,
                              has_structures: bool = False) -> Dict:
        """
        选择非稳态求解算法

        Args:
            length: 渠道长度 (m)
            nx: 网格点数
            dt: 时间步长 (s)
            has_structures: 是否有结构物

        Returns:
            recommendation: 算法推荐字典
        """
        dx = length / (nx - 1)

        recommendation = {
            'solver': 'HydrostaticCanalSolver',
            'method': None,
            'theta': 0.6,
            'omega': 0.95,
            'dt_recommended': dt,
            'reasons': [],
            'warnings': []
        }

        # 计算Courant数
        c_max = 10.0  # 估计最大波速
        courant = c_max * dt / dx

        # 判据1：根据Courant数选择方法
        if courant > 1.0:
            recommendation['method'] = 'preissmann'
            recommendation['theta'] = 0.6  # Preissmann隐式
            recommendation['reasons'].append(
                f"Courant数={courant:.2f} > 1.0: 必须使用隐式方法"
            )

            # 警告过大的Courant数
            if courant > 5.0:
                recommendation['warnings'].append(
                    f"Courant数过大 ({courant:.2f})，建议减小dt或增加nx"
                )
                # 推荐更小的时间步长
                dt_recommended = 0.5 * dx / c_max
                recommendation['dt_recommended'] = dt_recommended
                recommendation['warnings'].append(
                    f"建议dt≤{dt_recommended:.3f}s"
                )

        elif courant > 0.5:
            recommendation['method'] = 'preissmann'
            recommendation['theta'] = 0.55  # 轻度隐式
            recommendation['reasons'].append(
                f"Courant数={courant:.2f}: 建议使用Preissmann方法以确保稳定性"
            )

        else:
            if has_structures:
                recommendation['method'] = 'preissmann'
                recommendation['theta'] = 0.6
                recommendation['reasons'].append(
                    f"Courant数={courant:.2f} (安全), 但存在结构物，仍建议Preissmann方法"
                )
            else:
                recommendation['method'] = 'explicit'
                recommendation['reasons'].append(
                    f"Courant数={courant:.2f} (安全) + 无结构物: 可使用显式方法"
                )

        return recommendation

    def estimate_computational_cost(self, nx: int, nt: int, method: str) -> Dict:
        """
        估算计算成本

        Args:
            nx: 空间网格点数
            nt: 时间步数
            method: 方法 ('explicit' 或 'preissmann')

        Returns:
            cost_estimate: 计算成本估算
        """
        if method == 'explicit':
            # 显式方法：每时间步约 O(nx) 操作
            flops_per_step = nx * 100  # 粗略估计
            memory_mb = nx * 8 * 4 / (1024**2)  # 4个双精度数组
        else:  # preissmann
            # 隐式方法：每时间步约 O(nx * iterations) 操作
            avg_iterations = 10
            flops_per_step = nx * 200 * avg_iterations
            memory_mb = nx * 8 * 6 / (1024**2)  # 更多临时数组

        total_flops = flops_per_step * nt
        estimated_time_seconds = total_flops / 1e9  # 假设1 GFLOPS

        return {
            'method': method,
            'flops_per_step': flops_per_step,
            'total_flops': total_flops,
            'estimated_time_seconds': estimated_time_seconds,
            'estimated_time_minutes': estimated_time_seconds / 60,
            'memory_mb': memory_mb,
            'cost_rating': self._rate_cost(estimated_time_seconds)
        }

    def _rate_cost(self, time_seconds: float) -> str:
        """评级计算成本"""
        if time_seconds < 1:
            return "Very Fast (< 1s)"
        elif time_seconds < 10:
            return "Fast (< 10s)"
        elif time_seconds < 60:
            return "Moderate (< 1min)"
        elif time_seconds < 600:
            return "Slow (< 10min)"
        else:
            return "Very Slow (> 10min)"

    def print_recommendation(self, recommendation: Dict):
        """
        打印推荐结果

        Args:
            recommendation: 推荐结果字典
        """
        print("\n" + "=" * 80)
        print("算法推荐")
        print("=" * 80)
        print(f"\n推荐求解器: {recommendation.get('solver', 'N/A')}")
        print(f"推荐方法: {recommendation.get('method', 'N/A')}")

        if 'theta' in recommendation:
            print(f"Preissmann参数 θ: {recommendation['theta']}")
        if 'omega' in recommendation:
            print(f"松弛因子 ω: {recommendation['omega']}")
        if 'dt' in recommendation:
            print(f"建议时间步长: {recommendation['dt']:.3f} s")

        if recommendation.get('reasons'):
            print("\n推荐理由:")
            for reason in recommendation['reasons']:
                print(f"  • {reason}")

        if recommendation.get('warnings'):
            print("\n⚠ 警告:")
            for warning in recommendation['warnings']:
                print(f"  ⚠ {warning}")

        print("=" * 80)

    def __repr__(self) -> str:
        return "AlgorithmSelector()"


if __name__ == "__main__":
    # 测试算法选择器
    selector = AlgorithmSelector()

    # 场景1：稳态求解，有结构物
    print("\n场景1：稳态求解 + 结构物")
    rec1 = selector.select_steady_solver(
        length=10000,
        nx=201,
        has_structures=True,
        accuracy_requirement='high'
    )
    selector.print_recommendation(rec1)

    # 场景2：非稳态求解，高Courant数
    print("\n场景2：非稳态求解 + 高Courant数")
    rec2 = selector.select_unsteady_solver(
        length=10000,
        nx=201,
        dt=2.0,  # 较大时间步
        has_structures=True
    )
    selector.print_recommendation(rec2)

    # 场景3：计算成本估算
    print("\n场景3：计算成本估算")
    cost = selector.estimate_computational_cost(
        nx=501,
        nt=7200,  # 1小时，dt=0.5s
        method='preissmann'
    )
    print(f"\n方法: {cost['method']}")
    print(f"总浮点操作数: {cost['total_flops']:.2e}")
    print(f"估算时间: {cost['estimated_time_seconds']:.1f}s ({cost['estimated_time_minutes']:.2f}分钟)")
    print(f"内存需求: {cost['memory_mb']:.2f} MB")
    print(f"成本评级: {cost['cost_rating']}")
