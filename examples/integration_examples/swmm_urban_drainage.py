# -*- coding: utf-8 -*-
"""
SWMM城市雨洪系统集成案例

本案例展示如何使用HydroClaude集成EPA SWMM进行城市雨洪模拟

功能展示：
1. SWMM模型的创建和加载
2. 实时监测节点和管道状态
3. PID控制泵站运行
4. 模拟结果的提取和可视化

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys
import os

# 添加项目根目录
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from integration.swmm_adapter import (
    SWMMAdapter,
    SWMMPIDController,
    create_simple_swmm_model,
    PYSWMM_AVAILABLE
)


def example_basic_simulation():
    """示例1：基本SWMM模拟"""
    print("=" * 60)
    print("示例1：基本SWMM模拟")
    print("=" * 60)

    if not PYSWMM_AVAILABLE:
        print("错误: pyswmm未安装")
        print("请使用以下命令安装: pip install pyswmm")
        return

    # 创建测试模型
    model_file = "test_swmm_model.inp"
    create_simple_swmm_model(model_file)

    try:
        # 创建适配器
        adapter = SWMMAdapter(model_file)

        # 运行模拟
        print("\n开始模拟...")

        def progress_callback(adapter, current_time):
            """进度回调"""
            if len(adapter.time_history) % 10 == 0:
                print(f"  模拟时间: {current_time}")

        adapter.run_simulation(callback=progress_callback)

        print("\n模拟完成！")

        # 输出统计信息
        print("\n" + "=" * 60)
        print("模拟统计")
        print("=" * 60)
        print(f"总时间步数: {len(adapter.time_history)}")
        print(f"节点数量: {len(adapter.nodes)}")
        print(f"管道数量: {len(adapter.links)}")
        print(f"泵站数量: {len(adapter.pumps)}")

        # 显示最终状态
        print("\n最终节点状态:")
        for node_id in list(adapter.nodes.keys())[:5]:  # 显示前5个
            state = adapter.get_node_state(node_id)
            print(f"  {node_id}: 水深={state.depth:.3f}m, 溢流={state.flooding:.3f}m^3/s")

        # 导出结果
        adapter.export_results("swmm_results.json")

        return adapter

    finally:
        # 清理
        if os.path.exists(model_file):
            os.remove(model_file)


def example_pid_control():
    """示例2：PID控制泵站"""
    print("\n" + "=" * 60)
    print("示例2：PID控制泵站")
    print("=" * 60)

    if not PYSWMM_AVAILABLE:
        print("错误: pyswmm未安装")
        return

    # 创建测试模型
    model_file = "test_swmm_control.inp"
    create_simple_swmm_model(model_file)

    try:
        # 创建适配器
        adapter = SWMMAdapter(model_file)

        # 添加PID控制器
        controller = SWMMPIDController(
            pump_id="PUMP1",
            target_node_id="TANK1",
            setpoint=5.0,  # 目标水位5m
            kp=0.5,
            ki=0.1,
            kd=0.05
        )

        adapter.add_controller("tank_controller", controller)

        print("\n开始带控制的模拟...")
        print("目标: 保持TANK1水位在5m")

        # 运行模拟
        step_count = 0

        def control_callback(adapter, current_time):
            """控制回调"""
            nonlocal step_count
            step_count += 1

            if step_count % 10 == 0:
                tank_state = adapter.get_node_state("TANK1")
                pump_state = adapter.get_pump_state("PUMP1")
                print(f"  时间: {current_time}, "
                      f"水位: {tank_state.depth:.2f}m, "
                      f"泵流量: {pump_state.flow:.3f}m^3/s")

        adapter.run_simulation(callback=control_callback)

        print("\n控制模拟完成！")

        # 分析控制性能
        tank_states = adapter.node_states["TANK1"]
        depths = np.array([s.depth for s in tank_states])

        print("\n" + "=" * 60)
        print("控制性能分析")
        print("=" * 60)
        print(f"目标水位: 5.0m")
        print(f"平均水位: {depths.mean():.3f}m")
        print(f"水位标准差: {depths.std():.3f}m")
        print(f"最大偏差: {abs(depths - 5.0).max():.3f}m")

        return adapter

    finally:
        if os.path.exists(model_file):
            os.remove(model_file)


def visualize_results(adapter: SWMMAdapter):
    """可视化模拟结果"""
    print("\n" + "=" * 60)
    print("可视化结果")
    print("=" * 60)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 时间数组（转换为小时）
    time_hours = np.array(adapter.time_history) / 3600.0

    # 1. 节点水位
    ax1 = axes[0, 0]
    for node_id in list(adapter.node_states.keys())[:3]:
        states = adapter.node_states[node_id]
        depths = [s.depth for s in states]
        ax1.plot(time_hours, depths, '-', linewidth=2, label=node_id)

    ax1.set_xlabel('Time (hours)', fontsize=10)
    ax1.set_ylabel('Water Depth (m)', fontsize=10)
    ax1.set_title('Node Water Depths', fontsize=12, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. 管道流量
    ax2 = axes[0, 1]
    for link_id in list(adapter.link_states.keys())[:3]:
        states = adapter.link_states[link_id]
        flows = [s.flow for s in states]
        ax2.plot(time_hours, flows, '-', linewidth=2, label=link_id)

    ax2.set_xlabel('Time (hours)', fontsize=10)
    ax2.set_ylabel('Flow (m^3/s)', fontsize=10)
    ax2.set_title('Link Flows', fontsize=12, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 3. 泵站运行
    ax3 = axes[1, 0]
    if adapter.pump_states:
        pump_id = list(adapter.pump_states.keys())[0]
        states = adapter.pump_states[pump_id]
        flows = [s.flow for s in states]
        statuses = [s.status for s in states]

        ax3_twin = ax3.twinx()

        line1 = ax3.plot(time_hours, flows, 'b-', linewidth=2, label='Flow')
        line2 = ax3_twin.plot(time_hours, statuses, 'r--', linewidth=2, label='Status')

        ax3.set_xlabel('Time (hours)', fontsize=10)
        ax3.set_ylabel('Flow (m^3/s)', fontsize=10, color='b')
        ax3_twin.set_ylabel('Status (0/1)', fontsize=10, color='r')
        ax3.set_title(f'Pump Operation: {pump_id}', fontsize=12, fontweight='bold')

        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax3.legend(lines, labels)
        ax3.grid(True, alpha=0.3)
    else:
        ax3.text(0.5, 0.5, 'No pumps in model', ha='center', va='center',
                transform=ax3.transAxes, fontsize=12)
        ax3.set_title('Pump Operation', fontsize=12, fontweight='bold')

    # 4. 系统总径流
    ax4 = axes[1, 1]
    if adapter.system_states:
        runoff = [s.runoff for s in adapter.system_states]
        rainfall = [s.rainfall for s in adapter.system_states]

        ax4_twin = ax4.twinx()

        line1 = ax4.plot(time_hours, runoff, 'b-', linewidth=2, label='Runoff')
        line2 = ax4_twin.plot(time_hours, rainfall, 'g-', linewidth=2, label='Rainfall')

        ax4.set_xlabel('Time (hours)', fontsize=10)
        ax4.set_ylabel('Runoff (m^3/s)', fontsize=10, color='b')
        ax4_twin.set_ylabel('Rainfall (mm)', fontsize=10, color='g')
        ax4.set_title('System Runoff and Rainfall', fontsize=12, fontweight='bold')

        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax4.legend(lines, labels)
        ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('swmm_results.png', dpi=300, bbox_inches='tight')
    print("可视化结果已保存到: swmm_results.png")


def main():
    """主函数"""
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║           SWMM城市雨洪系统集成案例                            ║
    ╚════════════════════════════════════════════════════════════════╝

    本案例展示HydroClaude与EPA SWMM的深度集成

    功能：
    1. SWMM模型创建和运行
    2. 实时状态监测
    3. PID控制器集成
    4. 结果可视化

    要求：
    - 安装pyswmm: pip install pyswmm
    """)

    if not PYSWMM_AVAILABLE:
        print("\n" + "=" * 60)
        print("错误: pyswmm未安装！")
        print("=" * 60)
        print("\n请先安装pyswmm:")
        print("  pip install pyswmm")
        print("\n或者使用conda:")
        print("  conda install -c conda-forge pyswmm")
        return

    # 运行示例
    try:
        # 示例1：基本模拟
        adapter1 = example_basic_simulation()

        # 示例2：PID控制
        adapter2 = example_pid_control()

        # 可视化（使用第二个示例的结果）
        if adapter2:
            visualize_results(adapter2)

        print("\n" + "=" * 60)
        print("所有示例运行完成！")
        print("=" * 60)

        print("\n集成说明:")
        print("- HydroClaude提供了完整的SWMM适配器")
        print("- 支持实时状态监测和控制")
        print("- 可以集成PID、MPC等先进控制算法")
        print("- 结果可以导出为JSON格式进行进一步分析")

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
