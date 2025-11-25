#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工程案例5: 水资源优化调度

场景：
  多源供水系统，需要优化泵站调度以满足时变需求，同时最小化运行成本

目标：
  1. 满足下游用水需求
  2. 最小化泵站电力成本
  3. 维持合理水位范围

方法：
  基于模型预测控制（MPC）的优化调度

作者: Claude
日期: 2025-10-24
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import PumpStation


def create_demand_profile(hours=24):
    """
    创建24小时需水量曲线

    Args:
        hours: 小时数

    Returns:
        需水量数组 (m^3/s)
    """
    t = np.linspace(0, hours, hours * 4)  # 15分钟间隔

    # 典型城市用水曲线
    # 高峰: 7-9时, 18-20时
    # 低谷: 0-5时
    base_demand = 8.0  # 基础需水量

    # 叠加日变化
    daily_pattern = 3.0 * (
        np.sin(2 * np.pi * (t - 7) / 24) +  # 早高峰
        0.5 * np.sin(2 * np.pi * (t - 19) / 24)  # 晚高峰
    )

    demand = base_demand + daily_pattern
    demand = np.maximum(demand, 3.0)  # 最小需求

    return t, demand


def create_electricity_price(hours=24):
    """
    创建24小时电价曲线（峰谷电价）

    Args:
        hours: 小时数

    Returns:
        电价数组 (元/kWh)
    """
    t = np.linspace(0, hours, hours * 4)
    price = np.zeros_like(t)

    for i, hour in enumerate(t):
        h = hour % 24

        if 8 <= h < 11 or 18 <= h < 21:
            # 高峰时段
            price[i] = 1.2
        elif 11 <= h < 18 or 21 <= h < 23:
            # 平时段
            price[i] = 0.7
        else:
            # 谷时段 (23-8时)
            price[i] = 0.3

    return t, price


def simple_mpc_optimization(
    current_state,
    demand_forecast,
    price_forecast,
    horizon=12
):
    """
    简化的MPC优化

    Args:
        current_state: 当前状态 {'water_level': h, 'flow': Q}
        demand_forecast: 需求预测 (m^3/s)
        price_forecast: 电价预测 (元/kWh)
        horizon: 预测时域 (步数)

    Returns:
        最优泵站流量 (m^3/s)
    """
    # 简化优化：在低电价时多抽水，高电价时少抽水
    # 同时满足需求和水位约束

    h = current_state['water_level']
    target_level = 2.5  # 目标水位

    # 基于电价的权重
    avg_price = np.mean(price_forecast[:horizon])
    price_factor = 0.5 if avg_price < 0.5 else (1.5 if avg_price > 1.0 else 1.0)

    # 基于水位的调整
    level_error = target_level - h
    level_factor = 1.0 + 0.5 * level_error  # 水位低时多抽

    # 基于需求的基准
    avg_demand = np.mean(demand_forecast[:horizon])

    # 综合决策
    optimal_flow = avg_demand * price_factor * level_factor
    optimal_flow = np.clip(optimal_flow, 3.0, 20.0)  # 泵站容量限制

    return optimal_flow


