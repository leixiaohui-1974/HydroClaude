#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
案例2: 河道洪水演进模拟
Case 02: River Flood Routing Simulation

模拟洪水波在天然河道中的传播过程，分析洪峰削减和传播时间。
Simulates flood wave propagation in a natural river channel,
analyzing peak reduction and travel time.

作者: HydroClaude Team
日期: 2025-10-31
阶段: Stage 8 - Phase 8.3
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, Tuple

from solvers.godunov_fvm_solver import GodunvFVMSolver


class FloodRoutingSimulation:
    """
    洪水演进模拟

    河道特征:
    - 长度: 50 km
    - 断面: 梯形
    - 底宽: 30m, 边坡: 1:2
    - 粗糙度: n=0.030 (天然河道)
    - 坡度: 1/1000

    洪水过程:
    - 洪峰流量: 1000 m³/s
    - 涨洪历时: 6 hours
    - 落洪历时: 12 hours
    """

    def __init__(self):
        # 河道参数
        self.L = 50000.0  # 河道长度 (m)
        self.B = 30.0     # 河底宽度 (m)
        self.m = 2.0      # 边坡系数 (1:m)
        self.n = 0.030    # 曼宁粗糙度
        self.S0 = 0.001   # 河床坡度

        # 数值计算参数
        self.n_cells = 200  # 网格数
        self.dx = self.L / self.n_cells
        self.cfl = 0.5

        # 洪水参数
        self.Q_peak = 1000.0  # 洪峰流量 (m³/s)
        self.T_rise = 6.0 * 3600  # 涨洪历时 (s)
        self.T_fall = 12.0 * 3600  # 落洪历时 (s)
        self.T_total = self.T_rise + self.T_fall  # 总时长 (s)

        # 初始水深
        self.h0 = 3.0  # m

        # 重力加速度
        self.g = 9.81

    def create_inflow_hydrograph(self, t: float) -> float:
        """
        创建上游入流过程

        采用三角形洪水过程:
        - 0 → T_rise: 线性上涨到洪峰
        - T_rise → T_total: 线性下降到基流

        Args:
            t: 时间 (s)

        Returns:
            流量 (m³/s)
        """
        Q_base = 100.0  # 基流 (m³/s)

        if t <= 0:
            return Q_base
        elif t < self.T_rise:
            # 涨洪段
            return Q_base + (self.Q_peak - Q_base) * (t / self.T_rise)
        elif t < self.T_total:
            # 落洪段
            return Q_base + (self.Q_peak - Q_base) * (1 - (t - self.T_rise) / self.T_fall)
        else:
            return Q_base

    def initialize_solver(self) -> GodunvFVMSolver:
        """
        初始化FVM求解器

        Returns:
            配置好的求解器实例
        """
        solver = GodunvFVMSolver(
            width=self.B,
            length=self.L,
            n_cells=self.n_cells,
            manning_n=self.n,
            slope=self.S0,
            g=self.g,
            cfl=self.cfl,
            order=1  # 使用一阶格式，更稳定
        )

        # 初始条件：均匀流
        Q_init = self.create_inflow_hydrograph(0.0)
        solver.h[:] = self.h0
        solver.Q[:] = Q_init * np.ones(self.n_cells)

        return solver

    def run_simulation(self, save_interval: float = 3600.0) -> Dict:
        """
        运行洪水演进模拟

        Args:
            save_interval: 结果保存间隔 (s), 默认1小时

        Returns:
            结果字典，包含时间序列和水位流量数据
        """
        print("\n" + "="*70)
        print("河道洪水演进模拟")
        print("="*70)
        print(f"河道长度: {self.L/1000:.1f} km")
        print(f"网格数: {self.n_cells}")
        print(f"洪峰流量: {self.Q_peak:.1f} m³/s")
        print(f"总时长: {self.T_total/3600:.1f} hours")
        print("="*70 + "\n")

        # 初始化求解器
        solver = self.initialize_solver()

        # 结果存储
        results = {
            'time': [],
            'h_profile': [],
            'Q_profile': [],
            'Q_upstream': [],
            'Q_downstream': [],
            'h_upstream': [],
            'h_downstream': []
        }

        # 时间步进
        t = 0.0
        step = 0
        save_counter = 0
        next_save = 0

        while t < self.T_total:
            # 计算时间步长
            dt = solver.compute_dt()

            # 上游边界：入流流量
            Q_in = self.create_inflow_hydrograph(t)
            A_in = solver.B * solver.h[0]
            solver.Q[0] = Q_in

            # 下游边界：自由出流
            solver.h[-1] = solver.h[-2]
            solver.Q[-1] = solver.Q[-2]

            # 时间步进
            solver.step(dt)

            t += dt
            step += 1

            # 保存结果
            if t >= next_save:
                results['time'].append(t)
                results['h_profile'].append(solver.h.copy())
                results['Q_profile'].append(solver.Q.copy())
                results['Q_upstream'].append(solver.Q[0])
                results['Q_downstream'].append(solver.Q[-1])
                results['h_upstream'].append(solver.h[0])
                results['h_downstream'].append(solver.h[-1])

                save_counter += 1
                next_save = save_counter * save_interval

                # 打印进度
                hours = t / 3600
                Q_up = solver.Q[0]
                Q_down = solver.Q[-1]
                h_max = np.max(solver.h)
                print(f"t={hours:6.2f}h | Q_上={Q_up:7.1f}m³/s | Q_下={Q_down:7.1f}m³/s | h_max={h_max:5.2f}m")

        print(f"\n模拟完成！总步数: {step}, 最终时间: {t/3600:.2f} hours\n")

        # 转换为numpy数组
        for key in ['time', 'h_profile', 'Q_profile', 'Q_upstream',
                    'Q_downstream', 'h_upstream', 'h_downstream']:
            results[key] = np.array(results[key])

        # 分析洪峰削减
        self.analyze_peak_reduction(results)

        return results

    def analyze_peak_reduction(self, results: Dict):
        """
        分析洪峰削减效果

        Args:
            results: 模拟结果
        """
        Q_up_max = np.max(results['Q_upstream'])
        Q_down_max = np.max(results['Q_downstream'])

        # 洪峰削减率
        reduction_rate = (Q_up_max - Q_down_max) / Q_up_max * 100

        # 洪峰传播时间
        idx_up = np.argmax(results['Q_upstream'])
        idx_down = np.argmax(results['Q_downstream'])
        t_up = results['time'][idx_up]
        t_down = results['time'][idx_down]
        travel_time = (t_down - t_up) / 3600  # hours

        print("="*70)
        print("洪峰削减分析")
        print("="*70)
        print(f"上游洪峰: {Q_up_max:.1f} m³/s")
        print(f"下游洪峰: {Q_down_max:.1f} m³/s")
        print(f"削减幅度: {Q_up_max - Q_down_max:.1f} m³/s ({reduction_rate:.1f}%)")
        print(f"洪峰传播时间: {travel_time:.2f} hours")
        print(f"平均波速: {self.L / (travel_time * 3600):.2f} m/s")
        print("="*70 + "\n")

    def visualize_results(self, results: Dict, save_path: str = None):
        """
        可视化模拟结果

        Args:
            results: 模拟结果
            save_path: 图片保存路径
        """
        fig = plt.figure(figsize=(16, 10))

        # 1. 上下游流量过程
        ax1 = plt.subplot(2, 3, 1)
        time_hours = results['time'] / 3600
        ax1.plot(time_hours, results['Q_upstream'], 'b-', linewidth=2, label='Upstream')
        ax1.plot(time_hours, results['Q_downstream'], 'r-', linewidth=2, label='Downstream')
        ax1.set_xlabel('Time (hours)', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Discharge (m³/s)', fontsize=12, fontweight='bold')
        ax1.set_title('Flood Hydrograph', fontsize=13, fontweight='bold')
        ax1.legend(fontsize=11)
        ax1.grid(True, alpha=0.3)

        # 2. 上下游水位过程
        ax2 = plt.subplot(2, 3, 2)
        ax2.plot(time_hours, results['h_upstream'], 'b-', linewidth=2, label='Upstream')
        ax2.plot(time_hours, results['h_downstream'], 'r-', linewidth=2, label='Downstream')
        ax2.set_xlabel('Time (hours)', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Water Depth (m)', fontsize=12, fontweight='bold')
        ax2.set_title('Water Level Process', fontsize=13, fontweight='bold')
        ax2.legend(fontsize=11)
        ax2.grid(True, alpha=0.3)

        # 3. 洪峰削减
        ax3 = plt.subplot(2, 3, 3)
        Q_up_max = np.max(results['Q_upstream'])
        Q_down_max = np.max(results['Q_downstream'])
        reduction = Q_up_max - Q_down_max
        ax3.bar(['Upstream', 'Downstream'], [Q_up_max, Q_down_max],
                color=['blue', 'red'], alpha=0.7, width=0.5)
        ax3.axhline(Q_up_max, color='blue', linestyle='--', alpha=0.5)
        ax3.text(0.5, Q_up_max + 20, f'Reduction: {reduction:.1f} m³/s',
                ha='center', fontsize=11, fontweight='bold')
        ax3.set_ylabel('Peak Discharge (m³/s)', fontsize=12, fontweight='bold')
        ax3.set_title('Peak Reduction', fontsize=13, fontweight='bold')
        ax3.grid(True, alpha=0.3, axis='y')

        # 4. 水位纵剖面（不同时刻）
        ax4 = plt.subplot(2, 3, 4)
        x_km = np.linspace(0, self.L/1000, self.n_cells)

        # 选择几个关键时刻
        n_profiles = min(5, len(results['time']))
        indices = np.linspace(0, len(results['time'])-1, n_profiles, dtype=int)
        colors = plt.cm.viridis(np.linspace(0, 1, n_profiles))

        for idx, color in zip(indices, colors):
            t_h = results['time'][idx] / 3600
            ax4.plot(x_km, results['h_profile'][idx], color=color,
                    linewidth=2, label=f't={t_h:.1f}h')

        ax4.set_xlabel('Distance (km)', fontsize=12, fontweight='bold')
        ax4.set_ylabel('Water Depth (m)', fontsize=12, fontweight='bold')
        ax4.set_title('Longitudinal Profile', fontsize=13, fontweight='bold')
        ax4.legend(fontsize=10, ncol=2)
        ax4.grid(True, alpha=0.3)

        # 5. 流量纵剖面（不同时刻）
        ax5 = plt.subplot(2, 3, 5)

        for idx, color in zip(indices, colors):
            t_h = results['time'][idx] / 3600
            ax5.plot(x_km, results['Q_profile'][idx], color=color,
                    linewidth=2, label=f't={t_h:.1f}h')

        ax5.set_xlabel('Distance (km)', fontsize=12, fontweight='bold')
        ax5.set_ylabel('Discharge (m³/s)', fontsize=12, fontweight='bold')
        ax5.set_title('Discharge Profile', fontsize=13, fontweight='bold')
        ax5.legend(fontsize=10, ncol=2)
        ax5.grid(True, alpha=0.3)

        # 6. 时空分布图（流量）
        ax6 = plt.subplot(2, 3, 6)

        # 创建流量时空矩阵
        Q_matrix = np.array(results['Q_profile'])
        T_matrix, X_matrix = np.meshgrid(time_hours, x_km)

        contour = ax6.contourf(T_matrix, X_matrix, Q_matrix.T, levels=15, cmap='jet')
        plt.colorbar(contour, ax=ax6, label='Discharge (m³/s)')
        ax6.set_xlabel('Time (hours)', fontsize=12, fontweight='bold')
        ax6.set_ylabel('Distance (km)', fontsize=12, fontweight='bold')
        ax6.set_title('Spatio-Temporal Distribution', fontsize=13, fontweight='bold')

        plt.suptitle('River Flood Routing Simulation - Case 02',
                    fontsize=16, fontweight='bold')
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"✓ 结果已保存: {save_path}\n")

        return fig


def main():
    """
    主函数：运行洪水演进模拟
    """
    # 创建模拟实例
    simulation = FloodRoutingSimulation()

    # 运行模拟
    results = simulation.run_simulation(save_interval=1800.0)  # 每0.5小时保存一次

    # 可视化结果
    output_dir = os.path.join(os.path.dirname(__file__), '../results')
    os.makedirs(output_dir, exist_ok=True)
    save_path = os.path.join(output_dir, 'flood_routing_case02.png')

    simulation.visualize_results(results, save_path=save_path)

    print("="*70)
    print("✅ Case 02: 河道洪水演进模拟完成！")
    print("="*70)


if __name__ == "__main__":
    main()
