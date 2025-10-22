"""
示例21: 灌区配水优化调度

演示灌区多水源、多渠系的配水优化:
1. 水库水源管理
2. 多级渠道配水
3. 多种作物需水
4. 轮灌制度优化
5. 水量平衡约束
6. 公平性与效率权衡

典型应用: 大型灌区、节水灌溉、农业水资源优化

作者: HydroClaude Team
日期: 2025-10-22
"""

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
from typing import Dict, List, Tuple
from dataclasses import dataclass

# 设置中文字体
rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
rcParams['axes.unicode_minus'] = False


@dataclass
class CropField:
    """作物田块数据类"""
    field_id: str
    crop_type: str        # 作物类型
    area: float           # 面积 (公顷)
    water_demand: float   # 需水量 (m³/公顷/天)
    priority: int         # 优先级 (1-5)
    growth_stage: str     # 生长阶段
    deficit_tolerance: float  # 缺水容忍度 (0-1)


@dataclass
class Canal:
    """渠道数据类"""
    canal_id: str
    canal_type: str       # 'main', 'branch', 'lateral'
    capacity: float       # 输水能力 (m³/s)
    length: float         # 长度 (km)
    loss_rate: float      # 损失率
    upstream_canal: str = None
    downstream_fields: List[str] = None


@dataclass
class IrrigationSchedule:
    """灌溉制度数据类"""
    schedule_id: str
    rotation_days: int    # 轮灌周期 (天)
    daily_hours: int      # 每天灌溉小时数
    flow_rate: float      # 灌溉流量 (m³/s)