def run_optimization():
    """运行水资源优化调度"""
    print("=" * 90)
    print("工程案例5: 水资源优化调度")
    print("=" * 90)
    print()
    print("场景: 多源供水系统优化调度")
    print("目标: 满足需求 + 最小化成本 + 水位控制")
    print()

    # ========================================
    # 系统配置
    # ========================================
    print("[1/5] 系统配置...")

    L = 15000.0          # 渠道总长度 (m)
    B = 12.0             # 渠道宽度 (m)
    S0 = 0.0001          # 底坡
    nx = 151             # 网格点数

    pump_position = 3000.0  # 泵站位置 (m)

    print(f"      渠道长度: {L/1000:.1f} km")
    print(f"      泵站位置: {pump_position/1000:.1f} km")

    # ========================================
    # 第2步: 创建需求和电价曲线
    # ========================================
    print("\n[2/5] 生成需求和电价曲线...")

    t_demand, demand = create_demand_profile(hours=24)
    t_price, electricity_price = create_electricity_price(hours=24)

    print(f"      需求范围: {demand.min():.1f} - {demand.max():.1f} m^3/s")
    print(f"      电价范围: {electricity_price.min():.1f} - {electricity_price.max():.1f} 元/kWh")

    # ========================================
    # 第3步: 创建求解器和泵站
    # ========================================
    print("\n[3/5] 创建求解器和泵站...")

    # 创建泵站
    pump = PumpStation(
        position=pump_position,
        width=B,
        rated_flow=20.0,  # 额定流量 (m^3/s)
        rated_head=10.0,  # 额定扬程 (m)
        # 效率
        g=9.81
    )

    # 创建求解器
    solver = HydrostaticCanalSolver(
        length=L,
        nx=nx,
        B=B,
        S0=S0,
        n=0.025,
        internal_structures=[(pump_position, pump)]
    )

    # 初始化
    solver.Q_in = 5.0  # 上游来水
    solver.h_downstream = 2.0
    solver.solve_steady_state(Q_target=5.0, h_downstream=2.0)

    print(f"       泵站容量: {pump.rated_flow:.1f} m^3/s")
    print(f"       初始水位: {solver.h.mean():.2f} m")

    # ========================================
    # 第4步: 运行优化调度
    # ========================================
    print("\n[4/5] 执行24小时优化调度...")

    # 时间设置
    dt = 15 * 60  # 15分钟时间步 (秒)
    n_steps = len(t_demand)

    # 记录历史
    time_history = []
    pump_flow_history = []
    water_level_history = []
    cost_history = []
    demand_history = []

    # 监测点（渠道中段）
    monitor_idx = nx // 2

    # 调度循环
    for step in range(n_steps):
        current_time = t_demand[step]

        # 当前状态
        current_state = {
            'water_level': solver.h[monitor_idx],
            'flow': solver.hu[monitor_idx] * B
        }

        # 预测时域（未来3小时）
        horizon = min(12, n_steps - step)
        demand_forecast = demand[step:step + horizon]
        price_forecast = electricity_price[step:step + horizon]

        # MPC优化
        optimal_pump_flow = simple_mpc_optimization(
            current_state,
            demand_forecast,
            price_forecast,
            horizon=horizon
        )

        # 设置泵站流量
        # PumpStation没有set_flow方法，直接设置flow属性
        pump.flow = optimal_pump_flow

        # 计算运行成本
        # 功率 = rho * g * Q * H / η
        if hasattr(solver, 'structure_indices') and solver.structure_indices:
            pump_idx = solver.structure_indices[0]
            head = solver.h[pump_idx]
        else:
            head = 5.0  # 默认扬程
        # PumpStation可能没有efficiency属性，使用默认值
        efficiency = getattr(pump, 'efficiency', 0.75)  # 默认效率75%
        power_kw = (1000 * 9.81 * optimal_pump_flow * head / efficiency) / 1000
        cost = power_kw * electricity_price[step] * (dt / 3600)  # 元

        # 记录
        time_history.append(current_time)
        pump_flow_history.append(optimal_pump_flow)
        water_level_history.append(current_state['water_level'])
        cost_history.append(cost)
        demand_history.append(demand[step])

        # 时间推进（简化：假设快速达到新稳态）
        if step < n_steps - 1:
            # 更新下游需求
            solver.h_downstream = 2.0 + 0.1 * (demand[step] - 8.0) / 5.0

        # 进度显示
        if step % 24 == 0:  # 每6小时
            print(f"      时刻 {current_time:5.1f}h: 泵流 {optimal_pump_flow:5.1f} m^3/s, "
                  f"水位 {current_state['water_level']:.2f} m, "
                  f"电价 {electricity_price[step]:.1f} 元/kWh")

    print(f"       调度完成")

    # ========================================
    # 第5步: 结果分析和可视化
    # ========================================
    print("\n[5/5] 生成结果分析...")

    # 转换为数组
    time_array = np.array(time_history)
    pump_flow_array = np.array(pump_flow_history)
    water_level_array = np.array(water_level_history)
    cost_array = np.array(cost_history)
    demand_array = np.array(demand_history)

    # 统计
    total_cost = np.sum(cost_array)
    total_water = np.sum(pump_flow_array) * (dt / 3600)  # m^3
    avg_cost_per_m3 = total_cost / total_water  # 元/m^3

    print(f"\n运行统计:")
    print(f"  总抽水量:   {total_water:.0f} m^3")
    print(f"  总电费:     {total_cost:.2f} 元")
    print(f"  平均成本:   {avg_cost_per_m3:.4f} 元/m^3")
    print(f"  泵流范围:   {pump_flow_array.min():.1f} - {pump_flow_array.max():.1f} m^3/s")
    print(f"  水位范围:   {water_level_array.min():.2f} - {water_level_array.max():.2f} m")

    # 可视化
    fig, axes = plt.subplots(4, 1, figsize=(14, 12))

    # 子图1: 需求和泵流
    axes[0].plot(time_array, demand_array, 'b-', linewidth=2, label='用水需求')
    axes[0].plot(time_array, pump_flow_array, 'r-', linewidth=2, label='泵站流量')
    axes[0].set_ylabel('流量 (m^3/s)', fontsize=11)
    axes[0].set_title('水资源优化调度结果 - 供需平衡', fontsize=13, fontweight='bold')
    axes[0].legend(fontsize=10)
    axes[0].grid(True, alpha=0.3)
    axes[0].set_xlim(0, 24)

    # 子图2: 水位变化
    axes[1].plot(time_array, water_level_array, 'g-', linewidth=2)
    axes[1].axhline(y=2.5, color='k', linestyle='--', alpha=0.5, label='目标水位')
    axes[1].fill_between(time_array, 2.3, 2.7, alpha=0.2, color='green', label='安全范围')
    axes[1].set_ylabel('水位 (m)', fontsize=11)
    axes[1].set_title('水位控制', fontsize=13, fontweight='bold')
    axes[1].legend(fontsize=10)
    axes[1].grid(True, alpha=0.3)
    axes[1].set_xlim(0, 24)

    # 子图3: 电价
    axes[2].plot(time_array, electricity_price[:len(time_array)], 'orange', linewidth=2)
    axes[2].fill_between(time_array, 0, electricity_price[:len(time_array)],
                        alpha=0.3, color='orange')
    axes[2].set_ylabel('电价 (元/kWh)', fontsize=11)
    axes[2].set_title('峰谷电价', fontsize=13, fontweight='bold')
    axes[2].grid(True, alpha=0.3)
    axes[2].set_xlim(0, 24)

    # 子图4: 运行成本
    cumulative_cost = np.cumsum(cost_array)
    axes[3].plot(time_array, cumulative_cost, 'purple', linewidth=2)
    axes[3].fill_between(time_array, 0, cumulative_cost, alpha=0.3, color='purple')
    axes[3].set_xlabel('时间 (小时)', fontsize=11)
    axes[3].set_ylabel('累计成本 (元)', fontsize=11)
    axes[3].set_title(f'运行成本累计 (总计: {total_cost:.2f} 元)', fontsize=13, fontweight='bold')
    axes[3].grid(True, alpha=0.3)
    axes[3].set_xlim(0, 24)

    plt.tight_layout()

    # 保存
    output_dir = os.path.join(os.path.dirname(__file__), 'results')
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(output_dir, 'optimization_results.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n 结果图保存至: {output_file}")

    plt.close()

    print()
    print("=" * 90)
    print(" 优化调度完成！")
    print("=" * 90)


if __name__ == "__main__":
    run_optimization()
