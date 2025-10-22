"""
示例18: 梯级水电站调度

演示梯级水库系统的联合优化调度:
1. 三级梯级水电站
2. 水流传递和时间延迟
3. 联合优化调度
4. 发电效益最大化
5. 防洪协调控制

作者: HydroClaude Team
日期: 2025-10-22
"""

import sys
sys.path.append('/home/user/HydroClaude')

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams

from physics.reservoir import Reservoir
from physics.reservoir_cascade import ReservoirCascade, CascadeTopology, CascadeFloodControl, CascadePowerOptimization

# 设置中文字体
rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
rcParams['axes.unicode_minus'] = False


def create_three_stage_cascade():
    """
    创建三级梯级水电站系统

    R1 (上游) -> R2 (中游) -> R3 (下游)
    """
    print("=" * 80)
    print("示例18: 三级梯级水电站调度")
    print("=" * 80)

    # 创建三个水库
    # 上游水库 - 大型调节水库
    reservoir_1 = Reservoir(
        reservoir_id="R1_upstream",
        total_capacity=10000e4,  # 1亿m³
        dead_storage=1000e4,     # 1000万m³
        min_level=200.0,
        normal_level=250.0,
        flood_limit_level=245.0,
        design_level=260.0,
        catchment_area=2000.0,
        ecological_flow=20.0,
        max_discharge=3000.0,
        has_turbine=True,
        turbine_capacity=200.0,  # 200 MW
        hydraulic_head=80.0,
        turbine_efficiency=0.90
    )

    # 中游水库 - 中型径流式水库
    reservoir_2 = Reservoir(
        reservoir_id="R2_middle",
        total_capacity=5000e4,   # 5000万m³
        dead_storage=500e4,
        min_level=150.0,
        normal_level=180.0,
        flood_limit_level=175.0,
        design_level=185.0,
        catchment_area=1000.0,
        ecological_flow=15.0,
        max_discharge=2500.0,
        has_turbine=True,
        turbine_capacity=150.0,  # 150 MW
        hydraulic_head=60.0,
        turbine_efficiency=0.88
    )

    # 下游水库 - 小型日调节水库
    reservoir_3 = Reservoir(
        reservoir_id="R3_downstream",
        total_capacity=2000e4,   # 2000万m³
        dead_storage=200e4,
        min_level=100.0,
        normal_level=120.0,
        flood_limit_level=118.0,
        design_level=125.0,
        catchment_area=500.0,
        ecological_flow=10.0,
        max_discharge=2000.0,
        has_turbine=True,
        turbine_capacity=100.0,  # 100 MW
        hydraulic_head=40.0,
        turbine_efficiency=0.85
    )

    # 定义梯级拓扑
    topology = CascadeTopology(
        reservoir_ids=["R1_upstream", "R2_middle", "R3_downstream"],
        connections={
            "R1_upstream": ["R2_middle"],
            "R2_middle": ["R3_downstream"]
        },
        travel_times={
            ("R1_upstream", "R2_middle"): 2.0,    # 传播时间2小时
            ("R2_middle", "R3_downstream"): 1.0   # 传播时间1小时
        },
        lateral_inflows={
            "R1_upstream": 50.0,    # 区间入流 50 m³/s
            "R2_middle": 30.0,      # 区间入流 30 m³/s
            "R3_downstream": 20.0   # 区间入流 20 m³/s
        }
    )

    # 创建梯级系统
    cascade = ReservoirCascade(
        cascade_id="three_stage_cascade",
        reservoirs=[reservoir_1, reservoir_2, reservoir_3],
        topology=topology
    )

    print("\n梯级系统参数:")
    print(f"  水库数量: {len(cascade.reservoirs)}")
    print(f"  总装机容量: {sum(r.turbine_capacity for r in cascade.reservoirs.values()):.0f} MW")
    print(f"  总库容: {sum(r.total_capacity for r in cascade.reservoirs.values())/1e4:.0f} 万m³")

    print("\n各水库参数:")
    for res_id, res in cascade.reservoirs.items():
        print(f"  {res_id}:")
        print(f"    装机: {res.turbine_capacity:.0f} MW")
        print(f"    库容: {res.total_capacity/1e4:.0f} 万m³")
        print(f"    水头: {res.hydraulic_head:.0f} m")

    print("\n拓扑连接:")
    for upstream, downstreams in topology.connections.items():
        for downstream in downstreams:
            travel_time = topology.travel_times.get((upstream, downstream), 0)
            print(f"  {upstream} -> {downstream} (传播时间: {travel_time:.1f}小时)")

    return cascade


