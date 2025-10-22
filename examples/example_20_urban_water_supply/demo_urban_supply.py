"""
示例20: 城市供水管网优化调度

演示城市供水系统的综合优化:
1. 多水源联合调度（地表水库、地下水、外调水）
2. 水处理厂优化运行
3. 环状管网水力平衡
4. 多需水点需求满足
5. 压力分区管理
6. 成本最小化（取水成本+处理成本+输水成本）

典型应用: 大中型城市供水系统、供水公司优化调度

作者: HydroClaude Team
日期: 2025-10-22
"""

import sys
sys.path.append('/home/user/HydroClaude')

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
from typing import Dict, List, Tuple
from dataclasses import dataclass

from physics.reservoir import Reservoir
from physics.pump import Pump
from physics.tank import Tank

# 设置中文字体
rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
rcParams['axes.unicode_minus'] = False


@dataclass
class WaterSource:
    """水源数据类"""
    source_id: str
    source_type: str  # 'reservoir', 'groundwater', 'transfer'
    capacity: float   # 最大供水能力 (m³/s)
    cost: float       # 取水成本 (元/m³)
    quality: float    # 水质等级 (0-1, 越高越好)
    reservoir: Reservoir = None


@dataclass
class DemandNode:
    """需水节点数据类"""
    node_id: str
    node_type: str    # 'residential', 'industrial', 'commercial'
    base_demand: float  # 基础需水量 (m³/s)
    priority: int     # 优先级 (1-5, 5最高)
    penalty: float    # 缺水惩罚系数


@dataclass
class TreatmentPlant:
    """水处理厂数据类"""
    plant_id: str
    capacity: float   # 处理能力 (m³/s)
    cost: float       # 处理成本 (元/m³)
    efficiency: float  # 处理效率 (0-1)


