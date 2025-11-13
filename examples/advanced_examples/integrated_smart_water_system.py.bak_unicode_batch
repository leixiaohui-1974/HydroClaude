"""
智慧供水系统综合集成案例

本案例展示HydroClaude所有高级功能的协同工作，构建完整的智慧供水系统

系统组成：
1. 明渠输水 + 有压管网（水力模拟）
2. 余氯水质追踪（水质模拟）
3. 多目标优化调度（NSGA-II）
4. 实时SCADA监控（数据集成）
5. GIS空间可视化（GIS集成）

优化目标：
- 最小化能耗
- 保证水质（余氯≥0.05mg/L）
- 满足供水需求
- 平衡各用水区

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import sys
import os
import json

# 添加项目根目录
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from optimization.multi_objective import (
    MOProblem, Individual, NSGA2, NSGA2Config
)
from simulation.water_quality import (
    WaterQualitySimulator,
    ReactionConfig,
    ReactionType
)
from integration.realtime_data import (
    SCADAAdapter,
    SCADAPoint,
    TimeSeriesDatabase,
    SensorData
)
from integration.gis_adapter import (
    GISAdapter,
    create_water_network_geojson,
    GIS_AVAILABLE
)


class SmartWaterSystem:
    """
    智慧供水系统

    集成所有功能模块，构建完整的供水系统
    """

    def __init__(self):
        # 系统参数
        self.n_zones = 3  # 3个供水分区
        self.simulation_hours = 24

        # 水源参数
        self.source_elevation = 100.0  # m
        self.source_chlorine = 1.2  # mg/L

        # 管网参数
        self.pipe_lengths = [5000, 4000, 3000]  # m
        self.pipe_diameters = [0.6, 0.5, 0.4]  # m

        # 用水需求（m³/h）
        self.demands = self._generate_demands()

        # 泵站参数
        self.pump_capacity = 0.3  # m³/s
        self.pump_efficiency = 0.75
        self.pump_head = 50  # m

        # 创建子系统
        self.quality_simulators = self._create_quality_simulators()
        self.scada = self._create_scada_system()
        self.tsdb = TimeSeriesDatabase(db_name="smart_water")

        # 状态变量
        self.current_flows = np.zeros(3)  # 各区流量
        self.current_pressures = np.zeros(3)  # 各区压力
        self.current_chlorine = np.zeros(3)  # 各区余氯

    def _generate_demands(self):
        """生成24小时用水需求曲线"""
        time = np.arange(24)

        # 典型日用水曲线（峰谷变化）
        base_demands = np.array([50, 60, 70])  # m³/h

        demands = {}
        for i, base in enumerate(base_demands):
            # 添加日变化
            pattern = (0.6 + 0.4 * np.sin(2 * np.pi * (time - 6) / 24) +
                      0.2 * np.sin(4 * np.pi * time / 24))
            demands[f'Zone{i+1}'] = base * pattern

        return demands

    def _create_quality_simulators(self):
        """创建各区水质模拟器"""
        simulators = {}

        for i in range(self.n_zones):
            sim = WaterQualitySimulator(
                nx=30,
                length=self.pipe_lengths[i],
                diameter=self.pipe_diameters[i]
            )

            # 设置余氯衰减
            reaction = ReactionConfig(
                reaction_type=ReactionType.FIRST_ORDER,
                bulk_coefficient=-0.5,
                wall_coefficient=-0.1
            )
            sim.add_reaction("chlorine", reaction)
            sim.set_initial_concentration(self.source_chlorine)

            simulators[f'Zone{i+1}'] = sim

        return simulators

    def _create_scada_system(self):
        """创建SCADA监控系统"""
        scada = SCADAAdapter()

        # 为每个分区添加监测点
        for i in range(self.n_zones):
            zone_id = i + 1

            points = [
                SCADAPoint(
                    point_id=f'AI_FLOW_Z{zone_id}',
                    point_type='AI',
                    description=f'Zone{zone_id} Flow Rate',
                    unit='m³/s',
                    min_value=0,
                    max_value=0.2
                ),
                SCADAPoint(
                    point_id=f'AI_PRESSURE_Z{zone_id}',
                    point_type='AI',
                    description=f'Zone{zone_id} Pressure',
                    unit='m',
                    min_value=0,
                    max_value=100,
                    alarm_enabled=True,
                    alarm_high=80,
                    alarm_low=20
                ),
                SCADAPoint(
                    point_id=f'AI_CHLORINE_Z{zone_id}',
                    point_type='AI',
                    description=f'Zone{zone_id} Chlorine',
                    unit='mg/L',
                    min_value=0,
                    max_value=5,
                    alarm_enabled=True,
                    alarm_high=2.0,
                    alarm_low=0.05
                ),
            ]

            for point in points:
                scada.add_point(point)

        scada.connect("192.168.1.100", 502)

        return scada

    def create_optimization_problem(self):
        """创建多目标优化问题"""

        def objective_function(x):
            """
            优化目标函数

            决策变量 x: [q1, q2, q3, pump_speed]
            - q1, q2, q3: 各区流量 (m³/s)
            - pump_speed: 泵站转速比 (0.5-1.0)
            """
            q1, q2, q3, pump_speed = x

            # 目标1：最小化能耗
            total_flow = q1 + q2 + q3
            pump_power = (9.81 * total_flow * self.pump_head * pump_speed /
                         self.pump_efficiency)  # kW
            energy_cost = pump_power * 0.8  # 假设电价0.8元/kWh

            # 目标2：最小化余氯不足
            # 模拟余氯衰减
            chlorine_deficit = 0.0
            for i, q in enumerate([q1, q2, q3]):
                if q > 0:
                    # 简化余氯模型
                    residence_time = self.pipe_lengths[i] / (q / (np.pi * (self.pipe_diameters[i]/2)**2))
                    decay_rate = 0.5 / 86400  # 1/s
                    outlet_chlorine = self.source_chlorine * np.exp(-decay_rate * residence_time)

                    if outlet_chlorine < 0.05:
                        chlorine_deficit += (0.05 - outlet_chlorine) * 1000  # 放大惩罚

            # 目标3：最小化供需不平衡
            demands_m3s = np.array([d[12] / 3600 for d in self.demands.values()])  # 中午时段需求
            supply_deficit = np.sum(np.abs(demands_m3s - np.array([q1, q2, q3])))

            return np.array([energy_cost, chlorine_deficit, supply_deficit])

        def constraint_function(x):
            """约束函数"""
            q1, q2, q3, pump_speed = x

            constraints = []

            # 约束1：总流量不超过泵站容量
            total_flow = q1 + q2 + q3
            constraints.append(total_flow - self.pump_capacity * pump_speed)

            # 约束2：各区流量非负
            constraints.extend([-q1, -q2, -q3])

            # 约束3：泵站转速范围
            constraints.extend([0.5 - pump_speed, pump_speed - 1.0])

            return np.array(constraints)

        # 定义边界
        bounds = [
            (0.01, 0.15),  # q1
            (0.01, 0.12),  # q2
            (0.01, 0.10),  # q3
            (0.5, 1.0),    # pump_speed
        ]

        problem = MOProblem(
            n_objectives=3,
            n_variables=4,
            bounds=bounds,
            objective_function=objective_function,
            constraint_function=constraint_function
        )

        return problem

    def optimize_operation(self):
        """优化运行策略"""
        print("=" * 60)
        print("多目标优化调度")
        print("=" * 60)

        problem = self.create_optimization_problem()

        config = NSGA2Config(
            population_size=50,
            n_generations=100,
            seed=42
        )

        print("\n优化参数:")
        print(f"  种群大小: {config.population_size}")
        print(f"  迭代代数: {config.n_generations}")
        print(f"  决策变量: 4个 (3个区流量 + 泵速)")
        print(f"  优化目标: 3个 (能耗 + 水质 + 供需平衡)")

        print("\n开始优化...")

        optimizer = NSGA2(problem, config)
        result = optimizer.optimize()

        print(f"\n优化完成！")
        print(f"  Pareto前沿解数: {len(result.pareto_front)}")

        # 选择均衡解（归一化后距离原点最近）
        objectives = result.get_pareto_objectives()
        obj_norm = (objectives - objectives.min(axis=0)) / (objectives.max(axis=0) - objectives.min(axis=0) + 1e-10)
        distances = np.sqrt(np.sum(obj_norm**2, axis=1))
        best_idx = np.argmin(distances)

        best_solution = result.pareto_front[best_idx]
        best_vars = best_solution.decision_variables
        best_objs = best_solution.objectives

        print(f"\n最优方案:")
        print(f"  Zone1流量: {best_vars[0]:.3f} m³/s")
        print(f"  Zone2流量: {best_vars[1]:.3f} m³/s")
        print(f"  Zone3流量: {best_vars[2]:.3f} m³/s")
        print(f"  泵站转速: {best_vars[3]:.2f}")
        print(f"\n目标值:")
        print(f"  能耗成本: {best_objs[0]:.2f} 元/h")
        print(f"  余氯不足: {best_objs[1]:.4f}")
        print(f"  供需偏差: {best_objs[2]:.4f} m³/s")

        return best_vars, result

    def simulate_24hours(self, optimal_flows):
        """模拟24小时运行"""
        print("\n" + "=" * 60)
        print("24小时系统模拟")
        print("=" * 60)

        q1, q2, q3, pump_speed = optimal_flows

        print(f"\n运行参数:")
        print(f"  流量分配: [{q1:.3f}, {q2:.3f}, {q3:.3f}] m³/s")
        print(f"  泵站转速: {pump_speed:.2f}")

        # 模拟历史
        history = {
            'time': [],
            'flows': {f'Zone{i+1}': [] for i in range(3)},
            'pressures': {f'Zone{i+1}': [] for i in range(3)},
            'chlorine': {f'Zone{i+1}': [] for i in range(3)},
            'energy': []
        }

        print("\n开始模拟...")

        for hour in range(self.simulation_hours):
            # 更新流速
            for i, q in enumerate([q1, q2, q3]):
                zone = f'Zone{i+1}'
                area = np.pi * (self.pipe_diameters[i] / 2) ** 2
                velocity = q / area
                self.quality_simulators[zone].set_velocity(velocity)

                # 水质模拟
                self.quality_simulators[zone].step(dt=3600, inflow_concentration=self.source_chlorine)

                # 获取出口余氯
                outlet_chlorine = self.quality_simulators[zone].get_outlet_concentration()

                # 计算压力（简化）
                pressure = self.source_elevation + self.pump_head * pump_speed - \
                          (self.pipe_lengths[i] / 1000) * (velocity ** 2) / (2 * 9.81)

                # 更新SCADA
                self.scada.write_point(f'AI_FLOW_Z{i+1}', q)
                self.scada.write_point(f'AI_PRESSURE_Z{i+1}', pressure)
                self.scada.write_point(f'AI_CHLORINE_Z{i+1}', outlet_chlorine)

                # 写入时序数据库
                current_time = datetime.now() + timedelta(hours=hour)
                self.tsdb.write(SensorData(f'FLOW_Z{i+1}', current_time, q, 'm³/s'))
                self.tsdb.write(SensorData(f'PRESSURE_Z{i+1}', current_time, pressure, 'm'))
                self.tsdb.write(SensorData(f'CHLORINE_Z{i+1}', current_time, outlet_chlorine, 'mg/L'))

                # 记录历史
                history['flows'][zone].append(q)
                history['pressures'][zone].append(pressure)
                history['chlorine'][zone].append(outlet_chlorine)

            # 能耗计算
            total_flow = q1 + q2 + q3
            power = 9.81 * total_flow * self.pump_head * pump_speed / self.pump_efficiency / 1000  # kW
            history['energy'].append(power)

            history['time'].append(hour)

            if (hour + 1) % 6 == 0:
                print(f"  模拟进度: {hour+1}/{self.simulation_hours} 小时")

        print("\n模拟完成！")

        return history

    def generate_gis_visualization(self, optimal_flows):
        """生成GIS可视化"""
        print("\n" + "=" * 60)
        print("GIS空间可视化")
        print("=" * 60)

        if not GIS_AVAILABLE:
            print("\n警告: GIS库未安装，跳过可视化")
            return

        # 定义节点（经纬度坐标）
        nodes = [
            {'id': 'SOURCE', 'x': 120.0, 'y': 30.0, 'type': 'source'},
            {'id': 'Z1', 'x': 120.05, 'y': 30.02, 'type': 'zone', 'flow': optimal_flows[0]},
            {'id': 'Z2', 'x': 120.03, 'y': 29.98, 'type': 'zone', 'flow': optimal_flows[1]},
            {'id': 'Z3', 'x': 120.06, 'y': 29.97, 'type': 'zone', 'flow': optimal_flows[2]},
        ]

        # 定义管道
        links = [
            {'id': 'P1', 'from': 'SOURCE', 'to': 'Z1', 'diameter': self.pipe_diameters[0]},
            {'id': 'P2', 'from': 'SOURCE', 'to': 'Z2', 'diameter': self.pipe_diameters[1]},
            {'id': 'P3', 'from': 'SOURCE', 'to': 'Z3', 'diameter': self.pipe_diameters[2]},
        ]

        # 创建GeoJSON
        create_water_network_geojson(nodes, links, 'smart_water_system.geojson')

        print("\nGIS数据已生成:")
        print("  - smart_water_system_nodes.geojson")
        print("  - smart_water_system_links.geojson")


def visualize_integrated_results(history, optimization_result):
    """可视化综合结果"""
    print("\n" + "=" * 60)
    print("生成综合分析图表")
    print("=" * 60)

    fig = plt.figure(figsize=(16, 12))

    # 1. 各区流量
    ax1 = plt.subplot(3, 3, 1)
    for zone in ['Zone1', 'Zone2', 'Zone3']:
        ax1.plot(history['time'], history['flows'][zone], '-', linewidth=2, label=zone)
    ax1.set_xlabel('Time (hours)')
    ax1.set_ylabel('Flow (m³/s)')
    ax1.set_title('Zone Flow Rates', fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. 各区压力
    ax2 = plt.subplot(3, 3, 2)
    for zone in ['Zone1', 'Zone2', 'Zone3']:
        ax2.plot(history['time'], history['pressures'][zone], '-', linewidth=2, label=zone)
    ax2.axhline(y=20, color='r', linestyle='--', linewidth=1, label='Min')
    ax2.set_xlabel('Time (hours)')
    ax2.set_ylabel('Pressure (m)')
    ax2.set_title('Zone Pressures', fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 3. 各区余氯
    ax3 = plt.subplot(3, 3, 3)
    for zone in ['Zone1', 'Zone2', 'Zone3']:
        ax3.plot(history['time'], history['chlorine'][zone], '-', linewidth=2, label=zone)
    ax3.axhline(y=0.05, color='r', linestyle='--', linewidth=1, label='Min Standard')
    ax3.set_xlabel('Time (hours)')
    ax3.set_ylabel('Chlorine (mg/L)')
    ax3.set_title('Zone Chlorine Concentrations', fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # 4. 能耗曲线
    ax4 = plt.subplot(3, 3, 4)
    ax4.plot(history['time'], history['energy'], 'b-', linewidth=2)
    ax4.fill_between(history['time'], 0, history['energy'], alpha=0.3)
    ax4.set_xlabel('Time (hours)')
    ax4.set_ylabel('Power (kW)')
    ax4.set_title('Energy Consumption', fontweight='bold')
    ax4.grid(True, alpha=0.3)

    # 5. Pareto前沿（3D）
    ax5 = plt.subplot(3, 3, 5, projection='3d')
    objectives = optimization_result.get_pareto_objectives()
    ax5.scatter(objectives[:, 0], objectives[:, 1], objectives[:, 2],
               c='b', marker='o', s=30, alpha=0.6)
    ax5.set_xlabel('Energy Cost')
    ax5.set_ylabel('Chlorine Deficit')
    ax5.set_zlabel('Supply Deficit')
    ax5.set_title('Pareto Front (3 Objectives)', fontweight='bold')

    # 6. 水质合格率
    ax6 = plt.subplot(3, 3, 6)
    compliance_rates = []
    for zone in ['Zone1', 'Zone2', 'Zone3']:
        chlorine_data = np.array(history['chlorine'][zone])
        compliance = (chlorine_data >= 0.05).sum() / len(chlorine_data) * 100
        compliance_rates.append(compliance)

    ax6.bar(['Zone1', 'Zone2', 'Zone3'], compliance_rates, color=['b', 'g', 'r'], alpha=0.7)
    ax6.axhline(y=100, color='green', linestyle='--', linewidth=1)
    ax6.set_ylabel('Compliance Rate (%)')
    ax6.set_title('Water Quality Compliance', fontweight='bold')
    ax6.grid(True, alpha=0.3, axis='y')
    ax6.set_ylim([90, 102])

    # 7-9. 各区详细分析
    for i, zone in enumerate(['Zone1', 'Zone2', 'Zone3']):
        ax = plt.subplot(3, 3, 7+i)

        # 双轴
        ax_twin = ax.twinx()

        line1 = ax.plot(history['time'], history['pressures'][zone],
                       'b-', linewidth=2, label='Pressure')
        line2 = ax_twin.plot(history['time'], history['chlorine'][zone],
                           'r-', linewidth=2, label='Chlorine')

        ax.set_xlabel('Time (hours)')
        ax.set_ylabel('Pressure (m)', color='b')
        ax_twin.set_ylabel('Chlorine (mg/L)', color='r')
        ax.set_title(f'{zone} Detail', fontweight='bold')

        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax.legend(lines, labels, loc='upper right')
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('integrated_smart_water_system.png', dpi=300, bbox_inches='tight')
    print("\n综合分析图表已保存: integrated_smart_water_system.png")


def main():
    """主函数"""
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║           智慧供水系统综合集成案例                            ║
    ╚════════════════════════════════════════════════════════════════╝

    本案例展示HydroClaude所有高级功能的协同工作

    集成模块：
    1. 多目标优化（NSGA-II）- 调度策略优化
    2. 水质模拟 - 余氯追踪
    3. SCADA监控 - 实时数据采集
    4. 时序数据库 - 历史数据存储
    5. GIS可视化 - 空间分布展示

    优化目标：
    - 最小化能耗成本
    - 保证水质达标（余氯≥0.05mg/L）
    - 满足各区供水需求

    系统特点：
    - 3个供水分区
    - 24小时连续模拟
    - 实时监控与优化
    """)

    # 创建智慧供水系统
    system = SmartWaterSystem()

    # 1. 多目标优化
    optimal_flows, opt_result = system.optimize_operation()

    # 2. 24小时模拟
    history = system.simulate_24hours(optimal_flows)

    # 3. GIS可视化
    system.generate_gis_visualization(optimal_flows)

    # 4. 综合分析
    visualize_integrated_results(history, opt_result)

    # 5. 系统统计
    print("\n" + "=" * 60)
    print("系统运行统计")
    print("=" * 60)

    for zone in ['Zone1', 'Zone2', 'Zone3']:
        chlorine_data = np.array(history['chlorine'][zone])
        pressure_data = np.array(history['pressures'][zone])

        print(f"\n{zone}:")
        print(f"  平均流量: {np.mean(history['flows'][zone]):.3f} m³/s")
        print(f"  平均压力: {np.mean(pressure_data):.1f} m")
        print(f"  平均余氯: {np.mean(chlorine_data):.3f} mg/L")
        print(f"  水质合格率: {(chlorine_data >= 0.05).sum() / len(chlorine_data) * 100:.1f}%")

    total_energy = np.sum(history['energy'])
    print(f"\n总能耗: {total_energy:.2f} kWh/day")
    print(f"平均功率: {np.mean(history['energy']):.2f} kW")

    print("\n" + "=" * 60)
    print("案例运行完成！")
    print("=" * 60)

    print("\n集成价值:")
    print("- 多模块协同工作")
    print("- 优化驱动运行")
    print("- 实时监控反馈")
    print("- 数据闭环管理")

    print("\n应用前景:")
    print("- 智慧水务平台")
    print("- 数字孪生系统")
    print("- AI辅助决策")
    print("- 自动化运营")


if __name__ == "__main__":
    main()