def simulate_cascade_operation(cascade):
    """
    仿真梯级水电站运行
    """
    print("\n" + "=" * 80)
    print("梯级水电站仿真")
    print("=" * 80)

    # 仿真参数
    dt = 3600.0  # 1小时
    n_hours = 168  # 仿真7天

    time_hours = np.arange(n_hours)

    # 生成上游入流（模拟一个洪水过程）
    inflow_r1 = 800.0 + 1200 * np.exp(-0.5 * ((time_hours - 48) / 24) ** 2)

    # 区间入流已在拓扑中定义
    inflows = {
        "R1_upstream": inflow_r1
        # R2和R3的入流包括上游出流 + 区间入流
    }

    print(f"\n仿真设置:")
    print(f"  时间步长: {dt/3600:.1f} 小时")
    print(f"  仿真时长: {n_hours} 小时 ({n_hours/24:.1f} 天)")
    print(f"  R1入流范围: {np.min(inflow_r1):.0f} - {np.max(inflow_r1):.0f} m³/s")

    # 模拟时变电价（峰谷电价）
    electricity_prices = np.ones(n_hours)
    for i in range(n_hours):
        hour_of_day = i % 24
        if 8 <= hour_of_day < 12 or 18 <= hour_of_day < 22:
            # 高峰期
            electricity_prices[i] = 1.5
        elif 23 <= hour_of_day or hour_of_day < 7:
            # 低谷期
            electricity_prices[i] = 0.5

    # 结果存储
    results = {res_id: {
        'time': [],
        'storage': [],
        'level': [],
        'inflow': [],
        'outflow': [],
        'power': []
    } for res_id in cascade.reservoirs.keys()}

    results['cascade'] = {
        'time': [],
        'total_power': [],
        'total_storage': [],
        'electricity_price': []
    }

    print(f"\n开始仿真...")

    # 仿真循环
    for i in range(n_hours):
        # 简单控制策略：峰期多发电，谷期少发电
        hour_of_day = i % 24
        if 8 <= hour_of_day < 12 or 18 <= hour_of_day < 22:
            # 高峰期：最大发电
            turbine_discharges = {
                "R1_upstream": cascade.reservoirs["R1_upstream"]._get_max_turbine_flow() * 0.9,
                "R2_middle": cascade.reservoirs["R2_middle"]._get_max_turbine_flow() * 0.9,
                "R3_downstream": cascade.reservoirs["R3_downstream"]._get_max_turbine_flow() * 0.9
            }
        else:
            # 平峰/低谷期：减少发电
            turbine_discharges = {
                "R1_upstream": cascade.reservoirs["R1_upstream"]._get_max_turbine_flow() * 0.5,
                "R2_middle": cascade.reservoirs["R2_middle"]._get_max_turbine_flow() * 0.5,
                "R3_downstream": cascade.reservoirs["R3_downstream"]._get_max_turbine_flow() * 0.5
            }

        # 仿真梯级系统
        states = cascade.simulate_cascade(
            dt=dt,
            inflows=inflows,
            turbine_discharges=turbine_discharges,
            high_fidelity=True
        )

        # 记录结果
        total_power = 0
        total_storage = 0

        for res_id, state in states.items():
            results[res_id]['time'].append(i)
            results[res_id]['storage'].append(state.storage / 1e4)
            results[res_id]['level'].append(state.water_level)
            results[res_id]['inflow'].append(state.inflow)
            results[res_id]['outflow'].append(state.outflow)
            results[res_id]['power'].append(state.power_generation)

            total_power += state.power_generation
            total_storage += state.storage

        results['cascade']['time'].append(i)
        results['cascade']['total_power'].append(total_power)
        results['cascade']['total_storage'].append(total_storage / 1e4)
        results['cascade']['electricity_price'].append(electricity_prices[i])

    print(f"仿真完成!")

    # 统计结果
    print(f"\n仿真结果统计:")
    for res_id, res_results in results.items():
        if res_id == 'cascade':
            continue
        print(f"\n  {res_id}:")
        print(f"    最大入流: {np.max(res_results['inflow']):.0f} m³/s")
        print(f"    最大出流: {np.max(res_results['outflow']):.0f} m³/s")
        print(f"    水位变幅: {np.min(res_results['level']):.2f} - {np.max(res_results['level']):.2f} m")
        print(f"    平均发电: {np.mean(res_results['power']):.2f} MW")
        print(f"    总发电量: {np.sum(res_results['power']):.2f} MWh")

    print(f"\n  梯级总计:")
    print(f"    总发电量: {np.sum(results['cascade']['total_power']):.2f} MWh")
    print(f"    平均功率: {np.mean(results['cascade']['total_power']):.2f} MW")
    print(f"    最大功率: {np.max(results['cascade']['total_power']):.2f} MW")

    # 计算发电收益
    total_revenue = sum(
        results['cascade']['total_power'][i] * results['cascade']['electricity_price'][i]
        for i in range(n_hours)
    )
    print(f"    总发电收益: {total_revenue:.2f} 元 (假设电价单位为元/MWh)")

    return results