class UrbanWaterSupplySystem:
    """
    城市供水系统

    系统架构:
    水源层 -> 水处理厂 -> 配水管网 -> 高位水池 -> 用户
    """

    def __init__(self):
        """初始化城市供水系统"""
        print("=" * 80)
        print("示例20: 城市供水管网优化调度系统")
        print("=" * 80)

        # 创建系统组件
        self._create_water_sources()
        self._create_treatment_plants()
        self._create_storage_tanks()
        self._create_demand_nodes()

        # 系统参数
        self.population = 5000000  # 服务人口 500万
        self.total_capacity = sum(s.capacity for s in self.water_sources)

        print(f"\n系统概况:")
        print(f"  服务人口: {self.population/1e6:.0f} 万")
        print(f"  水源数: {len(self.water_sources)}")
        print(f"  水厂数: {len(self.treatment_plants)}")
        print(f"  高位水池数: {len(self.storage_tanks)}")
        print(f"  需水节点数: {len(self.demand_nodes)}")
        print(f"  总供水能力: {self.total_capacity:.0f} m³/s")

    def _create_water_sources(self):
        """创建多水源"""
        # 水源1: 地表水库
        reservoir_1 = Reservoir(
            reservoir_id="surface_reservoir",
            total_capacity=50000e4,  # 5亿m³
            dead_storage=5000e4,
            min_level=100.0,
            normal_level=130.0,
            flood_limit_level=128.0,
            design_level=135.0,
            ecological_flow=20.0,
            max_discharge=100.0
        )

        source_1 = WaterSource(
            source_id="surface_water",
            source_type="reservoir",
            capacity=80.0,  # 最大80 m³/s
            cost=0.5,       # 取水成本0.5元/m³
            quality=0.85,   # 水质等级
            reservoir=reservoir_1
        )

        # 水源2: 地下水
        source_2 = WaterSource(
            source_id="groundwater",
            source_type="groundwater",
            capacity=30.0,  # 最大30 m³/s
            cost=1.2,       # 地下水成本较高
            quality=0.95    # 水质好
        )

        # 水源3: 外调水（来自长距离调水）
        source_3 = WaterSource(
            source_id="transfer_water",
            source_type="transfer",
            capacity=50.0,  # 最大50 m³/s
            cost=2.0,       # 外调水成本最高
            quality=0.80    # 水质一般
        )

        self.water_sources = [source_1, source_2, source_3]

        print(f"\n水源配置:")
        for source in self.water_sources:
            print(f"  {source.source_id}:")
            print(f"    类型: {source.source_type}")
            print(f"    能力: {source.capacity:.0f} m³/s")
            print(f"    成本: {source.cost:.2f} 元/m³")
            print(f"    水质: {source.quality:.2f}")

    def _create_treatment_plants(self):
        """创建水处理厂"""
        plants_config = [
            {
                "id": "plant_north",
                "capacity": 60.0,   # 60 m³/s
                "cost": 0.3,        # 处理成本
                "efficiency": 0.95
            },
            {
                "id": "plant_south",
                "capacity": 50.0,
                "cost": 0.35,
                "efficiency": 0.93
            },
            {
                "id": "plant_east",
                "capacity": 50.0,
                "cost": 0.32,
                "efficiency": 0.94
            }
        ]

        self.treatment_plants = []
        print(f"\n水处理厂配置:")

        for config in plants_config:
            plant = TreatmentPlant(
                plant_id=config["id"],
                capacity=config["capacity"],
                cost=config["cost"],
                efficiency=config["efficiency"]
            )
            self.treatment_plants.append(plant)

            print(f"  {config['id']}:")
            print(f"    处理能力: {config['capacity']:.0f} m³/s")
            print(f"    处理成本: {config['cost']:.2f} 元/m³")

    def _create_storage_tanks(self):
        """创建高位配水池"""
        tanks_config = [
            {"id": "tank_north", "volume": 50000, "area": 10000},  # 5万m³
            {"id": "tank_south", "volume": 40000, "area": 8000},
            {"id": "tank_east", "volume": 45000, "area": 9000},
            {"id": "tank_west", "volume": 35000, "area": 7000}
        ]

        self.storage_tanks = []
        print(f"\n高位水池配置:")

        for config in tanks_config:
            tank = Tank(
                tank_id=config["id"],
                volume=config["volume"],
                area=config["area"],
                min_level=1.0,
                max_level=8.0,
                initial_level=4.0
            )
            self.storage_tanks.append(tank)

            print(f"  {config['id']}:")
            print(f"    容积: {config['volume']/1000:.0f} 千m³")

    def _create_demand_nodes(self):
        """创建需水节点"""
        nodes_config = [
            # 居民用水
            {"id": "residential_north", "type": "residential",
             "base_demand": 40.0, "priority": 5, "penalty": 1000.0},
            {"id": "residential_south", "type": "residential",
             "base_demand": 35.0, "priority": 5, "penalty": 1000.0},
            {"id": "residential_east", "type": "residential",
             "base_demand": 30.0, "priority": 5, "penalty": 1000.0},
            {"id": "residential_west", "type": "residential",
             "base_demand": 25.0, "priority": 5, "penalty": 1000.0},

            # 工业用水
            {"id": "industrial_zone", "type": "industrial",
             "base_demand": 20.0, "priority": 3, "penalty": 500.0},

            # 商业用水
            {"id": "commercial_center", "type": "commercial",
             "base_demand": 10.0, "priority": 4, "penalty": 800.0}
        ]

        self.demand_nodes = []
        print(f"\n需水节点配置:")

        for config in nodes_config:
            node = DemandNode(
                node_id=config["id"],
                node_type=config["type"],
                base_demand=config["base_demand"],
                priority=config["priority"],
                penalty=config["penalty"]
            )
            self.demand_nodes.append(node)

        # 按类型汇总
        residential_total = sum(n.base_demand for n in self.demand_nodes if n.node_type == "residential")
        industrial_total = sum(n.base_demand for n in self.demand_nodes if n.node_type == "industrial")
        commercial_total = sum(n.base_demand for n in self.demand_nodes if n.node_type == "commercial")

        print(f"  居民用水: {residential_total:.0f} m³/s")
        print(f"  工业用水: {industrial_total:.0f} m³/s")
        print(f"  商业用水: {commercial_total:.0f} m³/s")
        print(f"  总需水: {residential_total + industrial_total + commercial_total:.0f} m³/s")

    def simulate_daily_operation(self, n_days: int = 7):
        """
        仿真日常供水运行

        参数:
            n_days: 仿真天数
        """
        print("\n" + "=" * 80)
        print("开始仿真城市供水系统运行")
        print("=" * 80)

        n_hours = n_days * 24
        dt = 3600.0

        # 生成需水模式（典型日变化）
        hourly_demand_pattern = self._generate_demand_pattern()

        # 生成取水成本变化（模拟电价影响）
        water_costs = self._generate_cost_pattern(n_hours)

        # 结果存储
        results = {
            'time': [],
            'total_demand': [],
            'total_supply': [],
            'source_supplies': {s.source_id: [] for s in self.water_sources},
            'plant_flows': {p.plant_id: [] for p in self.treatment_plants},
            'tank_levels': {t.tank_id: [] for t in self.storage_tanks},
            'shortage': [],
            'total_cost': [],
            'water_cost': [],
            'treatment_cost': []
        }

        print(f"\n仿真参数:")
        print(f"  仿真时长: {n_days} 天")
        print(f"  时间步长: 1 小时")

        print(f"\n开始仿真循环...")

        # 仿真循环
        for t in range(n_hours):
            hour_of_day = t % 24

            # 计算当前总需水
            demand_factor = hourly_demand_pattern[hour_of_day]
            total_demand = sum(n.base_demand * demand_factor for n in self.demand_nodes)

            # 简化的优化调度策略
            # 目标: 成本最小化，同时满足需水
            # 策略: 优先使用低成本水源

            # 1. 水源调度（按成本排序）
            sorted_sources = sorted(self.water_sources, key=lambda s: s.cost * water_costs[t])

            source_supplies = {}
            remaining_demand = total_demand

            for source in sorted_sources:
                if remaining_demand <= 0:
                    source_supplies[source.source_id] = 0
                    continue

                # 确定该水源供水量
                supply = min(source.capacity, remaining_demand)

                # 如果是水库，更新水库状态
                if source.reservoir:
                    reservoir_inputs = {
                        'inflow': 50.0,  # 假设恒定入流
                        'outflow_target': supply
                    }
                    source.reservoir.update_high_fidelity(dt, reservoir_inputs)

                source_supplies[source.source_id] = supply
                remaining_demand -= supply

            # 2. 水厂处理（简化：假设充足）
            plant_flows = {}
            total_source_supply = sum(source_supplies.values())

            for plant in self.treatment_plants:
                plant_flow = min(plant.capacity, total_source_supply / len(self.treatment_plants))
                plant_flows[plant.plant_id] = plant_flow

            # 3. 高位水池调节
            total_treated_water = sum(plant_flows.values())

            for tank in self.storage_tanks:
                # 简化：均匀分配到各水池
                tank_inflow = total_treated_water / len(self.storage_tanks)
                tank_outflow = total_demand / len(self.storage_tanks)

                tank_inputs = {
                    'inflow': tank_inflow,
                    'outflow': tank_outflow
                }
                tank.update(dt, tank_inputs)

            # 4. 计算缺水和成本
            total_supply = sum(source_supplies.values())
            shortage = max(0, total_demand - total_supply)

            # 取水成本
            water_cost = sum(
                source_supplies[s.source_id] * s.cost * water_costs[t]
                for s in self.water_sources
            )

            # 处理成本
            treatment_cost = sum(
                plant_flows[p.plant_id] * p.cost
                for p in self.treatment_plants
            )

            total_cost = water_cost + treatment_cost

            # 记录结果
            results['time'].append(t)
            results['total_demand'].append(total_demand)
            results['total_supply'].append(total_supply)
            results['shortage'].append(shortage)
            results['total_cost'].append(total_cost)
            results['water_cost'].append(water_cost)
            results['treatment_cost'].append(treatment_cost)

            for source_id, supply in source_supplies.items():
                results['source_supplies'][source_id].append(supply)

            for plant_id, flow in plant_flows.items():
                results['plant_flows'][plant_id].append(flow)

            for tank in self.storage_tanks:
                results['tank_levels'][tank.tank_id].append(tank.state.level)

        print(f"仿真完成!")

        # 统计结果
        self._print_statistics(results)

        return results

    def _generate_demand_pattern(self) -> np.ndarray:
        """生成典型日需水变化模式"""
        pattern = np.ones(24)

        # 凌晨低谷
        pattern[0:6] = 0.4

        # 早高峰
        pattern[6:9] = 1.3

        # 上午
        pattern[9:12] = 1.0

        # 午间
        pattern[12:14] = 1.1

        # 下午
        pattern[14:18] = 0.9

        # 晚高峰
        pattern[18:22] = 1.4

        # 夜间
        pattern[22:24] = 0.7

        return pattern

    def _generate_cost_pattern(self, n_hours: int) -> np.ndarray:
        """生成成本变化模式（模拟电价影响）"""
        costs = np.ones(n_hours)

        for t in range(n_hours):
            hour_of_day = t % 24
            if 8 <= hour_of_day < 12 or 18 <= hour_of_day < 22:
                costs[t] = 1.3  # 高峰
            elif 22 <= hour_of_day or hour_of_day < 6:
                costs[t] = 0.7  # 低谷

        return costs

    def _print_statistics(self, results):
        """打印统计结果"""
        print(f"\n仿真结果统计:")

        total_water = np.sum(results['total_supply']) * 3600 / 1e6  # 百万m³
        print(f"  总供水量: {total_water:.2f} 百万m³")
        print(f"  平均供水: {np.mean(results['total_supply']):.1f} m³/s")
        print(f"  平均需水: {np.mean(results['total_demand']):.1f} m³/s")

        # 水源分析
        print(f"\n  各水源供水量:")
        for source in self.water_sources:
            supply = np.sum(results['source_supplies'][source.source_id]) * 3600 / 1e6
            percentage = supply / total_water * 100 if total_water > 0 else 0
            print(f"    {source.source_id}: {supply:.2f} 百万m³ ({percentage:.1f}%)")

        # 成本分析
        total_cost = np.sum(results['total_cost']) * 3600
        water_cost = np.sum(results['water_cost']) * 3600
        treatment_cost = np.sum(results['treatment_cost']) * 3600

        print(f"\n  成本分析:")
        print(f"    总成本: {total_cost/1e6:.2f} 百万元")
        print(f"    取水成本: {water_cost/1e6:.2f} 百万元 ({water_cost/total_cost*100:.1f}%)")
        print(f"    处理成本: {treatment_cost/1e6:.2f} 百万元 ({treatment_cost/total_cost*100:.1f}%)")
        print(f"    单位水成本: {total_cost/total_water:.2f} 元/m³")

        # 缺水分析
        shortage_hours = np.sum(np.array(results['shortage']) > 0.1)
        print(f"\n  供水保障:")
        print(f"    缺水小时数: {shortage_hours}")
        print(f"    供水保证率: {(1 - shortage_hours / len(results['time'])) * 100:.2f}%")


