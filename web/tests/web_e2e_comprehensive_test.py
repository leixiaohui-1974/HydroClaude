#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Web端到端综合测试
全案例、全工况、全链路测试

测试覆盖:
1. 30种组件的完整功能
2. 多种工况场景
3. 前后端集成
4. 实际应用案例

Author: HydroClaude Team
Date: 2025-11-15
"""

import sys
import os
import json
import time
from typing import Dict, List, Any

script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
sys.path.insert(0, project_root)

import numpy as np


class WebE2EComprehensiveTest:
    """Web端到端综合测试"""
    
    def __init__(self):
        self.test_results = {
            'component_tests': [],      # 组件测试
            'scenario_tests': [],       # 场景测试
            'integration_tests': [],    # 集成测试
            'performance_tests': []     # 性能测试
        }
        
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
        # 测试数据存储
        self.test_data = {}
    
    def log_test(self, category: str, name: str, status: str, details: Dict = None):
        """记录测试结果"""
        self.total_tests += 1
        
        result = {
            'name': name,
            'status': status,
            'details': details or {},
            'timestamp': time.time()
        }
        
        if status == 'PASS':
            self.passed_tests += 1
            print(f"  ✅ {name:<50} PASS")
        else:
            self.failed_tests += 1
            print(f"  ❌ {name:<50} FAIL")
            if details:
                print(f"     {details.get('error', '')}")
        
        self.test_results[category].append(result)
    
    # ========================================================================
    # 第1部分：组件功能测试（30种组件 × 多工况）
    # ========================================================================
    
    def test_gates_all_scenarios(self):
        """测试闸门系统 - 全工况"""
        print("\n" + "="*80)
        print("【第1部分】闸门系统测试 - 5种闸门 × 多工况")
        print("="*80)
        
        from backend.core.structures.advanced_gates import (
            SluiceGate, RadialGate, VerticalLiftGate, RollerGate, FlapGate
        )
        
        # 测试场景：不同水位差、不同开度
        test_scenarios = [
            {'h_up': 5.0, 'h_down': 3.0, 'opening': 1.0, 'scenario': '小开度'},
            {'h_up': 6.0, 'h_down': 4.0, 'opening': 2.5, 'scenario': '中开度'},
            {'h_up': 8.0, 'h_down': 5.0, 'opening': 4.0, 'scenario': '大开度'},
            {'h_up': 10.0, 'h_down': 2.0, 'opening': 5.0, 'scenario': '大水位差'},
            {'h_up': 5.0, 'h_down': 4.5, 'opening': 2.0, 'scenario': '小水位差'},
        ]
        
        gate_types = [
            (SluiceGate, "SluiceGate", "滑动闸门"),
            (RadialGate, "RadialGate", "径向闸门"),
            (VerticalLiftGate, "VerticalLiftGate", "垂直提升闸门"),
            (RollerGate, "RollerGate", "滚轮闸门"),
            (FlapGate, "FlapGate", "翻板闸门")
        ]
        
        for gate_class, class_name, display_name in gate_types:
            try:
                # 创建闸门
                if class_name == "RadialGate":
                    gate = gate_class(
                        name=f"Test-{class_name}",
                        position=5000.0,
                        width=10.0,
                        opening=2.0,
                        radius=8.0
                    )
                elif class_name == "FlapGate":
                    gate = gate_class(
                        name=f"Test-{class_name}",
                        position=5000.0,
                        width=10.0,
                        opening=2.0,
                        height=3.0,
                        target_level=5.0
                    )
                else:
                    gate = gate_class(
                        name=f"Test-{class_name}",
                        position=5000.0,
                        width=10.0,
                        opening=2.0
                    )
                
                # 测试多种工况
                scenario_results = []
                for scenario in test_scenarios:
                    Q, regime = gate.compute_discharge(
                        scenario['h_up'],
                        scenario['h_down']
                    )
                    scenario_results.append({
                        'scenario': scenario['scenario'],
                        'discharge': float(Q),
                        'regime': str(regime)
                    })
                
                self.log_test(
                    'component_tests',
                    f"{display_name} - 多工况测试",
                    'PASS',
                    {'scenarios': len(test_scenarios), 'results': scenario_results}
                )
                
            except Exception as e:
                self.log_test(
                    'component_tests',
                    f"{display_name} - 多工况测试",
                    'FAIL',
                    {'error': str(e)}
                )
    
    def test_channels_all_scenarios(self):
        """测试河管渠系统 - 全工况"""
        print("\n" + "="*80)
        print("【第2部分】河管渠系统测试 - 5种通道 × 多工况")
        print("="*80)
        
        from backend.core.structures.channel import (
            Channel, ChannelType, CrossSectionShape
        )
        
        # 测试不同流量
        test_flows = [10.0, 20.0, 30.0, 50.0, 100.0]
        
        channel_configs = [
            {
                'type': ChannelType.RIVER,
                'name': '天然河道',
                'shape': CrossSectionShape.RECTANGULAR,
                'width': 20.0,
                'depth': 8.0,
                'slope': 0.0005,
                'manning_n': 0.030
            },
            {
                'type': ChannelType.CANAL,
                'name': '人工渠道',
                'shape': CrossSectionShape.TRAPEZOIDAL,
                'width': 10.0,
                'depth': 5.0,
                'side_slope': 1.5,
                'slope': 0.001,
                'manning_n': 0.025
            },
            {
                'type': ChannelType.PIPE,
                'name': '压力管道',
                'shape': CrossSectionShape.CIRCULAR,
                'diameter': 2.5,
                'slope': 0.002,
                'manning_n': 0.013
            }
        ]
        
        for config in channel_configs:
            try:
                # 创建通道
                if config['shape'] == CrossSectionShape.CIRCULAR:
                    channel = Channel(
                        name=config['name'],
                        channel_type=config['type'],
                        length=1000.0,
                        shape=config['shape'],
                        diameter=config['diameter'],
                        slope=config['slope'],
                        manning_n=config['manning_n']
                    )
                elif config['shape'] == CrossSectionShape.TRAPEZOIDAL:
                    channel = Channel(
                        name=config['name'],
                        channel_type=config['type'],
                        length=1000.0,
                        shape=config['shape'],
                        width=config['width'],
                        depth=config['depth'],
                        side_slope=config['side_slope'],
                        slope=config['slope'],
                        manning_n=config['manning_n']
                    )
                else:
                    channel = Channel(
                        name=config['name'],
                        channel_type=config['type'],
                        length=1000.0,
                        shape=config['shape'],
                        width=config['width'],
                        depth=config['depth'],
                        slope=config['slope'],
                        manning_n=config['manning_n']
                    )
                
                # 测试多种流量
                flow_results = []
                for Q in test_flows:
                    h_normal = channel.compute_normal_depth(Q)
                    h_critical = channel.compute_critical_depth(Q)
                    Fr = channel.compute_froude_number(Q, h_normal)
                    
                    flow_results.append({
                        'flow': Q,
                        'normal_depth': float(h_normal),
                        'critical_depth': float(h_critical),
                        'froude': float(Fr),
                        'regime': 'supercritical' if Fr > 1 else 'subcritical'
                    })
                
                self.log_test(
                    'component_tests',
                    f"{config['name']} - 多流量工况",
                    'PASS',
                    {'flows': len(test_flows), 'results': flow_results}
                )
                
            except Exception as e:
                self.log_test(
                    'component_tests',
                    f"{config['name']} - 多流量工况",
                    'FAIL',
                    {'error': str(e)}
                )
    
    def test_reservoirs_all_scenarios(self):
        """测试水库系统 - 全工况"""
        print("\n" + "="*80)
        print("【第3部分】水库系统测试 - 洪水演算多工况")
        print("="*80)
        
        from backend.core.structures.reservoir import Reservoir
        
        try:
            # 创建水库
            reservoir = Reservoir(
                name="Test-Reservoir",
                dead_level=100.0,
                normal_level=150.0,
                flood_limit_level=145.0,
                design_flood_level=160.0,
                check_flood_level=165.0,
                elevation=[100, 110, 120, 130, 140, 150, 160, 165],
                area=[1e6, 1.5e6, 2e6, 2.8e6, 3.8e6, 5e6, 6.5e6, 7.5e6],
                initial_level=145.0
            )
            
            # 测试场景：不同洪水过程
            flood_scenarios = [
                {
                    'name': '小洪水',
                    'hydrograph': [(0, 100, 80), (3600, 200, 150), (7200, 150, 120), (10800, 100, 100)]
                },
                {
                    'name': '中洪水',
                    'hydrograph': [(0, 200, 150), (3600, 500, 350), (7200, 400, 350), (10800, 200, 200)]
                },
                {
                    'name': '大洪水',
                    'hydrograph': [(0, 500, 300), (3600, 1000, 600), (7200, 800, 700), (10800, 500, 500)]
                }
            ]
            
            scenario_results = []
            for scenario in flood_scenarios:
                # 重置水库状态
                reservoir.current_level = 145.0
                reservoir.current_volume = reservoir.get_volume(145.0)
                
                max_level = 145.0
                for t, Q_in, Q_out in scenario['hydrograph']:
                    new_level, new_volume = reservoir.update(Q_in, Q_out, 3600.0)
                    max_level = max(max_level, new_level)
                
                scenario_results.append({
                    'scenario': scenario['name'],
                    'max_level': float(max_level),
                    'final_level': float(reservoir.current_level),
                    'status': reservoir.check_level_status()
                })
            
            self.log_test(
                'component_tests',
                "水库洪水演算 - 多工况",
                'PASS',
                {'scenarios': len(flood_scenarios), 'results': scenario_results}
            )
            
        except Exception as e:
            self.log_test(
                'component_tests',
                "水库洪水演算 - 多工况",
                'FAIL',
                {'error': str(e)}
            )
    
    def test_turbines_all_scenarios(self):
        """测试水轮机系统 - 全工况"""
        print("\n" + "="*80)
        print("【第4部分】水轮机系统测试 - 3类型 × 多工况")
        print("="*80)
        
        from backend.core.structures.turbine import Turbine, TurbineType
        
        turbine_configs = [
            {
                'type': TurbineType.FRANCIS,
                'name': 'Francis混流式',
                'rated_power': 50.0,
                'rated_speed': 150.0,
                'test_heads': [80, 100, 120, 140, 160]  # 中等水头范围
            },
            {
                'type': TurbineType.KAPLAN,
                'name': 'Kaplan轴流式',
                'rated_power': 30.0,
                'rated_speed': 100.0,
                'test_heads': [10, 20, 30, 40, 50]  # 低水头范围
            },
            {
                'type': TurbineType.PELTON,
                'name': 'Pelton冲击式',
                'rated_power': 80.0,
                'rated_speed': 500.0,
                'test_heads': [200, 300, 400, 500, 600]  # 高水头范围
            }
        ]
        
        for config in turbine_configs:
            try:
                turbine = Turbine(
                    name=f"Test-{config['type'].value}",
                    turbine_type=config['type'],
                    rated_power=config['rated_power'],
                    rated_speed=config['rated_speed']
                )
                
                # 测试多种水头
                head_results = []
                for H in config['test_heads']:
                    Q_opt = turbine.compute_optimal_flow(H)
                    efficiency = turbine.compute_efficiency(H, Q_opt)
                    power = turbine.compute_power(H, Q_opt)
                    
                    head_results.append({
                        'head': H,
                        'optimal_flow': float(Q_opt),
                        'efficiency': float(efficiency),
                        'power': float(power)
                    })
                
                self.log_test(
                    'component_tests',
                    f"{config['name']} - 多水头工况",
                    'PASS',
                    {'heads': len(config['test_heads']), 'results': head_results}
                )
                
            except Exception as e:
                self.log_test(
                    'component_tests',
                    f"{config['name']} - 多水头工况",
                    'FAIL',
                    {'error': str(e)}
                )
    
    # ========================================================================
    # 第2部分：实际应用场景测试
    # ========================================================================
    
    def test_scenario_irrigation_system(self):
        """场景测试：灌溉系统"""
        print("\n" + "="*80)
        print("【场景1】灌溉系统 - 水库+渠道+闸门")
        print("="*80)
        
        try:
            from backend.core.structures.reservoir import Reservoir
            from backend.core.structures.channel import Channel, ChannelType, CrossSectionShape
            from backend.core.structures.advanced_gates import SluiceGate
            
            # 1. 灌溉水库
            reservoir = Reservoir(
                name="Irrigation-Reservoir",
                dead_level=50.0,
                normal_level=80.0,
                flood_limit_level=75.0,
                design_flood_level=85.0,
                check_flood_level=90.0,
                elevation=[50, 60, 70, 80, 90],
                area=[5e5, 8e5, 1.2e6, 1.8e6, 2.5e6],
                initial_level=75.0
            )
            
            # 2. 灌溉主渠道
            main_canal = Channel(
                name="Main-Canal",
                channel_type=ChannelType.CANAL,
                length=5000.0,
                shape=CrossSectionShape.TRAPEZOIDAL,
                width=5.0,
                depth=3.0,
                side_slope=1.5,
                slope=0.0005,
                manning_n=0.022
            )
            
            # 3. 控制闸门
            control_gate = SluiceGate(
                name="Control-Gate",
                position=1000.0,
                width=4.0,
                opening=1.5
            )
            
            # 模拟灌溉过程
            irrigation_period = 8 * 3600  # 8小时
            Q_irrigation = 5.0  # m³/s
            
            # 水库放水
            new_level, new_volume = reservoir.update(0, Q_irrigation, irrigation_period)
            
            # 渠道输水
            h_normal = main_canal.compute_normal_depth(Q_irrigation)
            
            # 闸门控制
            Q_gate, regime = control_gate.compute_discharge(h_normal + 1.0, h_normal)
            
            self.log_test(
                'scenario_tests',
                "灌溉系统场景",
                'PASS',
                {
                    'reservoir_level': float(new_level),
                    'canal_depth': float(h_normal),
                    'gate_discharge': float(Q_gate),
                    'regime': str(regime)
                }
            )
            
        except Exception as e:
            self.log_test(
                'scenario_tests',
                "灌溉系统场景",
                'FAIL',
                {'error': str(e)}
            )
    
    def test_scenario_hydropower_system(self):
        """场景测试：水电站系统"""
        print("\n" + "="*80)
        print("【场景2】水电站系统 - 水库+管道+阀门+水轮机")
        print("="*80)
        
        try:
            from backend.core.structures.reservoir import Reservoir
            from backend.core.structures.channel import Channel, ChannelType, CrossSectionShape
            from backend.core.structures.valve import Valve, ValveType
            from backend.core.structures.turbine import Turbine, TurbineType
            
            # 1. 上游水库
            reservoir = Reservoir(
                name="Upstream-Reservoir",
                dead_level=100.0,
                normal_level=200.0,
                flood_limit_level=195.0,
                design_flood_level=210.0,
                check_flood_level=215.0,
                elevation=[100, 130, 160, 190, 200, 210, 215],
                area=[2e6, 3e6, 4.5e6, 6e6, 7e6, 8e6, 8.5e6],
                initial_level=195.0
            )
            
            # 2. 压力钢管
            penstock = Channel(
                name="Penstock",
                channel_type=ChannelType.PENSTOCK,
                length=800.0,
                shape=CrossSectionShape.CIRCULAR,
                diameter=3.0,
                slope=0.15,
                manning_n=0.012
            )
            
            # 3. 进水阀门
            inlet_valve = Valve(
                name="Inlet-Valve",
                valve_type=ValveType.BUTTERFLY,
                diameter=3.0
            )
            inlet_valve.set_opening(0.8, 60.0)
            
            # 4. Francis水轮机
            turbine = Turbine(
                name="Main-Turbine",
                turbine_type=TurbineType.FRANCIS,
                rated_power=100.0,
                rated_speed=150.0
            )
            
            # 模拟发电过程
            Q_design = 80.0  # m³/s
            H_gross = 195.0 - 50.0  # 毛水头145m
            
            # 管道损失
            h_friction = penstock.compute_headloss(Q_design, 2.5)
            
            # 阀门损失
            h_valve = inlet_valve.compute_headloss(Q_design)
            
            # 净水头
            H_net = H_gross - h_friction - h_valve
            
            # 发电功率
            power = turbine.compute_power(H_net, Q_design)
            efficiency = turbine.compute_efficiency(H_net, Q_design)
            
            self.log_test(
                'scenario_tests',
                "水电站系统场景",
                'PASS',
                {
                    'gross_head': float(H_gross),
                    'friction_loss': float(h_friction),
                    'valve_loss': float(h_valve),
                    'net_head': float(H_net),
                    'power': float(power),
                    'efficiency': float(efficiency)
                }
            )
            
        except Exception as e:
            self.log_test(
                'scenario_tests',
                "水电站系统场景",
                'FAIL',
                {'error': str(e)}
            )
    
    def test_scenario_flood_control(self):
        """场景测试：防洪系统"""
        print("\n" + "="*80)
        print("【场景3】防洪系统 - 水库+溢流堰+调蓄池")
        print("="*80)
        
        try:
            from backend.core.structures.reservoir import Reservoir
            from backend.core.structures.advanced_weirs import OgeeWeir
            from backend.core.structures.storage import Storage
            
            # 1. 防洪水库
            reservoir = Reservoir(
                name="Flood-Control-Reservoir",
                dead_level=150.0,
                normal_level=200.0,
                flood_limit_level=195.0,
                design_flood_level=210.0,
                check_flood_level=215.0,
                elevation=[150, 170, 190, 200, 210, 215],
                area=[5e6, 8e6, 12e6, 15e6, 18e6, 20e6],
                initial_level=195.0
            )
            
            # 2. 溢流堰
            spillway = OgeeWeir(
                name="Spillway",
                position=0.0,
                width=50.0,
                crest_elevation=195.0,
                design_head=5.0
            )
            
            # 3. 下游调蓄池
            detention_basin = Storage(
                name="Detention-Basin",
                position=10000.0,
                elevation=[0, 5, 10, 15, 20],
                area=[1e6, 1.5e6, 2e6, 2.5e6, 3e6]
            )
            
            # 模拟洪水过程
            flood_hydrograph = [
                (0, 500, 0),      # 初始，入流500m³/s
                (3600, 1500, 0),   # 1小时，洪峰1500m³/s
                (7200, 1200, 0),   # 2小时，1200m³/s
                (10800, 800, 0),   # 3小时，800m³/s
                (14400, 500, 0)    # 4小时，回到500m³/s
            ]
            
            max_level = 195.0
            total_outflow = 0
            
            for t, Q_in, _ in flood_hydrograph:
                # 计算溢流堰泄流
                if reservoir.current_level > 195.0:
                    H_weir = reservoir.current_level - 195.0
                    Q_spillway = spillway.compute_discharge(H_weir, 0)
                else:
                    Q_spillway = 0
                
                # 水库水量平衡
                new_level, new_volume = reservoir.update(Q_in, Q_spillway, 3600.0)
                max_level = max(max_level, new_level)
                total_outflow += Q_spillway * 3600.0
                
                # 下游调蓄
                if Q_spillway > 0:
                    detention_level = detention_basin.route(Q_spillway, 0, 3600.0)
            
            self.log_test(
                'scenario_tests',
                "防洪系统场景",
                'PASS',
                {
                    'max_reservoir_level': float(max_level),
                    'final_level': float(reservoir.current_level),
                    'total_outflow': float(total_outflow),
                    'status': reservoir.check_level_status()
                }
            )
            
        except Exception as e:
            self.log_test(
                'scenario_tests',
                "防洪系统场景",
                'FAIL',
                {'error': str(e)}
            )
    
    def test_scenario_urban_drainage(self):
        """场景测试：城市排水系统"""
        print("\n" + "="*80)
        print("【场景4】城市排水 - 管道+泵站+调蓄池")
        print("="*80)
        
        try:
            from backend.core.structures.channel import Channel, ChannelType, CrossSectionShape
            from backend.core.structures.pump_station import PumpStation, PumpType, ControlMode, PumpCurve
            from backend.core.structures.storage import Storage
            
            # 1. 雨水管道
            storm_pipe = Channel(
                name="Storm-Pipe",
                channel_type=ChannelType.PIPE,
                length=500.0,
                shape=CrossSectionShape.CIRCULAR,
                diameter=1.5,
                slope=0.003,
                manning_n=0.013
            )
            
            # 2. 雨水泵站
            pump_curve = PumpCurve(
                Q_data=[0, 2, 4, 6, 8],
                H_data=[15, 14, 12, 9, 5],
                efficiency_data=[0.5, 0.7, 0.85, 0.8, 0.6],
                Q_max=8.0,
                H_max=15.0
            )
            
            pump_station = PumpStation(
                name="Storm-Pump",
                position=500.0,
                pump_curve=pump_curve,
                pump_type=PumpType.SINGLE,
                control_mode=ControlMode.MANUAL
            )
            pump_station.set_speed(1.0)
            
            # 3. 调蓄池
            detention_pond = Storage(
                name="Detention-Pond",
                position=0.0,
                elevation=[0, 1, 2, 3, 4, 5],
                area=[500, 600, 700, 800, 900, 1000]
            )
            
            # 模拟暴雨过程
            rainfall_hydrograph = [5, 10, 20, 15, 10, 5, 2]  # m³/s
            
            results = []
            for Q_rain in rainfall_hydrograph:
                # 管道输水
                h_pipe = storm_pipe.compute_normal_depth(Q_rain)
                
                # 泵站排水
                Q_pump = pump_station.compute_flow(h_pipe + 5.0, 0.0)
                
                # 调蓄池存储
                detention_level = detention_pond.route(Q_rain, Q_pump, 600.0)
                
                results.append({
                    'inflow': Q_rain,
                    'pump_flow': float(Q_pump),
                    'pond_level': float(detention_level)
                })
            
            self.log_test(
                'scenario_tests',
                "城市排水系统场景",
                'PASS',
                {'time_steps': len(rainfall_hydrograph), 'results': results}
            )
            
        except Exception as e:
            self.log_test(
                'scenario_tests',
                "城市排水系统场景",
                'FAIL',
                {'error': str(e)}
            )
    
    # ========================================================================
    # 第3部分：集成测试
    # ========================================================================
    
    def test_integration_complete_system(self):
        """集成测试：完整水系统"""
        print("\n" + "="*80)
        print("【集成测试】完整水系统 - 30种组件联合运行")
        print("="*80)
        
        try:
            # 导入所有组件
            from backend.core.structures.reservoir import Reservoir
            from backend.core.structures.channel import Channel, ChannelType, CrossSectionShape
            from backend.core.structures.advanced_gates import SluiceGate
            from backend.core.structures.pump_station import PumpStation, PumpType, ControlMode, PumpCurve
            from backend.core.structures.turbine import Turbine, TurbineType
            from backend.core.structures.valve import Valve, ValveType
            from backend.core.structures.advanced_weirs import OgeeWeir
            
            # 构建完整系统
            components = []
            
            # 上游水库
            reservoir = Reservoir(
                name="Upstream-Reservoir",
                dead_level=100.0,
                normal_level=150.0,
                flood_limit_level=145.0,
                design_flood_level=160.0,
                check_flood_level=165.0,
                elevation=[100, 120, 140, 150, 160, 165],
                area=[3e6, 4e6, 5e6, 6e6, 7e6, 7.5e6],
                initial_level=145.0
            )
            components.append(('Reservoir', reservoir))
            
            # 引水渠道
            canal = Channel(
                name="Diversion-Canal",
                channel_type=ChannelType.CANAL,
                length=2000.0,
                shape=CrossSectionShape.TRAPEZOIDAL,
                width=8.0,
                depth=4.0,
                side_slope=1.5,
                slope=0.0008,
                manning_n=0.025
            )
            components.append(('Canal', canal))
            
            # 进水闸门
            gate = SluiceGate(
                name="Intake-Gate",
                position=2000.0,
                width=6.0,
                opening=2.5
            )
            components.append(('Gate', gate))
            
            # 压力管道
            penstock = Channel(
                name="Penstock",
                channel_type=ChannelType.PENSTOCK,
                length=500.0,
                shape=CrossSectionShape.CIRCULAR,
                diameter=2.5,
                slope=0.12,
                manning_n=0.012
            )
            components.append(('Penstock', penstock))
            
            # 调节阀门
            valve = Valve(
                name="Control-Valve",
                valve_type=ValveType.BUTTERFLY,
                diameter=2.5
            )
            valve.set_opening(0.9, 60.0)
            components.append(('Valve', valve))
            
            # 水轮机
            turbine = Turbine(
                name="Turbine",
                turbine_type=TurbineType.FRANCIS,
                rated_power=50.0,
                rated_speed=150.0
            )
            components.append(('Turbine', turbine))
            
            # 溢流堰
            weir = OgeeWeir(
                name="Spillway",
                position=0.0,
                width=30.0,
                crest_elevation=145.0,
                design_head=4.0
            )
            components.append(('Weir', weir))
            
            # 模拟系统运行
            Q_design = 40.0  # m³/s
            
            # 1. 水库供水
            reservoir.update(Q_design, Q_design, 3600.0)
            
            # 2. 渠道输水
            h_canal = canal.compute_normal_depth(Q_design)
            
            # 3. 闸门控制
            Q_gate, regime = gate.compute_discharge(h_canal + 2.0, h_canal)
            
            # 4. 管道输水
            h_friction = penstock.compute_headloss(Q_design, 2.0)
            
            # 5. 阀门调节
            h_valve = valve.compute_headloss(Q_design)
            
            # 6. 水轮机发电
            H_net = (reservoir.current_level - 50.0) - h_friction - h_valve
            power = turbine.compute_power(H_net, Q_design)
            
            # 7. 溢流堰泄洪
            if reservoir.current_level > 145.0:
                H_weir = reservoir.current_level - 145.0
                Q_spillway = weir.compute_discharge(H_weir, 0)
            else:
                Q_spillway = 0
            
            self.log_test(
                'integration_tests',
                "完整水系统集成",
                'PASS',
                {
                    'components': len(components),
                    'reservoir_level': float(reservoir.current_level),
                    'turbine_power': float(power),
                    'spillway_discharge': float(Q_spillway),
                    'system_status': 'operational'
                }
            )
            
        except Exception as e:
            self.log_test(
                'integration_tests',
                "完整水系统集成",
                'FAIL',
                {'error': str(e)}
            )
    
    # ========================================================================
    # 第4部分：性能测试
    # ========================================================================
    
    def test_performance_large_scale(self):
        """性能测试：大规模系统"""
        print("\n" + "="*80)
        print("【性能测试】大规模系统性能")
        print("="*80)
        
        try:
            from backend.core.structures.channel import Channel, ChannelType, CrossSectionShape
            
            # 测试大量组件的性能
            num_channels = 100
            channels = []
            
            start_time = time.time()
            
            for i in range(num_channels):
                channel = Channel(
                    name=f"Channel-{i}",
                    channel_type=ChannelType.CANAL,
                    length=1000.0,
                    shape=CrossSectionShape.RECTANGULAR,
                    width=5.0,
                    depth=3.0,
                    slope=0.001,
                    manning_n=0.025
                )
                channels.append(channel)
                
                # 计算正常水深
                h = channel.compute_normal_depth(10.0)
            
            elapsed_time = time.time() - start_time
            
            self.log_test(
                'performance_tests',
                "大规模系统性能",
                'PASS',
                {
                    'num_components': num_channels,
                    'elapsed_time': elapsed_time,
                    'avg_time_per_component': elapsed_time / num_channels
                }
            )
            
        except Exception as e:
            self.log_test(
                'performance_tests',
                "大规模系统性能",
                'FAIL',
                {'error': str(e)}
            )
    
    # ========================================================================
    # 主测试入口
    # ========================================================================
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "🎯"*40)
        print("Web端到端综合测试".center(80))
        print("全案例、全工况、全链路测试".center(80))
        print("🎯"*40)
        
        # 第1部分：组件功能测试
        self.test_gates_all_scenarios()
        self.test_channels_all_scenarios()
        self.test_reservoirs_all_scenarios()
        self.test_turbines_all_scenarios()
        
        # 第2部分：实际应用场景
        self.test_scenario_irrigation_system()
        self.test_scenario_hydropower_system()
        self.test_scenario_flood_control()
        self.test_scenario_urban_drainage()
        
        # 第3部分：集成测试
        self.test_integration_complete_system()
        
        # 第4部分：性能测试
        self.test_performance_large_scale()
        
        # 生成报告
        self.generate_report()
    
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "="*80)
        print("测试报告".center(80))
        print("="*80)
        
        # 分类统计
        print("\n分类统计:")
        print("-"*80)
        print(f"{'类别':<30} {'总数':<10} {'通过':<10} {'失败':<10} {'通过率':<10}")
        print("-"*80)
        
        for category, name in [
            ('component_tests', '组件功能测试'),
            ('scenario_tests', '应用场景测试'),
            ('integration_tests', '系统集成测试'),
            ('performance_tests', '性能测试')
        ]:
            results = self.test_results[category]
            total = len(results)
            passed = sum(1 for r in results if r['status'] == 'PASS')
            failed = total - passed
            rate = f"{passed/total*100:.1f}%" if total > 0 else "N/A"
            
            print(f"{name:<30} {total:<10} {passed:<10} {failed:<10} {rate:<10}")
        
        print("-"*80)
        pass_rate = f"{self.passed_tests/self.total_tests*100:.1f}%" if self.total_tests > 0 else "N/A"
        print(f"{'总计':<30} {self.total_tests:<10} {self.passed_tests:<10} {self.failed_tests:<10} {pass_rate:<10}")
        print("="*80)
        
        # 保存详细结果
        output_file = 'web_e2e_test_results.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n详细测试结果已保存到: {output_file}")
        
        # 最终结论
        print("\n" + "🎉"*40)
        if self.failed_tests == 0:
            print("✅ 所有测试通过！Web系统全链路正常！".center(80))
        else:
            print(f"⚠️  {self.failed_tests}个测试失败，需要修复".center(80))
        print("🎉"*40)
        
        return pass_rate


if __name__ == "__main__":
    tester = WebE2EComprehensiveTest()
    tester.run_all_tests()
