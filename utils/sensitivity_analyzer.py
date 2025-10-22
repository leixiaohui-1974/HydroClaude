#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
参数敏感性分析工具

分析不同参数对求解结果的影响

作者: Claude
日期: 2025-10-22
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from typing import Dict, List, Callable, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
import time

from physics.steady_saint_venant import SteadySaintVenantSystem
from solvers.newton_solver import NewtonSolver

# 设置样式
mpl.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
mpl.rcParams['axes.unicode_minus'] = False


@dataclass
class SensitivityResult:
    """敏感性分析结果"""
    parameter_name: str
    parameter_values: List[float]
    output_values: List[float]
    baseline_value: float
    baseline_output: float


class SensitivityAnalyzer:
    """参数敏感性分析器"""

    def __init__(self, output_dir: str = "sensitivity_results"):
        """
        初始化分析器

        Args:
            output_dir: 结果输出目录
        """
        self.output_dir = output_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    def analyze_parameter(self,
                         base_system_func: Callable,
                         solver_func: Callable,
                         parameter_name: str,
                         parameter_values: List[float],
                         output_metric: Callable[[np.ndarray, np.ndarray], float],
                         baseline_value: float = None,
                         verbose: bool = True) -> SensitivityResult:
        """
        分析单个参数的敏感性

        Args:
            base_system_func: 创建系统的函数 (param_value) -> (system, U_init)
            solver_func: 求解函数 (system, U_init) -> (h, Q, info)
            parameter_name: 参数名称
            parameter_values: 参数值列表
            output_metric: 输出指标函数 (h, Q) -> float
            baseline_value: 基线参数值
            verbose: 是否输出详细信息

        Returns:
            SensitivityResult: 敏感性分析结果
        """
        if verbose:
            print(f"\n分析参数: {parameter_name}")
            print(f"  参数范围: {min(parameter_values):.4f} - {max(parameter_values):.4f}")
            print(f"  测试点数: {len(parameter_values)}")
            print()

        output_values = []
        baseline_output = None

        for i, param_value in enumerate(parameter_values):
            if verbose:
                print(f"  [{i+1}/{len(parameter_values)}] {parameter_name}={param_value:.4f}...", end=" ", flush=True)

            try:
                # 创建系统
                system, U_init = base_system_func(param_value)

                # 求解
                h, Q, info = solver_func(system, U_init)

                if info['converged']:
                    # 计算输出指标
                    output = output_metric(h, Q)
                    output_values.append(output)

                    if baseline_value is not None and abs(param_value - baseline_value) < 1e-6:
                        baseline_output = output

                    if verbose:
                        print(f"✅ 输出={output:.6f}")
                else:
                    output_values.append(np.nan)
                    if verbose:
                        print("❌ 未收敛")

            except Exception as e:
                output_values.append(np.nan)
                if verbose:
                    print(f"❌ 失败: {e}")

        return SensitivityResult(
            parameter_name=parameter_name,
            parameter_values=parameter_values,
            output_values=output_values,
            baseline_value=baseline_value,
            baseline_output=baseline_output
        )

    def plot_sensitivity(self,
                        result: SensitivityResult,
                        output_name: str = "Output",
                        save_path: str = None) -> str:
        """
        绘制敏感性曲线

        Args:
            result: 敏感性分析结果
            output_name: 输出指标名称
            save_path: 保存路径

        Returns:
            图片保存路径
        """
        fig, ax = plt.subplots(figsize=(10, 6))

        # 过滤NaN值
        valid_indices = ~np.isnan(result.output_values)
        x_valid = np.array(result.parameter_values)[valid_indices]
        y_valid = np.array(result.output_values)[valid_indices]

        # 绘制曲线
        ax.plot(x_valid, y_valid, 'o-', linewidth=2, markersize=6,
               color='#3498db', label='Computed Values')

        # 标注基线
        if result.baseline_value is not None and result.baseline_output is not None:
            ax.plot(result.baseline_value, result.baseline_output, 'r*',
                   markersize=15, label='Baseline', zorder=5)
            ax.axvline(x=result.baseline_value, color='red', linestyle='--',
                      alpha=0.5, linewidth=1.5)
            ax.axhline(y=result.baseline_output, color='red', linestyle='--',
                      alpha=0.5, linewidth=1.5)

        ax.set_xlabel(f'{result.parameter_name}', fontsize=12, fontweight='bold')
        ax.set_ylabel(f'{output_name}', fontsize=12, fontweight='bold')
        ax.set_title(f'Sensitivity Analysis: {output_name} vs {result.parameter_name}',
                    fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()

        plt.tight_layout()

        if save_path is None:
            save_path = os.path.join(self.output_dir,
                                    f'sensitivity_{result.parameter_name}.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()

        return save_path

    def plot_multi_sensitivity(self,
                              results: List[SensitivityResult],
                              output_name: str = "Output",
                              save_path: str = None) -> str:
        """
        绘制多参数敏感性对比

        Args:
            results: 多个敏感性分析结果
            output_name: 输出指标名称
            save_path: 保存路径

        Returns:
            图片保存路径
        """
        n_results = len(results)
        fig, axes = plt.subplots(1, n_results, figsize=(6 * n_results, 5))

        if n_results == 1:
            axes = [axes]

        colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6']

        for i, result in enumerate(results):
            ax = axes[i]

            # 过滤NaN值
            valid_indices = ~np.isnan(result.output_values)
            x_valid = np.array(result.parameter_values)[valid_indices]
            y_valid = np.array(result.output_values)[valid_indices]

            # 归一化到基线（如果有）
            if result.baseline_output is not None and result.baseline_output != 0:
                y_normalized = (y_valid - result.baseline_output) / result.baseline_output * 100
                ylabel = f'{output_name} Change (%)'
                baseline_y = 0.0
            else:
                y_normalized = y_valid
                ylabel = output_name
                baseline_y = result.baseline_output

            ax.plot(x_valid, y_normalized, 'o-', linewidth=2, markersize=6,
                   color=colors[i % len(colors)])

            if result.baseline_value is not None:
                ax.axvline(x=result.baseline_value, color='red', linestyle='--',
                          alpha=0.5, linewidth=1.5, label='Baseline')
                ax.axhline(y=baseline_y, color='red', linestyle='--',
                          alpha=0.5, linewidth=1.5)

            ax.set_xlabel(f'{result.parameter_name}', fontsize=11, fontweight='bold')
            ax.set_ylabel(ylabel, fontsize=11, fontweight='bold')
            ax.set_title(f'{result.parameter_name}', fontsize=12, fontweight='bold')
            ax.grid(True, alpha=0.3)
            if result.baseline_value is not None:
                ax.legend()

        plt.tight_layout()

        if save_path is None:
            save_path = os.path.join(self.output_dir, 'multi_sensitivity.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()

        return save_path

    def compute_sensitivity_index(self, result: SensitivityResult) -> float:
        """
        计算敏感性指数

        敏感性指数 = (输出变化率) / (参数变化率)

        Args:
            result: 敏感性分析结果

        Returns:
            敏感性指数
        """
        # 过滤NaN值
        valid_indices = ~np.isnan(result.output_values)
        x = np.array(result.parameter_values)[valid_indices]
        y = np.array(result.output_values)[valid_indices]

        if len(x) < 2:
            return np.nan

        # 使用线性拟合计算斜率
        coeffs = np.polyfit(x, y, 1)
        slope = coeffs[0]

        # 归一化到基线
        if result.baseline_value is not None and result.baseline_output is not None:
            # 敏感性指数 = (dy/y0) / (dx/x0)
            sensitivity = (slope * result.baseline_value) / result.baseline_output
        else:
            sensitivity = slope

        return sensitivity


def main():
    """测试敏感性分析"""
    from solvers.gate import SluiceGate
    from utils.canal_utils import compute_steady_uniform_flow

    print("=" * 100)
    print("参数敏感性分析演示")
    print("=" * 100)

    # 基础配置
    length = 1000.0
    nx = 51
    B = 10.0
    S0 = 0.001
    n = 0.025
    Q_target = 10.0
    baseline_opening = 5.0

    # 创建分析器
    analyzer = SensitivityAnalyzer(output_dir="sensitivity_results")

    # 定义系统创建函数（闸门开度作为参数）
    def create_system(gate_opening):
        gate = SluiceGate(position=500.0, width=B, opening=gate_opening, Cd=0.6)
        system = SteadySaintVenantSystem(
            length, nx, B, S0, n,
            structures=[(500.0, gate)],
            pseudo_dt=0.1
        )
        h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)
        system.set_boundary_conditions(
            Q_upstream=Q_target,
            h_upstream=h_uniform,
            h_downstream=h_uniform
        )
        h_init = np.ones(nx) * h_uniform
        Q_init = np.ones(nx) * Q_target
        U_init = system.pack_state(h_init, Q_init)
        system.U_prev = U_init.copy()
        return system, U_init

    # 定义求解函数
    def solve_system(system, U_init):
        newton = NewtonSolver(max_iter=30, tol_residual=1e-4, verbose=False)
        U_sol, info = newton.solve(
            U_init=U_init,
            residual_func=lambda U: system.compute_residual(U, 0.0),
            jacobian_func=lambda U: system.compute_jacobian(U, 0.0)
        )
        h, Q = system.unpack_state(U_sol)
        return h, Q, info

    # 定义输出指标（闸门处的最大水深）
    def max_depth_metric(h, Q):
        return np.max(h)

    # 测试闸门开度敏感性
    print("\n" + "=" * 100)
    print("测试1: 闸门开度敏感性")
    print("=" * 100)

    gate_openings = np.linspace(3.0, 7.0, 9)  # 从3m到7m
    result_opening = analyzer.analyze_parameter(
        base_system_func=create_system,
        solver_func=solve_system,
        parameter_name="Gate Opening (m)",
        parameter_values=gate_openings.tolist(),
        output_metric=max_depth_metric,
        baseline_value=baseline_opening,
        verbose=True
    )

    # 计算敏感性指数
    sensitivity_index = analyzer.compute_sensitivity_index(result_opening)
    print(f"\n敏感性指数: {sensitivity_index:.6f}")

    # 绘制敏感性曲线
    print("\n生成可视化图表...")
    plot_path = analyzer.plot_sensitivity(result_opening, output_name="Max Water Depth (m)")
    print(f"✅ 保存到: {plot_path}")

    print("\n" + "=" * 100)
    print("敏感性分析完成")
    print("=" * 100)


if __name__ == '__main__':
    main()
