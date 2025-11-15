#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试案例库 - 100+测试案例
Test Case Library with 100+ Cases

分类：
1. 基础功能测试（30个）
2. 复杂场景测试（30个）
3. 边界条件测试（20个）
4. 极端工况测试（20个）
5. 集成测试（20个）

Author: HydroClaude Team
Date: 2025-11-15
"""

from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum


class TestCategory(Enum):
    """测试类别"""
    BASIC = "basic"                    # 基础功能
    COMPLEX = "complex"                # 复杂场景
    BOUNDARY = "boundary"              # 边界条件
    EXTREME = "extreme"                # 极端工况
    INTEGRATION = "integration"        # 集成测试
    PERFORMANCE = "performance"        # 性能测试


class TestPriority(Enum):
    """测试优先级"""
    CRITICAL = "critical"              # 关键（P0）
    HIGH = "high"                      # 高（P1）
    MEDIUM = "medium"                  # 中（P2）
    LOW = "low"                        # 低（P3）


@dataclass
class TestCase:
    """测试案例"""
    id: str
    name: str
    category: TestCategory
    priority: TestPriority
    description: str
    components: List[str]
    parameters: Dict[str, Any]
    expected_result: Dict[str, Any]
    tags: List[str]


class TestCaseLibrary:
    """测试案例库"""
    
    def __init__(self):
        self.test_cases = []
        self._generate_all_cases()
    
    def _generate_all_cases(self):
        """生成所有测试案例"""
        # 1. 基础功能测试（30个）
        self._generate_basic_cases()
        
        # 2. 复杂场景测试（30个）
        self._generate_complex_cases()
        
        # 3. 边界条件测试（20个）
        self._generate_boundary_cases()
        
        # 4. 极端工况测试（20个）
        self._generate_extreme_cases()
        
        # 5. 集成测试（20个）
        self._generate_integration_cases()
    
    # ========================================================================
    # 第1部分：基础功能测试（30个案例）
    # ========================================================================
    
    def _generate_basic_cases(self):
        """生成基础功能测试案例（30个）"""
        
        # 闸门基础测试（5个）
        for i, (gate_type, opening) in enumerate([
            ("SluiceGate", 1.0),
            ("RadialGate", 2.0),
            ("VerticalLiftGate", 1.5),
            ("RollerGate", 3.0),
            ("FlapGate", 2.5)
        ]):
            self.test_cases.append(TestCase(
                id=f"BASIC-001-{i+1}",
                name=f"{gate_type}基础流量计算",
                category=TestCategory.BASIC,
                priority=TestPriority.CRITICAL,
                description=f"测试{gate_type}在标准工况下的流量计算",
                components=[gate_type],
                parameters={
                    'h_upstream': 5.0,
                    'h_downstream': 3.0,
                    'opening': opening,
                    'width': 10.0
                },
                expected_result={
                    'discharge': {'min': 10.0, 'max': 100.0},
                    'regime': ['free', 'submerged']
                },
                tags=['gate', 'discharge', 'basic']
            ))
        
        # 河道渠道基础测试（5个）
        for i, (channel_type, shape, Q) in enumerate([
            ("River", "rectangular", 50.0),
            ("Canal", "trapezoidal", 30.0),
            ("Pipe", "circular", 10.0),
            ("Tunnel", "circular", 20.0),
            ("Penstock", "circular", 40.0)
        ]):
            self.test_cases.append(TestCase(
                id=f"BASIC-002-{i+1}",
                name=f"{channel_type}正常水深计算",
                category=TestCategory.BASIC,
                priority=TestPriority.CRITICAL,
                description=f"测试{channel_type}的Manning公式计算",
                components=["Channel"],
                parameters={
                    'channel_type': channel_type,
                    'shape': shape,
                    'flow': Q,
                    'slope': 0.001,
                    'manning_n': 0.025
                },
                expected_result={
                    'normal_depth': {'min': 0.5, 'max': 5.0},
                    'critical_depth': {'min': 0.3, 'max': 4.0}
                },
                tags=['channel', 'manning', 'basic']
            ))
        
        # 水库基础测试（5个）
        for i, scenario in enumerate([
            "正常蓄水",
            "洪水入库",
            "泄洪",
            "死水位",
            "超蓄"
        ]):
            self.test_cases.append(TestCase(
                id=f"BASIC-003-{i+1}",
                name=f"水库{scenario}场景",
                category=TestCategory.BASIC,
                priority=TestPriority.HIGH,
                description=f"测试水库在{scenario}场景下的水量平衡",
                components=["Reservoir"],
                parameters={
                    'initial_level': 145.0 + i*5,
                    'Q_in': 100.0 * (i+1),
                    'Q_out': 50.0 * (i+1),
                    'duration': 3600.0
                },
                expected_result={
                    'final_level': {'min': 140.0, 'max': 160.0},
                    'status': ['normal', 'warning', 'alert']
                },
                tags=['reservoir', 'routing', 'basic']
            ))
        
        # 水轮机基础测试（3个）
        for i, (turbine_type, head) in enumerate([
            ("Francis", 100.0),
            ("Kaplan", 20.0),
            ("Pelton", 400.0)
        ]):
            self.test_cases.append(TestCase(
                id=f"BASIC-004-{i+1}",
                name=f"{turbine_type}水轮机发电",
                category=TestCategory.BASIC,
                priority=TestPriority.HIGH,
                description=f"测试{turbine_type}水轮机的发电功率计算",
                components=["Turbine"],
                parameters={
                    'turbine_type': turbine_type,
                    'head': head,
                    'flow': 50.0,
                    'rated_power': 50.0
                },
                expected_result={
                    'power': {'min': 30.0, 'max': 60.0},
                    'efficiency': {'min': 0.85, 'max': 0.95}
                },
                tags=['turbine', 'power', 'basic']
            ))
        
        # 阀门基础测试（7个）
        for i, valve_type in enumerate([
            "Butterfly", "Ball", "Gate", "Globe", 
            "Check", "Needle", "Cone"
        ]):
            self.test_cases.append(TestCase(
                id=f"BASIC-005-{i+1}",
                name=f"{valve_type}阀门水头损失",
                category=TestCategory.BASIC,
                priority=TestPriority.MEDIUM,
                description=f"测试{valve_type}阀门的水头损失计算",
                components=["Valve"],
                parameters={
                    'valve_type': valve_type,
                    'opening': 0.8,
                    'flow': 10.0,
                    'diameter': 0.5
                },
                expected_result={
                    'headloss': {'min': 0.1, 'max': 5.0},
                    'cv': {'min': 0.5, 'max': 1.0}
                },
                tags=['valve', 'headloss', 'basic']
            ))
        
        # 堰基础测试（5个）
        for i, weir_type in enumerate([
            "SharpCrested", "BroadCrested", "VNotch",
            "Rectangular", "Trapezoidal"
        ]):
            self.test_cases.append(TestCase(
                id=f"BASIC-006-{i+1}",
                name=f"{weir_type}堰流量计算",
                category=TestCategory.BASIC,
                priority=TestPriority.MEDIUM,
                description=f"测试{weir_type}堰的流量系数和过流能力",
                components=["Weir"],
                parameters={
                    'weir_type': weir_type,
                    'head': 2.0,
                    'width': 5.0
                },
                expected_result={
                    'discharge': {'min': 5.0, 'max': 50.0},
                    'coefficient': {'min': 0.3, 'max': 0.9}
                },
                tags=['weir', 'discharge', 'basic']
            ))
    
    # ========================================================================
    # 第2部分：复杂场景测试（30个案例）
    # ========================================================================
    
    def _generate_complex_cases(self):
        """生成复杂场景测试案例（30个）"""
        
        # 多闸门联合调度（5个）
        for i in range(5):
            self.test_cases.append(TestCase(
                id=f"COMPLEX-001-{i+1}",
                name=f"多闸门联合调度场景{i+1}",
                category=TestCategory.COMPLEX,
                priority=TestPriority.HIGH,
                description=f"测试{i+2}个闸门的联合运行和流量分配",
                components=["SluiceGate"] * (i+2),
                parameters={
                    'num_gates': i+2,
                    'total_flow': 100.0 * (i+1),
                    'gate_openings': [0.5, 0.7, 0.9, 1.0, 1.2][:i+2]
                },
                expected_result={
                    'flow_distribution': 'balanced',
                    'total_discharge_error': {'max': 0.01}
                },
                tags=['gates', 'coordination', 'complex']
            ))
        
        # 梯级水库联合调度（5个）
        for i in range(5):
            self.test_cases.append(TestCase(
                id=f"COMPLEX-002-{i+1}",
                name=f"{i+2}级水库联合调度",
                category=TestCategory.COMPLEX,
                priority=TestPriority.HIGH,
                description=f"测试{i+2}个梯级水库的联合防洪/发电调度",
                components=["Reservoir"] * (i+2),
                parameters={
                    'num_reservoirs': i+2,
                    'inflow_hydrograph': [500, 1000, 1500, 1000, 500],
                    'coordination': 'flood_control'
                },
                expected_result={
                    'peak_reduction': {'min': 0.2, 'max': 0.5},
                    'all_levels_safe': True
                },
                tags=['reservoir', 'cascade', 'complex']
            ))
        
        # 复杂管网系统（5个）
        for i in range(5):
            self.test_cases.append(TestCase(
                id=f"COMPLEX-003-{i+1}",
                name=f"管网系统场景{i+1} - {(i+1)*5}节点",
                category=TestCategory.COMPLEX,
                priority=TestPriority.MEDIUM,
                description=f"测试{(i+1)*5}节点的复杂管网水力计算",
                components=["Channel", "Valve", "Pump"],
                parameters={
                    'num_nodes': (i+1)*5,
                    'num_pipes': (i+1)*7,
                    'num_pumps': i+1,
                    'demand_pattern': 'variable'
                },
                expected_result={
                    'pressure_range': {'min': 20.0, 'max': 80.0},
                    'flow_balance_error': {'max': 0.01}
                },
                tags=['network', 'pipe', 'complex']
            ))
        
        # 水电站群优化调度（5个）
        for i in range(5):
            self.test_cases.append(TestCase(
                id=f"COMPLEX-004-{i+1}",
                name=f"水电站群{i+2}站优化调度",
                category=TestCategory.COMPLEX,
                priority=TestPriority.HIGH,
                description=f"测试{i+2}个水电站的联合经济运行",
                components=["HydropowerStation"] * (i+2),
                parameters={
                    'num_stations': i+2,
                    'total_load': 500.0 * (i+1),
                    'optimization': 'max_efficiency'
                },
                expected_result={
                    'total_output': {'min': 400.0 * (i+1)},
                    'avg_efficiency': {'min': 0.88}
                },
                tags=['hydropower', 'optimization', 'complex']
            ))
        
        # 城市防洪排涝系统（5个）
        for i in range(5):
            rainfall_intensity = 50 + i*20  # mm/h
            self.test_cases.append(TestCase(
                id=f"COMPLEX-005-{i+1}",
                name=f"城市排水 - {rainfall_intensity}mm/h暴雨",
                category=TestCategory.COMPLEX,
                priority=TestPriority.CRITICAL,
                description=f"测试城市排水系统应对{rainfall_intensity}mm/h暴雨",
                components=["Channel", "PumpStation", "Storage"],
                parameters={
                    'rainfall': rainfall_intensity,
                    'duration': 2.0,  # 小时
                    'catchment_area': 10.0  # km²
                },
                expected_result={
                    'no_overflow': True,
                    'max_ponding_depth': {'max': 0.3}
                },
                tags=['urban', 'drainage', 'complex']
            ))
        
        # 灌溉系统全周期（5个）
        for i in range(5):
            self.test_cases.append(TestCase(
                id=f"COMPLEX-006-{i+1}",
                name=f"灌溉系统 - 第{i+1}轮次",
                category=TestCategory.COMPLEX,
                priority=TestPriority.MEDIUM,
                description=f"测试灌溉系统完整工作周期 - 轮次{i+1}",
                components=["Reservoir", "Channel", "SluiceGate"],
                parameters={
                    'irrigation_area': 5000 * (i+1),  # 亩
                    'crop_type': ['rice', 'wheat', 'corn', 'cotton', 'vegetables'][i],
                    'season': 'summer'
                },
                expected_result={
                    'water_usage_efficiency': {'min': 0.7},
                    'coverage': {'min': 0.95}
                },
                tags=['irrigation', 'agriculture', 'complex']
            ))
    
    # ========================================================================
    # 第3部分：边界条件测试（20个案例）
    # ========================================================================
    
    def _generate_boundary_cases(self):
        """生成边界条件测试案例（20个）"""
        
        # 最小流量边界（5个）
        for i, component in enumerate(["SluiceGate", "Channel", "Turbine", "Valve", "Weir"]):
            self.test_cases.append(TestCase(
                id=f"BOUNDARY-001-{i+1}",
                name=f"{component}最小流量测试",
                category=TestCategory.BOUNDARY,
                priority=TestPriority.HIGH,
                description=f"测试{component}在最小流量条件下的行为",
                components=[component],
                parameters={
                    'flow': 0.001,  # 极小流量
                    'operating_condition': 'minimum'
                },
                expected_result={
                    'stable': True,
                    'error_handling': 'graceful'
                },
                tags=['boundary', 'minimum', 'flow']
            ))
        
        # 最大流量边界（5个）
        for i, component in enumerate(["SluiceGate", "Channel", "Turbine", "Valve", "Weir"]):
            self.test_cases.append(TestCase(
                id=f"BOUNDARY-002-{i+1}",
                name=f"{component}最大流量测试",
                category=TestCategory.BOUNDARY,
                priority=TestPriority.HIGH,
                description=f"测试{component}在最大流量条件下的行为",
                components=[component],
                parameters={
                    'flow': 10000.0,  # 极大流量
                    'operating_condition': 'maximum'
                },
                expected_result={
                    'stable': True,
                    'within_capacity': True
                },
                tags=['boundary', 'maximum', 'flow']
            ))
        
        # 零水位差（5个）
        for i in range(5):
            self.test_cases.append(TestCase(
                id=f"BOUNDARY-003-{i+1}",
                name=f"零水位差场景{i+1}",
                category=TestCategory.BOUNDARY,
                priority=TestPriority.MEDIUM,
                description="测试上下游水位相等时的系统行为",
                components=["SluiceGate"],
                parameters={
                    'h_upstream': 5.0,
                    'h_downstream': 5.0,
                    'opening': 1.0 + i*0.5
                },
                expected_result={
                    'discharge': {'max': 0.1},
                    'no_error': True
                },
                tags=['boundary', 'zero_diff', 'water_level']
            ))
        
        # 临界工况（5个）
        for i, condition in enumerate([
            "临界水深",
            "临界Froude数",
            "临界雷诺数",
            "临界空化数",
            "临界稳定性"
        ]):
            self.test_cases.append(TestCase(
                id=f"BOUNDARY-004-{i+1}",
                name=f"{condition}边界测试",
                category=TestCategory.BOUNDARY,
                priority=TestPriority.HIGH,
                description=f"测试系统在{condition}条件下的临界行为",
                components=["Channel", "Turbine"],
                parameters={
                    'condition': condition,
                    'safety_factor': 1.0
                },
                expected_result={
                    'transition_smooth': True,
                    'no_instability': True
                },
                tags=['boundary', 'critical', condition.replace(' ', '_')]
            ))
    
    # ========================================================================
    # 第4部分：极端工况测试（20个案例）
    # ========================================================================
    
    def _generate_extreme_cases(self):
        """生成极端工况测试案例（20个）"""
        
        # 千年一遇洪水（5个）
        for i in range(5):
            return_period = 100 * (i+1)
            self.test_cases.append(TestCase(
                id=f"EXTREME-001-{i+1}",
                name=f"{return_period}年一遇洪水",
                category=TestCategory.EXTREME,
                priority=TestPriority.CRITICAL,
                description=f"测试系统应对{return_period}年一遇特大洪水",
                components=["Reservoir", "OgeeWeir", "Storage"],
                parameters={
                    'return_period': return_period,
                    'peak_flow': 5000 * (i+1),
                    'flood_volume': 1e9 * (i+1)
                },
                expected_result={
                    'dam_safe': True,
                    'max_level': {'max': 'check_flood_level'}
                },
                tags=['extreme', 'flood', 'safety']
            ))
        
        # 干旱低水位（5个）
        for i in range(5):
            self.test_cases.append(TestCase(
                id=f"EXTREME-002-{i+1}",
                name=f"极端干旱场景{i+1}",
                category=TestCategory.EXTREME,
                priority=TestPriority.HIGH,
                description=f"测试水库/河道在极端干旱条件下运行",
                components=["Reservoir", "Channel"],
                parameters={
                    'drought_level': i+1,
                    'water_level': 'dead_level',
                    'inflow': 1.0  # 极小入流
                },
                expected_result={
                    'emergency_supply': 'available',
                    'min_ecological_flow': 'maintained'
                },
                tags=['extreme', 'drought', 'low_water']
            ))
        
        # 地震工况（5个）
        for i in range(5):
            magnitude = 6.0 + i*0.5
            self.test_cases.append(TestCase(
                id=f"EXTREME-003-{i+1}",
                name=f"{magnitude}级地震工况",
                category=TestCategory.EXTREME,
                priority=TestPriority.CRITICAL,
                description=f"测试{magnitude}级地震对水工结构的影响",
                components=["Reservoir", "SluiceGate", "HydropowerStation"],
                parameters={
                    'earthquake_magnitude': magnitude,
                    'epicenter_distance': 10.0,  # km
                    'peak_acceleration': 0.1 * (i+1)  # g
                },
                expected_result={
                    'structural_integrity': True,
                    'emergency_shutdown': 'successful'
                },
                tags=['extreme', 'earthquake', 'safety']
            ))
        
        # 极端温度（5个）
        for i, (season, temp) in enumerate([
            ("极寒", -30),
            ("严寒", -20),
            ("酷暑", 45),
            ("高温", 40),
            ("温差", 35)
        ]):
            self.test_cases.append(TestCase(
                id=f"EXTREME-004-{i+1}",
                name=f"{season}气候 - {temp}°C",
                category=TestCategory.EXTREME,
                priority=TestPriority.MEDIUM,
                description=f"测试系统在{season}({temp}°C)条件下运行",
                components=["Channel", "Valve", "Turbine"],
                parameters={
                    'temperature': temp,
                    'ice_formation': temp < 0,
                    'thermal_expansion': temp > 35
                },
                expected_result={
                    'operational': True,
                    'protection_active': True
                },
                tags=['extreme', 'temperature', season]
            ))
    
    # ========================================================================
    # 第5部分：集成测试（20个案例）
    # ========================================================================
    
    def _generate_integration_cases(self):
        """生成集成测试案例（20个）"""
        
        # 完整流域系统（5个）
        for i in range(5):
            self.test_cases.append(TestCase(
                id=f"INTEGRATION-001-{i+1}",
                name=f"流域系统集成 - 规模{i+1}",
                category=TestCategory.INTEGRATION,
                priority=TestPriority.CRITICAL,
                description=f"测试包含{(i+1)*10}个组件的完整流域系统",
                components=["Reservoir", "Channel", "SluiceGate", "Weir", "Station"],
                parameters={
                    'num_components': (i+1)*10,
                    'basin_area': 1000 * (i+1),  # km²
                    'simulation_period': 30  # 天
                },
                expected_result={
                    'water_balance_error': {'max': 0.001},
                    'all_constraints_met': True
                },
                tags=['integration', 'basin', 'full_system']
            ))
        
        # 多目标优化（5个）
        for i, objectives in enumerate([
            ["flood_control"],
            ["power_generation"],
            ["water_supply"],
            ["flood_control", "power_generation"],
            ["flood_control", "power_generation", "water_supply"]
        ]):
            self.test_cases.append(TestCase(
                id=f"INTEGRATION-002-{i+1}",
                name=f"多目标优化 - {len(objectives)}目标",
                category=TestCategory.INTEGRATION,
                priority=TestPriority.HIGH,
                description=f"测试{len(objectives)}个目标的联合优化",
                components=["Reservoir", "HydropowerStation", "Channel"],
                parameters={
                    'objectives': objectives,
                    'weights': [1.0/len(objectives)] * len(objectives),
                    'optimization_horizon': 7  # 天
                },
                expected_result={
                    'pareto_optimal': True,
                    'all_objectives_improved': True
                },
                tags=['integration', 'optimization', 'multi_objective']
            ))
        
        # 长时间序列模拟（5个）
        for i in range(5):
            duration = 365 * (i+1)  # 天
            self.test_cases.append(TestCase(
                id=f"INTEGRATION-003-{i+1}",
                name=f"长期模拟 - {duration}天",
                category=TestCategory.INTEGRATION,
                priority=TestPriority.MEDIUM,
                description=f"测试系统{duration}天长时间序列模拟",
                components=["Reservoir", "Channel", "HydropowerStation"],
                parameters={
                    'duration_days': duration,
                    'time_step': 3600,  # 秒
                    'historical_data': True
                },
                expected_result={
                    'numerical_stability': True,
                    'annual_statistics': 'valid'
                },
                tags=['integration', 'long_term', 'simulation']
            ))
        
        # 实时调度（5个）
        for i in range(5):
            self.test_cases.append(TestCase(
                id=f"INTEGRATION-004-{i+1}",
                name=f"实时调度 - 场景{i+1}",
                category=TestCategory.INTEGRATION,
                priority=TestPriority.HIGH,
                description=f"测试实时预报+实时调度系统",
                components=["Reservoir", "Channel", "SluiceGate", "Forecast"],
                parameters={
                    'forecast_horizon': (i+1)*3,  # 小时
                    'update_interval': 1800,  # 秒
                    'decision_support': True
                },
                expected_result={
                    'response_time': {'max': 60},  # 秒
                    'forecast_accuracy': {'min': 0.8}
                },
                tags=['integration', 'real_time', 'forecast']
            ))
    
    def get_cases_by_category(self, category: TestCategory) -> List[TestCase]:
        """按类别获取测试案例"""
        return [case for case in self.test_cases if case.category == category]
    
    def get_cases_by_priority(self, priority: TestPriority) -> List[TestCase]:
        """按优先级获取测试案例"""
        return [case for case in self.test_cases if case.priority == priority]
    
    def get_cases_by_component(self, component: str) -> List[TestCase]:
        """按组件获取测试案例"""
        return [case for case in self.test_cases if component in case.components]
    
    def get_total_count(self) -> int:
        """获取总案例数"""
        return len(self.test_cases)
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        stats = {
            'total': len(self.test_cases),
            'by_category': {},
            'by_priority': {},
            'by_component': {}
        }
        
        for category in TestCategory:
            stats['by_category'][category.value] = len(self.get_cases_by_category(category))
        
        for priority in TestPriority:
            stats['by_priority'][priority.value] = len(self.get_cases_by_priority(priority))
        
        all_components = set()
        for case in self.test_cases:
            all_components.update(case.components)
        
        for component in all_components:
            stats['by_component'][component] = len(self.get_cases_by_component(component))
        
        return stats


# 使用示例
if __name__ == "__main__":
    library = TestCaseLibrary()
    
    print("="*80)
    print("测试案例库统计")
    print("="*80)
    
    stats = library.get_statistics()
    
    print(f"\n总案例数: {stats['total']}")
    
    print("\n按类别分布:")
    for category, count in stats['by_category'].items():
        print(f"  {category:<20} {count:>3}个")
    
    print("\n按优先级分布:")
    for priority, count in stats['by_priority'].items():
        print(f"  {priority:<20} {count:>3}个")
    
    print("\n按组件分布:")
    for component, count in sorted(stats['by_component'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {component:<20} {count:>3}个")
    
    print("\n" + "="*80)
    print(f"✅ 测试案例库已生成 - 共{stats['total']}个测试案例")
    print("="*80)