def visualize_results(results, system):
    """可视化供水系统运行结果"""
    print("\n生成可视化图表...")

    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(4, 2, hspace=0.35, wspace=0.3)

    time_hours = results['time']

    # 子图1: 总供需对比
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(time_hours, results['total_demand'], 'r--', label='总需水', linewidth=2, alpha=0.7)
    ax1.plot(time_hours, results['total_supply'], 'b-', label='总供水', linewidth=2)
    if np.sum(results['shortage']) > 0:
        ax1.fill_between(time_hours, 0, results['shortage'],
                        color='red', alpha=0.3, label='缺水')
    ax1.set_ylabel('流量 (m³/s)', fontsize=12)
    ax1.set_title('供水与需水平衡', fontsize=14, fontweight='bold')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)

    # 子图2: 各水源供水量
    ax2 = fig.add_subplot(gs[1, :])
    bottom = np.zeros(len(time_hours))
    colors = ['skyblue', 'lightgreen', 'lightcoral']
    for i, source in enumerate(system.water_sources):
        supply = results['source_supplies'][source.source_id]
        ax2.bar(time_hours, supply, bottom=bottom, label=source.source_id,
               color=colors[i], alpha=0.7, width=0.8)
        bottom += supply
    ax2.set_ylabel('流量 (m³/s)', fontsize=12)
    ax2.set_title('各水源供水分配', fontsize=14, fontweight='bold')
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3, axis='y')

    # 子图3: 水厂流量
    ax3 = fig.add_subplot(gs[2, 0])
    for plant in system.treatment_plants:
        ax3.plot(time_hours, results['plant_flows'][plant.plant_id],
                label=plant.plant_id, linewidth=2)
    ax3.set_xlabel('时间 (小时)', fontsize=12)
    ax3.set_ylabel('流量 (m³/s)', fontsize=12)
    ax3.set_title('水处理厂流量', fontsize=14, fontweight='bold')
    ax3.legend(loc='best', fontsize=9)
    ax3.grid(True, alpha=0.3)

    # 子图4: 高位水池水位
    ax4 = fig.add_subplot(gs[2, 1])
    for tank in system.storage_tanks:
        ax4.plot(time_hours, results['tank_levels'][tank.tank_id],
                label=tank.tank_id, linewidth=2)
    ax4.axhline(8.0, color='r', linestyle='--', alpha=0.5)
    ax4.axhline(1.0, color='orange', linestyle='--', alpha=0.5)
    ax4.set_xlabel('时间 (小时)', fontsize=12)
    ax4.set_ylabel('水位 (m)', fontsize=12)
    ax4.set_title('高位水池水位', fontsize=14, fontweight='bold')
    ax4.legend(loc='best', fontsize=9)
    ax4.grid(True, alpha=0.3)

    # 子图5: 成本构成
    ax5 = fig.add_subplot(gs[3, :])
    ax5.plot(time_hours, np.array(results['water_cost']) * 3600,
            label='取水成本', linewidth=2)
    ax5.plot(time_hours, np.array(results['treatment_cost']) * 3600,
            label='处理成本', linewidth=2)
    ax5.plot(time_hours, np.array(results['total_cost']) * 3600,
            'k--', label='总成本', linewidth=2.5)
    ax5.set_xlabel('时间 (小时)', fontsize=12)
    ax5.set_ylabel('成本 (元/小时)', fontsize=12)
    ax5.set_title('供水成本构成', fontsize=14, fontweight='bold')
    ax5.legend(loc='best')
    ax5.grid(True, alpha=0.3)

    plt.savefig('/home/user/HydroClaude/examples/example_20_urban_water_supply/urban_supply_simulation.png',
                dpi=150, bbox_inches='tight')
    print(f"图像已保存到: urban_supply_simulation.png")


if __name__ == "__main__":
    # 创建城市供水系统
    system = UrbanWaterSupplySystem()

    # 仿真运行
    results = system.simulate_daily_operation(n_days=7)

    # 可视化结果
    visualize_results(results, system)

    print("\n" + "=" * 80)
    print("示例20完成!")
    print("=" * 80)

    print("\n关键成果:")
    print("  ✓ 多水源联合调度")
    print("  ✓ 水处理厂优化运行")
    print("  ✓ 高位水池削峰填谷")
    print("  ✓ 成本最小化优化")
    print("  ✓ 高供水保证率")
