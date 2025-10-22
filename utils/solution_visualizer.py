#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
求解结果可视化工具

绘制水深、流量、流速等沿程分布图

作者: Claude
日期: 2025-10-22
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from physics.steady_saint_venant import SteadySaintVenantSystem

# 设置样式
mpl.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
mpl.rcParams['axes.unicode_minus'] = False


class SolutionVisualizer:
    """求解结果可视化器"""

    def __init__(self, output_dir: str = "visualization_results"):
        """
        初始化可视化器

        Args:
            output_dir: 图片输出目录
        """
        self.output_dir = output_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # 配色方案
        self.colors = {
            'h': '#3498db',  # 蓝色 - 水深
            'Q': '#2ecc71',  # 绿色 - 流量
            'V': '#e74c3c',  # 红色 - 流速
            'structure': '#95a5a6',  # 灰色 - 结构
            'grid': '#ecf0f1'  # 浅灰 - 网格
        }

    def plot_profile(self,
                     system: SteadySaintVenantSystem,
                     h: np.ndarray,
                     Q: np.ndarray,
                     title: str = "Flow Profile",
                     save_path: Optional[str] = None,
                     show_structures: bool = True) -> str:
        """
        绘制沿程水深和流量分布

        Args:
            system: 系统实例
            h: 水深数组
            Q: 流量数组
            title: 图表标题
            save_path: 保存路径
            show_structures: 是否显示结构位置

        Returns:
            图片保存路径
        """
        x = system.x

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

        # 子图1: 水深
        ax1.plot(x, h, color=self.colors['h'], linewidth=2, label='Water Depth')
        ax1.fill_between(x, 0, h, alpha=0.3, color=self.colors['h'])
        ax1.set_ylabel('Water Depth h (m)', fontsize=12, fontweight='bold')
        ax1.set_title(title, fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='best')

        # 标注结构位置
        if show_structures and system.structures:
            for pos, structure in system.structures:
                ax1.axvline(x=pos, color=self.colors['structure'],
                           linestyle='--', alpha=0.6, linewidth=1.5)
                # 添加结构标签
                idx = np.argmin(np.abs(x - pos))
                ax1.annotate(f'{structure.__class__.__name__}',
                           xy=(pos, h[idx]),
                           xytext=(pos, h[idx] * 1.1),
                           fontsize=9,
                           ha='center',
                           bbox=dict(boxstyle='round,pad=0.3',
                                    facecolor=self.colors['structure'],
                                    alpha=0.3))

        # 子图2: 流量
        ax2.plot(x, Q, color=self.colors['Q'], linewidth=2, label='Discharge')
        ax2.set_xlabel('Distance x (m)', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Discharge Q (m³/s)', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='best')

        # 标注结构位置
        if show_structures and system.structures:
            for pos, structure in system.structures:
                ax2.axvline(x=pos, color=self.colors['structure'],
                           linestyle='--', alpha=0.6, linewidth=1.5)

        plt.tight_layout()

        if save_path is None:
            save_path = os.path.join(self.output_dir, 'flow_profile.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()

        return save_path

    def plot_velocity(self,
                      system: SteadySaintVenantSystem,
                      h: np.ndarray,
                      Q: np.ndarray,
                      title: str = "Velocity Distribution",
                      save_path: Optional[str] = None) -> str:
        """
        绘制流速分布

        Args:
            system: 系统实例
            h: 水深数组
            Q: 流量数组
            title: 图表标题
            save_path: 保存路径

        Returns:
            图片保存路径
        """
        x = system.x
        A = system.B * h  # 断面面积
        V = Q / (A + 1e-10)  # 流速

        fig, ax = plt.subplots(figsize=(12, 6))

        ax.plot(x, V, color=self.colors['V'], linewidth=2, label='Velocity')
        ax.fill_between(x, 0, V, alpha=0.3, color=self.colors['V'])
        ax.set_xlabel('Distance x (m)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Velocity V (m/s)', fontsize=12, fontweight='bold')
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best')

        # 标注结构位置
        if system.structures:
            for pos, structure in system.structures:
                ax.axvline(x=pos, color=self.colors['structure'],
                          linestyle='--', alpha=0.6, linewidth=1.5,
                          label='Structure' if pos == system.structures[0][0] else '')

        plt.tight_layout()

        if save_path is None:
            save_path = os.path.join(self.output_dir, 'velocity_distribution.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()

        return save_path

    def plot_froude_number(self,
                          system: SteadySaintVenantSystem,
                          h: np.ndarray,
                          Q: np.ndarray,
                          title: str = "Froude Number Distribution",
                          save_path: Optional[str] = None) -> str:
        """
        绘制Froude数分布

        Args:
            system: 系统实例
            h: 水深数组
            Q: 流量数组
            title: 图表标题
            save_path: 保存路径

        Returns:
            图片保存路径
        """
        x = system.x
        A = system.B * h
        V = Q / (A + 1e-10)
        Fr = V / np.sqrt(system.g * h + 1e-10)  # Froude数

        fig, ax = plt.subplots(figsize=(12, 6))

        ax.plot(x, Fr, color='#9b59b6', linewidth=2, label='Froude Number')
        ax.axhline(y=1.0, color='red', linestyle='--', linewidth=1.5,
                  alpha=0.7, label='Critical Flow (Fr=1)')
        ax.fill_between(x, Fr, 1.0, where=(Fr < 1.0), alpha=0.3,
                       color='blue', label='Subcritical (Fr<1)')
        ax.fill_between(x, 1.0, Fr, where=(Fr > 1.0), alpha=0.3,
                       color='red', label='Supercritical (Fr>1)')

        ax.set_xlabel('Distance x (m)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Froude Number Fr', fontsize=12, fontweight='bold')
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best')

        # 标注结构位置
        if system.structures:
            for pos, structure in system.structures:
                ax.axvline(x=pos, color=self.colors['structure'],
                          linestyle='--', alpha=0.6, linewidth=1.5)

        plt.tight_layout()

        if save_path is None:
            save_path = os.path.join(self.output_dir, 'froude_number.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()

        return save_path

    def plot_energy_grade_line(self,
                               system: SteadySaintVenantSystem,
                               h: np.ndarray,
                               Q: np.ndarray,
                               title: str = "Energy Grade Line",
                               save_path: Optional[str] = None) -> str:
        """
        绘制能量线和水面线

        Args:
            system: 系统实例
            h: 水深数组
            Q: 流量数组
            title: 图表标题
            save_path: 保存路径

        Returns:
            图片保存路径
        """
        x = system.x

        # 计算底高程（假设为常坡度）
        z_bed = system.length * system.S0 - x * system.S0

        # 水面高程
        z_water = z_bed + h

        # 流速水头
        A = system.B * h
        V = Q / (A + 1e-10)
        V_head = V**2 / (2 * system.g)

        # 能量线
        z_energy = z_water + V_head

        fig, ax = plt.subplots(figsize=(14, 7))

        # 绘制底床
        ax.fill_between(x, 0, z_bed, color='#8b4513', alpha=0.5, label='Channel Bed')

        # 绘制水体
        ax.fill_between(x, z_bed, z_water, color=self.colors['h'],
                       alpha=0.6, label='Water')

        # 绘制水面线
        ax.plot(x, z_water, color='blue', linewidth=2, label='Water Surface')

        # 绘制能量线
        ax.plot(x, z_energy, color='red', linewidth=2,
               linestyle='--', label='Energy Grade Line')

        ax.set_xlabel('Distance x (m)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Elevation (m)', fontsize=12, fontweight='bold')
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best', fontsize=10)

        # 标注结构位置
        if system.structures:
            for pos, structure in system.structures:
                idx = np.argmin(np.abs(x - pos))
                ax.plot([pos, pos], [z_bed[idx], z_energy[idx]],
                       color=self.colors['structure'], linewidth=2, alpha=0.7)
                ax.text(pos, z_energy[idx] * 1.02, structure.__class__.__name__,
                       fontsize=9, ha='center', rotation=90,
                       bbox=dict(boxstyle='round,pad=0.3',
                                facecolor='white', alpha=0.8))

        plt.tight_layout()

        if save_path is None:
            save_path = os.path.join(self.output_dir, 'energy_grade_line.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()

        return save_path

    def plot_comparison(self,
                       results: Dict[str, Tuple[SteadySaintVenantSystem, np.ndarray, np.ndarray]],
                       variable: str = 'h',
                       title: str = "Comparison",
                       save_path: Optional[str] = None) -> str:
        """
        对比多个求解结果

        Args:
            results: 结果字典 {name: (system, h, Q)}
            variable: 对比变量 ('h', 'Q', 'V')
            title: 图表标题
            save_path: 保存路径

        Returns:
            图片保存路径
        """
        fig, ax = plt.subplots(figsize=(12, 6))

        colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6']

        for i, (name, (system, h, Q)) in enumerate(results.items()):
            x = system.x

            if variable == 'h':
                y = h
                ylabel = 'Water Depth h (m)'
            elif variable == 'Q':
                y = Q
                ylabel = 'Discharge Q (m³/s)'
            elif variable == 'V':
                A = system.B * h
                y = Q / (A + 1e-10)
                ylabel = 'Velocity V (m/s)'
            else:
                raise ValueError(f"Unknown variable: {variable}")

            ax.plot(x, y, color=colors[i % len(colors)],
                   linewidth=2, label=name, marker='o', markersize=3,
                   markevery=max(1, len(x)//20))

        ax.set_xlabel('Distance x (m)', fontsize=12, fontweight='bold')
        ax.set_ylabel(ylabel, fontsize=12, fontweight='bold')
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best')

        plt.tight_layout()

        if save_path is None:
            save_path = os.path.join(self.output_dir, f'{variable}_comparison.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()

        return save_path

    def generate_complete_report(self,
                                system: SteadySaintVenantSystem,
                                h: np.ndarray,
                                Q: np.ndarray,
                                scenario_name: str = "Solution") -> Dict[str, str]:
        """
        生成完整的可视化报告

        Args:
            system: 系统实例
            h: 水深数组
            Q: 流量数组
            scenario_name: 场景名称

        Returns:
            Dict: {plot_name: file_path}
        """
        plots = {}

        print(f"生成 {scenario_name} 的可视化报告...")

        print("  1/5 流态剖面图...", end=" ", flush=True)
        plots['profile'] = self.plot_profile(system, h, Q,
                                            title=f"{scenario_name} - Flow Profile")
        print("✅")

        print("  2/5 流速分布图...", end=" ", flush=True)
        plots['velocity'] = self.plot_velocity(system, h, Q,
                                              title=f"{scenario_name} - Velocity Distribution")
        print("✅")

        print("  3/5 Froude数分布...", end=" ", flush=True)
        plots['froude'] = self.plot_froude_number(system, h, Q,
                                                  title=f"{scenario_name} - Froude Number")
        print("✅")

        print("  4/5 能量线图...", end=" ", flush=True)
        plots['energy'] = self.plot_energy_grade_line(system, h, Q,
                                                      title=f"{scenario_name} - Energy Grade Line")
        print("✅")

        print()
        print(f"所有图表已保存到: {self.output_dir}")

        return plots


def main():
    """测试可视化工具"""
    from physics.steady_saint_venant import SteadySaintVenantSystem
    from solvers.newton_solver import NewtonSolver
    from solvers.gate import SluiceGate
    from utils.canal_utils import compute_steady_uniform_flow

    print("=" * 100)
    print("求解结果可视化演示")
    print("=" * 100)
    print()

    # 三闸门场景
    length = 1000.0
    nx = 101
    B = 10.0
    S0 = 0.001
    n = 0.025
    Q_target = 10.0

    gate1 = SluiceGate(position=250.0, width=B, opening=4.5, Cd=0.6)
    gate2 = SluiceGate(position=500.0, width=B, opening=4.0, Cd=0.6)
    gate3 = SluiceGate(position=750.0, width=B, opening=5.0, Cd=0.6)

    h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)

    system = SteadySaintVenantSystem(
        length, nx, B, S0, n,
        structures=[
            (gate1.position, gate1),
            (gate2.position, gate2),
            (gate3.position, gate3)
        ],
        pseudo_dt=0.1
    )

    system.set_boundary_conditions(
        Q_upstream=Q_target,
        h_upstream=h_uniform,
        h_downstream=h_uniform
    )

    # 求解
    print("求解三闸门场景...")
    h_init = np.ones(nx) * h_uniform
    Q_init = np.ones(nx) * Q_target
    U_init = system.pack_state(h_init, Q_init)
    system.U_prev = U_init.copy()

    newton = NewtonSolver(max_iter=30, tol_residual=1e-4, verbose=False)
    U_sol, info = newton.solve(
        U_init=U_init,
        residual_func=lambda U: system.compute_residual(U, 0.0),
        jacobian_func=lambda U: system.compute_jacobian(U, 0.0)
    )

    h_sol, Q_sol = system.unpack_state(U_sol)
    print(f"✅ 收敛: {info['converged']}, 迭代: {info['iterations']}次\n")

    # 可视化
    visualizer = SolutionVisualizer(output_dir="visualization_results")
    plots = visualizer.generate_complete_report(system, h_sol, Q_sol,
                                                scenario_name="Three Gates")

    print()
    print("=" * 100)
    print("生成的图表:")
    print("=" * 100)
    for name, path in plots.items():
        print(f"  {name}: {path}")


if __name__ == '__main__':
    main()