def visualize_cascade_results(results, cascade):
    """
    可视化梯级运行结果
    """
    print("\n生成可视化图表...")

    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(4, 2, hspace=0.3, wspace=0.3)

    # 颜色方案
    colors = {
        'R1_upstream': 'blue',
        'R2_middle': 'green',
        'R3_downstream': 'red'
    }

    # 子图1: 各水库水位
    ax1 = fig.add_subplot(gs[0, :])
    for res_id in cascade.topological_order:
        ax1.plot(results[res_id]['time'], results[res_id]['level'],
                color=colors[res_id], label=res_id, linewidth=2)
        # 添加防洪限制水位线
        res = cascade.reservoirs[res_id]
        ax1.axhline(res.flood_limit_level, color=colors[res_id],
                   linestyle='--', alpha=0.5)
    ax1.set_ylabel('水位 (m)', fontsize=12)
    ax1.set_title('梯级水库水位过程', fontsize=14, fontweight='bold')
    ax1.legend(loc='best', ncol=3)
    ax1.grid(True, alpha=0.3)

    # 子图2: 各水库流量
    ax2 = fig.add_subplot(gs[1, :])
    for res_id in cascade.topological_order:
        ax2.plot(results[res_id]['time'], results[res_id]['inflow'],
                color=colors[res_id], linestyle='--', label=f'{res_id} 入流', alpha=0.7)
        ax2.plot(results[res_id]['time'], results[res_id]['outflow'],
                color=colors[res_id], label=f'{res_id} 出流', linewidth=2)
    ax2.set_ylabel('流量 (m³/s)', fontsize=12)
    ax2.set_title('梯级水库流量过程', fontsize=14, fontweight='bold')
    ax2.legend(loc='best', ncol=3, fontsize=9)
    ax2.grid(True, alpha=0.3)

    # 子图3: 各水库发电
    ax3 = fig.add_subplot(gs[2, :])
    for res_id in cascade.topological_order:
        ax3.plot(results[res_id]['time'], results[res_id]['power'],
                color=colors[res_id], label=res_id, linewidth=2)
        # 添加装机容量线
        res = cascade.reservoirs[res_id]
        ax3.axhline(res.turbine_capacity, color=colors[res_id],
                   linestyle='--', alpha=0.5)
    ax3.set_ylabel('发电功率 (MW)', fontsize=12)
    ax3.set_title('梯级水库发电过程', fontsize=14, fontweight='bold')
    ax3.legend(loc='best', ncol=3)
    ax3.grid(True, alpha=0.3)

    # 子图4: 总发电功率和电价
    ax4 = fig.add_subplot(gs[3, 0])
    ax4_twin = ax4.twinx()
    line1 = ax4.plot(results['cascade']['time'], results['cascade']['total_power'],
                    'b-', label='总发电功率', linewidth=2)
    line2 = ax4_twin.plot(results['cascade']['time'], results['cascade']['electricity_price'],
                         'r--', label='电价', linewidth=1.5, alpha=0.7)
    ax4.set_xlabel('时间 (小时)', fontsize=12)
    ax4.set_ylabel('总发电功率 (MW)', fontsize=12, color='b')
    ax4_twin.set_ylabel('电价 (相对单位)', fontsize=12, color='r')
    ax4.set_title('总发电功率与电价', fontsize=14, fontweight='bold')
    ax4.tick_params(axis='y', labelcolor='b')
    ax4_twin.tick_params(axis='y', labelcolor='r')
    # 合并图例
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax4.legend(lines, labels, loc='upper right')
    ax4.grid(True, alpha=0.3)

    # 子图5: 库容分布
    ax5 = fig.add_subplot(gs[3, 1])
    for res_id in cascade.topological_order:
        ax5.plot(results[res_id]['time'], results[res_id]['storage'],
                color=colors[res_id], label=res_id, linewidth=2)
    ax5.set_xlabel('时间 (小时)', fontsize=12)
    ax5.set_ylabel('库容 (万m³)', fontsize=12)
    ax5.set_title('梯级水库库容过程', fontsize=14, fontweight='bold')
    ax5.legend(loc='best')
    ax5.grid(True, alpha=0.3)

    plt.savefig('/home/user/HydroClaude/examples/example_18_cascade_hydropower/cascade_simulation.png', dpi=150)
    print(f"图像已保存到: cascade_simulation.png")


