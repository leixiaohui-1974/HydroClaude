#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
示例24: 水库多目标优化调度

演示Pareto最优解的生成和权衡分析

目标函数:
1. 最大化发电量
2. 最小化水位波动
3. 满足生态流量约束
4. 防洪安全

作者: HydroClaude Team
日期: 2025-10-22
"""

import sys
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import Tuple, List, Dict
from dataclasses import dataclass

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.constants import PhysicsConstants


@dataclass
class ObjectiveWeights:
    """多目标权重"""
    power_generation: float = 0.5      # 发电量权重
    water_stability: float = 0.3        # 水位稳定性权重
    ecological_flow: float = 0.1        # 生态流量权重
    flood_control: float = 0.1          # 防洪安全权重


class MultiObjectiveReservoirScheduler:
    """
    多目标水库调度器

    使用加权法和Pareto分析进行多目标优化
    """

    def __init__(self,
                 total_capacity: float = 50e6,     # 总库容 (m^3)
                 min_level: float = 100.0,         # 最低水位 (m)
                 normal_level: float = 120.0,      # 正常水位 (m)
                 flood_level: float = 125.0,       # 防洪限制水位 (m)
                 turbine_capacity: float = 100.0,  # 装机容量 (MW)
                 ecological_flow: float = 10.0):   # 生态流量 (m^3/s)

        self.total_capacity = total_capacity
        self.min_level = min_level
        self.normal_level = normal_level
        self.flood_level = flood_level
        self.turbine_capacity = turbine_capacity
        self.ecological_flow = ecological_flow

        # 库容-水位关系 (简化为线性)
        self.level_range = 25.0  # m
        self.capacity_per_meter = total_capacity / self.level_range

    def optimize_single_objective(self,
                                  inflow_forecast: np.ndarray,
                                  initial_storage: float,
                                  weights: ObjectiveWeights,
                                  dt: float = 3600.0) -> Dict:
        """
        单次优化运行（给定权重）

        Args:
            inflow_forecast: 入流预报序列 (m^3/s)
            initial_storage: 初始库容 (m^3)
            weights: 目标权重
            dt: 时间步长 (s)

        Returns:
            优化结果字典
        """
        n_steps = len(inflow_forecast)

        # 初始化状态
        storage = np.zeros(n_steps + 1)
        level = np.zeros(n_steps + 1)
        outflow = np.zeros(n_steps)
        power = np.zeros(n_steps)

        storage[0] = initial_storage
        level[0] = self._storage_to_level(storage[0])

        # 简化优化：使用启发式规则
        for t in range(n_steps):
            current_level = level[t]
            current_storage = storage[t]
            inflow = inflow_forecast[t]

            # 计算目标出流
            target_outflow = self._calculate_target_outflow(
                current_level, inflow, weights)

            # 约束出流
            actual_outflow = max(self.ecological_flow, target_outflow)
            actual_outflow = min(actual_outflow, 200.0)  # 最大泄流能力

            # 水量平衡
            new_storage = current_storage + (inflow - actual_outflow) * dt

            # 库容约束
            if new_storage < 0:
                new_storage = 0
                actual_outflow = max(0, inflow + current_storage / dt)
            elif new_storage > self.total_capacity:
                new_storage = self.total_capacity
                actual_outflow = inflow + (current_storage - self.total_capacity) / dt

            # 更新状态
            storage[t + 1] = new_storage
            level[t + 1] = self._storage_to_level(new_storage)
            outflow[t] = actual_outflow

            # 计算发电量
            head = level[t + 1] - self.min_level
            power[t] = self._calculate_power(actual_outflow, head)

        # 计算目标函数值
        objectives = self._evaluate_objectives(
            level, outflow, power, inflow_forecast)

        return {
            'storage': storage,
            'level': level,
            'outflow': outflow,
            'power': power,
            'objectives': objectives,
            'weights': weights
        }

    def _storage_to_level(self, storage: float) -> float:
        """库容转水位"""
        return self.min_level + storage / self.capacity_per_meter

    def _calculate_target_outflow(self,
                                  level: float,
                                  inflow: float,
                                  weights: ObjectiveWeights) -> float:
        """
        计算目标出流（启发式）

        Args:
            level: 当前水位 (m)
            inflow: 当前入流 (m^3/s)
            weights: 目标权重

        Returns:
            目标出流 (m^3/s)
        """
        # 基准出流
        base_outflow = inflow

        # 根据水位调整
        if level > self.flood_level:
            # 超过防洪限制，增加出流
            base_outflow = inflow * 1.5
        elif level > self.normal_level:
            # 接近防洪限制，适当增加出流
            base_outflow = inflow * 1.2
        elif level < self.min_level + 5:
            # 接近最低水位，减少出流
            base_outflow = inflow * 0.7

        # 根据权重调整
        if weights.power_generation > 0.5:
            # 优先发电，保持较高水位
            if level < self.normal_level - 5:
                base_outflow *= 0.8

        if weights.flood_control > 0.3:
            # 优先防洪，降低水位
            if level > self.normal_level - 2:
                base_outflow *= 1.3

        return base_outflow

    def _calculate_power(self, outflow: float, head: float) -> float:
        """
        计算发电功率

        Args:
            outflow: 出流 (m^3/s)
            head: 水头 (m)

        Returns:
            功率 (MW)
        """
        efficiency = 0.85
        power = PhysicsConstants.GRAVITY * outflow * head * efficiency / 1000.0
        return min(power, self.turbine_capacity)

    def _evaluate_objectives(self,
                            level: np.ndarray,
                            outflow: np.ndarray,
                            power: np.ndarray,
                            inflow: np.ndarray) -> Dict:
        """
        评估所有目标函数

        Args:
            level: 水位序列
            outflow: 出流序列
            power: 功率序列
            inflow: 入流序列

        Returns:
            目标函数值字典
        """
        # 1. 总发电量 (MWh) - 越大越好
        total_power = np.sum(power)  # 假设每步1小时

        # 2. 水位波动 (m) - 越小越好
        level_std = np.std(level)

        # 3. 生态流量满足度 (%) - 越高越好
        eco_satisfaction = np.mean(outflow >= self.ecological_flow) * 100

        # 4. 防洪安全性 (%) - 越高越好
        flood_safety = np.mean(level <= self.flood_level) * 100

        return {
            'power_generation': total_power,
            'level_stability': -level_std,  # 负号使其最大化
            'ecological_satisfaction': eco_satisfaction,
            'flood_safety': flood_safety
        }

    def generate_pareto_front(self,
                             inflow_forecast: np.ndarray,
                             initial_storage: float,
                             n_points: int = 20) -> List[Dict]:
        """
        生成Pareto前沿

        通过变化权重生成多个解

        Args:
            inflow_forecast: 入流预报
            initial_storage: 初始库容
            n_points: Pareto点数量

        Returns:
            Pareto解列表
        """
        pareto_solutions = []

        # 生成不同的权重组合
        for i in range(n_points):
            # 在发电和防洪之间权衡
            power_weight = i / (n_points - 1)
            flood_weight = 1.0 - power_weight

            weights = ObjectiveWeights(
                power_generation=power_weight * 0.8,
                flood_control=flood_weight * 0.8,
                water_stability=0.1,
                ecological_flow=0.1
            )

            # 运行优化
            solution = self.optimize_single_objective(
                inflow_forecast, initial_storage, weights)

            pareto_solutions.append(solution)

        return pareto_solutions


def demo_multi_objective_optimization():
    """演示多目标优化"""

    print("="*80)
    print("示例24: 水库多目标优化调度")
    print("="*80)
    print()

    # ========================================
    # 1. 创建调度器
    # ========================================

    scheduler = MultiObjectiveReservoirScheduler(
        total_capacity=50e6,      # 5000万m^3
        min_level=100.0,
        normal_level=120.0,
        flood_level=125.0,
        turbine_capacity=100.0,
        ecological_flow=10.0
    )

    print("【系统参数】")
    print(f"  总库容: {scheduler.total_capacity/1e6:.0f} 万m^3")
    print(f"  水位范围: {scheduler.min_level} - {scheduler.flood_level} m")
    print(f"  装机容量: {scheduler.turbine_capacity} MW")
    print(f"  生态流量: {scheduler.ecological_flow} m^3/s")
    print()

    # ========================================
    # 2. 生成入流场景
    # ========================================

    n_days = 7
    n_steps = n_days * 24  # 小时步长

    # 生成变化的入流（包含洪水过程）
    time_hours = np.arange(n_steps)
    base_inflow = 80.0  # m^3/s

    # 添加洪水过程
    flood_peak_time = 48  # 第2天
    flood_duration = 24   # 持续1天
    flood_magnitude = 150.0  # 洪峰增量

    inflow_forecast = np.ones(n_steps) * base_inflow
    for t in range(n_steps):
        if abs(t - flood_peak_time) < flood_duration / 2:
            # 三角形洪水过程
            flood_contrib = flood_magnitude * (1 - abs(t - flood_peak_time) / (flood_duration / 2))
            inflow_forecast[t] += flood_contrib

    print("【入流场景】")
    print(f"  仿真时长: {n_days} 天 ({n_steps} 小时)")
    print(f"  基流: {base_inflow} m^3/s")
    print(f"  洪峰: {np.max(inflow_forecast):.1f} m^3/s (第{flood_peak_time}小时)")
    print()

    # ========================================
    # 3. 生成Pareto前沿
    # ========================================

    print("【生成Pareto前沿】")
    print("  正在计算不同权重组合的优化解...")
    print()

    initial_storage = scheduler.total_capacity * 0.6  # 60%库容

    pareto_solutions = scheduler.generate_pareto_front(
        inflow_forecast, initial_storage, n_points=15)

    print(f"  生成 {len(pareto_solutions)} 个Pareto解")
    print()

    # ========================================
    # 4. 分析三个典型方案
    # ========================================

    print("【典型方案对比】")
    print("-" * 80)

    # 选择三个代表性方案
    power_priority = pareto_solutions[0]    # 发电优先
    balanced = pareto_solutions[7]          # 平衡方案
    flood_priority = pareto_solutions[-1]   # 防洪优先

    schemes = [
        ("发电优先", power_priority),
        ("平衡方案", balanced),
        ("防洪优先", flood_priority)
    ]

    print(f"{'方案':<15} {'发电量(MWh)':<15} {'水位波动(m)':<15} {'防洪安全(%)':<15}")
    print("-" * 80)

    for name, sol in schemes:
        obj = sol['objectives']
        print(f"{name:<15} {obj['power_generation']:<15.1f} "
              f"{-obj['level_stability']:<15.2f} {obj['flood_safety']:<15.1f}")

    print()

    # ========================================
    # 5. 可视化结果
    # ========================================

    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

    # 子图1: Pareto前沿 (发电 vs 防洪)
    ax1 = fig.add_subplot(gs[0, :2])
    power_vals = [s['objectives']['power_generation'] for s in pareto_solutions]
    flood_vals = [s['objectives']['flood_safety'] for s in pareto_solutions]

    ax1.plot(power_vals, flood_vals, 'b-o', linewidth=2, markersize=6,
            label='Pareto Front')

    # 标记三个典型方案
    for i, (name, sol) in enumerate(schemes):
        obj = sol['objectives']
        color = ['red', 'green', 'orange'][i]
        ax1.plot(obj['power_generation'], obj['flood_safety'],
                marker='*', markersize=15, color=color, label=name)

    ax1.set_xlabel('Total Power Generation (MWh)')
    ax1.set_ylabel('Flood Safety (%)')
    ax1.set_title('Pareto Front: Power vs Flood Control')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 子图2-4: 三个方案的水位过程
    time_days = time_hours / 24

    for idx, (name, sol) in enumerate(schemes):
        ax = fig.add_subplot(gs[1, idx])
        # level has n_steps+1 elements (includes initial state), so skip first element
        ax.plot(time_days, sol['level'][1:], linewidth=2, label='Water Level')
        ax.axhline(scheduler.normal_level, color='g', linestyle='--',
                  linewidth=1.5, label='Normal Level')
        ax.axhline(scheduler.flood_level, color='r', linestyle='--',
                  linewidth=1.5, label='Flood Level')
        ax.set_xlabel('Time (days)')
        ax.set_ylabel('Water Level (m)')
        ax.set_title(f'{name} - Water Level')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    # 子图5-7: 三个方案的出流过程
    for idx, (name, sol) in enumerate(schemes):
        ax = fig.add_subplot(gs[2, idx])
        ax.plot(time_days, inflow_forecast, 'b--', linewidth=1.5,
                alpha=0.7, label='Inflow')
        ax.plot(time_days, sol['outflow'], 'r-', linewidth=2, label='Outflow')
        ax.axhline(scheduler.ecological_flow, color='g', linestyle=':',
                  linewidth=1.5, label='Ecological Flow')
        ax.set_xlabel('Time (days)')
        ax.set_ylabel('Flow (m^3/s)')
        ax.set_title(f'{name} - Flow')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    # 子图8: 目标函数权衡
    ax8 = fig.add_subplot(gs[0, 2])

    power_norm = np.array(power_vals) / np.max(power_vals)
    flood_norm = np.array(flood_vals) / 100.0

    ax8.plot(power_norm, label='Power (normalized)', linewidth=2)
    ax8.plot(flood_norm, label='Flood Safety (normalized)', linewidth=2)
    ax8.set_xlabel('Solution Index')
    ax8.set_ylabel('Normalized Objective Value')
    ax8.set_title('Objective Trade-off')
    ax8.legend()
    ax8.grid(True, alpha=0.3)

    plt.suptitle('Multi-Objective Reservoir Optimization',
                fontsize=16, fontweight='bold', y=0.995)

    output_path = 'examples/example_24_multi_objective_optimization/multi_objective_optimization.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"图像已保存到: {output_path}")
    print()

    # ========================================
    # 6. 决策建议
    # ========================================

    print("【决策建议】")
    print("-" * 80)
    print()

    print("1. 发电优先方案:")
    print("   - 适用场景: 枯水期、电力紧张")
    print("   - 优点: 发电量最大")
    print("   - 缺点: 防洪风险较高")
    print()

    print("2. 平衡方案:")
    print("   - 适用场景: 一般运行工况")
    print("   - 优点: 兼顾发电和防洪")
    print("   - 推荐: 大部分时间采用")
    print()

    print("3. 防洪优先方案:")
    print("   - 适用场景: 汛期、洪水预报")
    print("   - 优点: 防洪安全性最高")
    print("   - 缺点: 牺牲部分发电量")
    print()

    print("4. 动态调整策略:")
    print("   - 根据来水预报动态选择方案")
    print("   - 枯水期偏向发电优先")
    print("   - 汛期偏向防洪优先")
    print("   - 平时采用平衡方案")
    print()

    return pareto_solutions


if __name__ == '__main__':
    solutions = demo_multi_objective_optimization()

    print("="*80)
    print("示例24完成!")
    print("="*80)
    print()
    print("关键成果:")
    print("   Pareto前沿生成")
    print("   多目标权衡分析")
    print("   典型方案对比")
    print("   决策支持建议")
    print("   动态调整策略")