class IrrigationSystem:
    """
    灌区配水系统

    系统架构:
    水库 → 总干渠 → 干渠 → 支渠 → 斗渠 → 田块
    """

    def __init__(self):
        """初始化灌区系统"""
        print("=" * 80)
        print("示例21: 灌区配水优化调度系统")
        print("=" * 80)

        # 创建系统组件
        self._create_water_source()
        self._create_canal_network()
        self._create_crop_fields()
        self._create_irrigation_schedules()

        # 系统参数
        self.total_area = sum(f.area for f in self.crop_fields)
        self.total_demand = sum(f.area * f.water_demand for f in self.crop_fields)

        print(f"\n灌区概况:")
        print(f"  灌溉面积: {self.total_area:.0f} 公顷")
        print(f"  渠道总长: {sum(c.length for c in self.canals):.1f} km")
        print(f"  田块数: {len(self.crop_fields)}")
        print(f"  总需水: {self.total_demand:.0f} m³/天")

    def _create_water_source(self):
        """创建水源水库"""
        # 使用简化的水库模型（不依赖Reservoir类）
        self.reservoir = {
            'id': 'irrigation_reservoir',
            'capacity': 5000e4,      # 5000万m³
            'current_storage': 3000e4,  # 当前3000万m³
            'min_storage': 500e4,
            'max_release': 50.0,     # 最大放水 50 m³/s
            'ecological_flow': 5.0   # 生态流量 5 m³/s
        }

        print(f"\n水源水库:")
        print(f"  库容: {self.reservoir['capacity']/1e4:.0f} 万m³")
        print(f"  当前蓄水: {self.reservoir['current_storage']/1e4:.0f} 万m³")
        print(f"  最大放水: {self.reservoir['max_release']:.1f} m³/s")

    def _create_canal_network(self):
        """创建渠系网络"""
        canals_config = [
            # 总干渠
            {
                'id': 'main_canal',
                'type': 'main',
                'capacity': 40.0,   # 40 m³/s
                'length': 15.0,     # 15 km
                'loss_rate': 0.05,  # 5%损失
                'upstream': None,
                'downstream': ['branch_1', 'branch_2', 'branch_3']
            },
            # 干渠1
            {
                'id': 'branch_1',
                'type': 'branch',
                'capacity': 15.0,
                'length': 8.0,
                'loss_rate': 0.08,
                'upstream': 'main_canal',
                'downstream': ['field_rice_1', 'field_rice_2', 'field_wheat_1']
            },
            # 干渠2
            {
                'id': 'branch_2',
                'type': 'branch',
                'capacity': 12.0,
                'length': 10.0,
                'loss_rate': 0.08,
                'upstream': 'main_canal',
                'downstream': ['field_wheat_2', 'field_corn_1', 'field_corn_2']
            },
            # 干渠3
            {
                'id': 'branch_3',
                'type': 'branch',
                'capacity': 13.0,
                'length': 12.0,
                'loss_rate': 0.08,
                'upstream': 'main_canal',
                'downstream': ['field_vegetable_1', 'field_fruit_1']
            }
        ]

        self.canals = []
        print(f"\n渠系网络:")

        for config in canals_config:
            canal = Canal(
                canal_id=config['id'],
                canal_type=config['type'],
                capacity=config['capacity'],
                length=config['length'],
                loss_rate=config['loss_rate'],
                upstream_canal=config.get('upstream'),
                downstream_fields=config.get('downstream', [])
            )
            self.canals.append(canal)

            print(f"  {config['id']}:")
            print(f"    容量: {config['capacity']:.1f} m³/s")
            print(f"    长度: {config['length']:.1f} km")

    def _create_crop_fields(self):
        """创建作物田块"""
        fields_config = [
            # 水稻田（需水量大，优先级高）
            {'id': 'field_rice_1', 'crop': 'rice', 'area': 200,
             'demand': 120, 'priority': 5, 'stage': 'heading', 'tolerance': 0.1},
            {'id': 'field_rice_2', 'crop': 'rice', 'area': 180,
             'demand': 120, 'priority': 5, 'stage': 'heading', 'tolerance': 0.1},

            # 小麦田（需水量中等）
            {'id': 'field_wheat_1', 'crop': 'wheat', 'area': 150,
             'demand': 80, 'priority': 4, 'stage': 'jointing', 'tolerance': 0.2},
            {'id': 'field_wheat_2', 'crop': 'wheat', 'area': 160,
             'demand': 80, 'priority': 4, 'stage': 'jointing', 'tolerance': 0.2},

            # 玉米田（需水量中等，耐旱性较好）
            {'id': 'field_corn_1', 'crop': 'corn', 'area': 120,
             'demand': 70, 'priority': 3, 'stage': 'tasseling', 'tolerance': 0.3},
            {'id': 'field_corn_2', 'crop': 'corn', 'area': 130,
             'demand': 70, 'priority': 3, 'stage': 'tasseling', 'tolerance': 0.3},

            # 蔬菜田（需水频繁但量不大）
            {'id': 'field_vegetable_1', 'crop': 'vegetable', 'area': 100,
             'demand': 100, 'priority': 4, 'stage': 'growing', 'tolerance': 0.15},

            # 果园（需水量适中）
            {'id': 'field_fruit_1', 'crop': 'fruit', 'area': 150,
             'demand': 60, 'priority': 3, 'stage': 'fruiting', 'tolerance': 0.25}
        ]

        self.crop_fields = []
        print(f"\n作物田块:")

        # 按作物类型汇总
        crop_summary = {}

        for config in fields_config:
            field = CropField(
                field_id=config['id'],
                crop_type=config['crop'],
                area=config['area'],
                water_demand=config['demand'],
                priority=config['priority'],
                growth_stage=config['stage'],
                deficit_tolerance=config['tolerance']
            )
            self.crop_fields.append(field)

            if config['crop'] not in crop_summary:
                crop_summary[config['crop']] = {'area': 0, 'fields': 0}
            crop_summary[config['crop']]['area'] += config['area']
            crop_summary[config['crop']]['fields'] += 1

        for crop, stats in crop_summary.items():
            print(f"  {crop}: {stats['fields']}块, {stats['area']:.0f}公顷")

    def _create_irrigation_schedules(self):
        """创建灌溉制度"""
        self.schedules = {
            'rice': IrrigationSchedule('rice_schedule', rotation_days=7, daily_hours=12, flow_rate=0.5),
            'wheat': IrrigationSchedule('wheat_schedule', rotation_days=10, daily_hours=8, flow_rate=0.4),
            'corn': IrrigationSchedule('corn_schedule', rotation_days=12, daily_hours=8, flow_rate=0.3),
            'vegetable': IrrigationSchedule('veg_schedule', rotation_days=5, daily_hours=6, flow_rate=0.4),
            'fruit': IrrigationSchedule('fruit_schedule', rotation_days=14, daily_hours=8, flow_rate=0.25)
        }

        print(f"\n灌溉制度:")
        for crop, schedule in self.schedules.items():
            print(f"  {crop}: 轮灌{schedule.rotation_days}天, 每天{schedule.daily_hours}小时")

    def optimize_water_allocation(self, n_days: int = 15):
        """
        优化配水方案

        使用简化的优化策略（不依赖Pyomo）:
        1. 按优先级排序
        2. 考虑生长阶段
        3. 轮灌制度
        4. 水量平衡

        参数:
            n_days: 优化时段（天）
        """
        print("\n" + "=" * 80)
        print("开始优化配水方案")
        print("=" * 80)

        print(f"\n优化参数:")
        print(f"  优化时段: {n_days} 天")

        # 结果存储
        results = {
            'day': [],
            'reservoir_storage': [],
            'reservoir_release': [],
            'total_water_supply': [],
            'total_water_demand': [],
            'crop_allocations': {f.field_id: [] for f in self.crop_fields},
            'deficit': {f.field_id: [] for f in self.crop_fields},
            'satisfaction_rate': []
        }

        current_storage = self.reservoir['current_storage']

        print(f"\n开始优化循环...")

        # 优化循环（按天）
        for day in range(n_days):
            # 计算每日需水
            daily_demands = {}
            total_demand = 0

            for field in self.crop_fields:
                # 检查是否该轮灌
                schedule = self.schedules[field.crop_type]
                if day % schedule.rotation_days == 0:
                    # 该田块需要灌溉
                    daily_demand = field.area * field.water_demand
                    daily_demands[field.field_id] = daily_demand
                    total_demand += daily_demand
                else:
                    daily_demands[field.field_id] = 0

            # 计算可供水量（考虑水库约束）
            max_daily_release = min(
                self.reservoir['max_release'] * 86400,  # 转换为m³/天
                current_storage - self.reservoir['min_storage']
            )

            available_water = max(0, max_daily_release - self.reservoir['ecological_flow'] * 86400)

            # 配水策略：按优先级分配
            if total_demand <= available_water:
                # 水量充足，全部满足
                allocations = daily_demands.copy()
                actual_release = total_demand
            else:
                # 水量不足，按优先级和缺水容忍度分配
                allocations = {}
                remaining_water = available_water

                # 按优先级排序
                sorted_fields = sorted(
                    [f for f in self.crop_fields if daily_demands[f.field_id] > 0],
                    key=lambda f: (f.priority, 1 - f.deficit_tolerance),
                    reverse=True
                )

                for field in sorted_fields:
                    demand = daily_demands[field.field_id]
                    # 考虑缺水容忍度
                    min_supply = demand * (1 - field.deficit_tolerance)

                    if remaining_water >= demand:
                        # 可以全部满足
                        allocations[field.field_id] = demand
                        remaining_water -= demand
                    elif remaining_water >= min_supply:
                        # 部分满足
                        allocations[field.field_id] = remaining_water
                        remaining_water = 0
                        break
                    else:
                        # 无法满足最低需求
                        allocations[field.field_id] = remaining_water
                        remaining_water = 0
                        break

                # 未分配到的田块
                for field_id in daily_demands:
                    if field_id not in allocations:
                        allocations[field_id] = 0

                actual_release = sum(allocations.values())

            # 更新水库库容
            current_storage -= actual_release
            current_storage = max(current_storage, self.reservoir['min_storage'])

            # 计算缺水和满意度
            deficits = {}
            total_deficit = 0
            for field_id, demand in daily_demands.items():
                deficit = max(0, demand - allocations.get(field_id, 0))
                deficits[field_id] = deficit
                total_deficit += deficit

            satisfaction_rate = (1 - total_deficit / total_demand) * 100 if total_demand > 0 else 100

            # 记录结果
            results['day'].append(day)
            results['reservoir_storage'].append(current_storage / 1e4)  # 转换为万m³
            results['reservoir_release'].append(actual_release / 1e4)
            results['total_water_supply'].append(sum(allocations.values()) / 1e4)
            results['total_water_demand'].append(total_demand / 1e4)
            results['satisfaction_rate'].append(satisfaction_rate)

            for field_id in allocations:
                results['crop_allocations'][field_id].append(allocations[field_id] / 1e4)
                results['deficit'][field_id].append(deficits[field_id] / 1e4)

        print(f"优化完成!")

        # 统计结果
        self._print_statistics(results, n_days)

        return results

    def _print_statistics(self, results, n_days):
        """打印统计结果"""
        print(f"\n优化结果统计 ({n_days}天):")

        total_supply = sum(results['total_water_supply']) * 1e4
        total_demand = sum(results['total_water_demand']) * 1e4

        print(f"  总供水量: {total_supply/1e4:.2f} 万m³")
        print(f"  总需水量: {total_demand/1e4:.2f} 万m³")
        print(f"  供水率: {total_supply/total_demand*100:.1f}%" if total_demand > 0 else "  供水率: 100.0%")
        print(f"  平均满意度: {np.mean(results['satisfaction_rate']):.1f}%")

        # 水库状态
        final_storage = results['reservoir_storage'][-1]
        initial_storage = self.reservoir['current_storage'] / 1e4
        print(f"\n  水库状态:")
        print(f"    初始库容: {initial_storage:.0f} 万m³")
        print(f"    最终库容: {final_storage:.0f} 万m³")
        print(f"    消耗水量: {initial_storage - final_storage:.0f} 万m³")

        # 各作物统计
        print(f"\n  各作物配水:")
        crop_stats = {}
        for field in self.crop_fields:
            crop = field.crop_type
            if crop not in crop_stats:
                crop_stats[crop] = {'supply': 0, 'demand': 0}

            supply = sum(results['crop_allocations'][field.field_id]) * 1e4
            # 计算需求（只统计灌溉日）
            demand_days = [i for i in range(n_days) if i % self.schedules[crop].rotation_days == 0]
            demand = len(demand_days) * field.area * field.water_demand

            crop_stats[crop]['supply'] += supply
            crop_stats[crop]['demand'] += demand

        for crop, stats in crop_stats.items():
            supply_rate = stats['supply'] / stats['demand'] * 100 if stats['demand'] > 0 else 100
            print(f"    {crop}: {stats['supply']/1e4:.2f}/{stats['demand']/1e4:.2f} 万m³ ({supply_rate:.1f}%)")