def demo_flood_control(cascade):
    """
    演示防洪协调控制
    """
    print("\n" + "=" * 80)
    print("防洪协调控制演示")
    print("=" * 80)

    # 创建防洪控制器
    flood_controller = CascadeFloodControl(cascade)

    # 生成洪水预报
    forecast_horizon = 72  # 72小时预报
    forecast_inflows = {
        "R1_upstream": 1000 + 2000 * np.exp(-0.5 * ((np.arange(forecast_horizon) - 24) / 12) ** 2),
        "R2_middle": np.ones(forecast_horizon) * 50,  # 区间入流
        "R3_downstream": np.ones(forecast_horizon) * 30
    }

    print(f"\n洪水预报:")
    print(f"  预报时长: {forecast_horizon} 小时")
    print(f"  R1预报洪峰: {np.max(forecast_inflows['R1_upstream']):.0f} m³/s")

    # 计算防洪控制策略
    strategies = flood_controller.compute_flood_control_strategy(
        forecast_inflows=forecast_inflows,
        forecast_horizon=forecast_horizon
    )

    print(f"\n防洪控制策略:")
    for res_id, outflows in strategies.items():
        print(f"  {res_id}:")
        print(f"    最大出流: {np.max(outflows):.0f} m³/s")
        print(f"    平均出流: {np.mean(outflows):.0f} m³/s")

    # 可视化防洪策略
    fig, ax = plt.subplots(figsize=(12, 6))

    colors = {'R1_upstream': 'blue', 'R2_middle': 'green', 'R3_downstream': 'red'}

    for res_id in cascade.topological_order:
        ax.plot(range(forecast_horizon), forecast_inflows[res_id],
               color=colors[res_id], linestyle='--', label=f'{res_id} 预报入流', alpha=0.7)
        ax.plot(range(forecast_horizon), strategies[res_id],
               color=colors[res_id], label=f'{res_id} 控制出流', linewidth=2)

    ax.set_xlabel('时间 (小时)', fontsize=12)
    ax.set_ylabel('流量 (m³/s)', fontsize=12)
    ax.set_title('防洪协调控制策略', fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('/home/user/HydroClaude/examples/example_18_cascade_hydropower/flood_control.png', dpi=150)
    print(f"\n防洪控制图像已保存到: flood_control.png")


if __name__ == "__main__":
    # 创建梯级系统
    cascade = create_three_stage_cascade()

    # 仿真梯级运行
    results = simulate_cascade_operation(cascade)

    # 可视化结果
    visualize_cascade_results(results, cascade)

    # 演示防洪控制
    demo_flood_control(cascade)

    print("\n" + "=" * 80)
    print("示例18完成!")
    print("=" * 80)