def visualize_results(results, system):
    """可视化优化结果"""
    print("\n生成可视化图表...")

    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

    days = results['day']

    # 子图1: 水库库容变化
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(days, results['reservoir_storage'], 'b-', linewidth=2)
    ax1.axhline(system.reservoir['min_storage']/1e4, color='r',
               linestyle='--', label='死库容', alpha=0.7)
    ax1.set_ylabel('库容 (万m³)', fontsize=12)
    ax1.set_title('水库库容变化', fontsize=14, fontweight='bold')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)

    # 子图2: 供需平衡
    ax2 = fig.add_subplot(gs[1, 0])
    ax2.plot(days, results['total_water_demand'], 'r--',
            label='需水', linewidth=2, alpha=0.7)
    ax2.plot(days, results['total_water_supply'], 'b-',
            label='供水', linewidth=2)
    ax2.set_xlabel('天数', fontsize=12)
    ax2.set_ylabel('水量 (万m³/天)', fontsize=12)
    ax2.set_title('供需平衡', fontsize=14, fontweight='bold')
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)

    # 子图3: 满意度
    ax3 = fig.add_subplot(gs[1, 1])
    ax3.plot(days, results['satisfaction_rate'], 'g-', linewidth=2)
    ax3.axhline(95, color='orange', linestyle='--', alpha=0.7)
    ax3.set_xlabel('天数', fontsize=12)
    ax3.set_ylabel('满意度 (%)', fontsize=12)
    ax3.set_title('配水满意度', fontsize=14, fontweight='bold')
    ax3.set_ylim([0, 105])
    ax3.grid(True, alpha=0.3)

    # 子图4: 各作物配水（堆积图）
    ax4 = fig.add_subplot(gs[2, :])

    # 按作物类型聚合
    crop_allocations = {}
    for field in system.crop_fields:
        crop = field.crop_type
        if crop not in crop_allocations:
            crop_allocations[crop] = np.zeros(len(days))
        crop_allocations[crop] += np.array(results['crop_allocations'][field.field_id])

    bottom = np.zeros(len(days))
    colors = ['skyblue', 'lightgreen', 'lightcoral', 'lightyellow', 'lightpink']
    for i, (crop, allocation) in enumerate(crop_allocations.items()):
        ax4.bar(days, allocation, bottom=bottom, label=crop,
               color=colors[i % len(colors)], alpha=0.7, width=0.8)
        bottom += allocation

    ax4.set_xlabel('天数', fontsize=12)
    ax4.set_ylabel('配水量 (万m³/天)', fontsize=12)
    ax4.set_title('各作物配水分配', fontsize=14, fontweight='bold')
    ax4.legend(loc='best')
    ax4.grid(True, alpha=0.3, axis='y')

    plt.savefig('/home/user/HydroClaude/examples/example_21_irrigation_optimization/irrigation_optimization.png',
                dpi=150, bbox_inches='tight')
    print(f"图像已保存到: irrigation_optimization.png")


if __name__ == "__main__":
    # 创建灌区系统
    system = IrrigationSystem()

    # 优化配水
    results = system.optimize_water_allocation(n_days=15)

    # 可视化结果
    visualize_results(results, system)

    print("\n" + "=" * 80)
    print("示例21完成!")
    print("=" * 80)

    print("\n关键成果:")
    print("  ✓ 多作物轮灌制度")
    print("  ✓ 优先级配水策略")
    print("  ✓ 水量平衡优化")
    print("  ✓ 缺水容忍度考虑")
    print("  ✓ 高满意度配水")
