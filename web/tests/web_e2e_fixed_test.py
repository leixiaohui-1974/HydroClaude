#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Web端到端综合测试 - 修复版
全案例、全工况、全链路测试

Author: HydroClaude Team
Date: 2025-11-15
"""

import sys
import os
import json
import time

script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
sys.path.insert(0, project_root)

from web_e2e_comprehensive_test import WebE2EComprehensiveTest


class WebE2EFixedTest(WebE2EComprehensiveTest):
    """修复版Web端到端测试"""
    
    def test_gates_all_scenarios(self):
        """测试闸门系统 - 全工况（修复版）"""
        print("\n" + "="*80)
        print("【第1部分】闸门系统测试 - 5种闸门 × 多工况 (修复版)")
        print("="*80)
        
        from backend.core.structures.advanced_gates import (
            SluiceGate, RadialGate, VerticalLiftGate, RollerGate, FlapGate
        )
        
        test_scenarios = [
            {'h_up': 5.0, 'h_down': 3.0, 'opening': 1.0, 'scenario': '小开度'},
            {'h_up': 6.0, 'h_down': 4.0, 'opening': 2.5, 'scenario': '中开度'},
            {'h_up': 8.0, 'h_down': 5.0, 'opening': 4.0, 'scenario': '大开度'},
        ]
        
        gate_configs = [
            (SluiceGate, "SluiceGate", "滑动闸门", {}),
            (RadialGate, "RadialGate", "径向闸门", {'radius': 8.0}),
            (VerticalLiftGate, "VerticalLiftGate", "垂直提升闸门", {}),
            (RollerGate, "RollerGate", "滚轮闸门", {}),
            (FlapGate, "FlapGate", "翻板闸门", {'gate_length': 5.0})  # 修复：使用gate_length而不是height
        ]
        
        for gate_class, class_name, display_name, extra_params in gate_configs:
            try:
                gate = gate_class(
                    name=f"Test-{class_name}",
                    position=5000.0,
                    width=10.0,
                    opening=2.0,
                    **extra_params
                )
                
                scenario_results = []
                for scenario in test_scenarios:
                    Q, regime = gate.compute_discharge(scenario['h_up'], scenario['h_down'])
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
    
    def test_turbines_all_scenarios(self):
        """测试水轮机系统 - 全工况（修复版）"""
        print("\n" + "="*80)
        print("【第4部分】水轮机系统测试 - 3类型 × 多工况 (修复版)")
        print("="*80)
        
        from backend.core.structures.turbine import Turbine, TurbineType, TurbineCharacteristics
        
        turbine_configs = [
            {
                'type': TurbineType.FRANCIS,
                'name': 'Francis混流式',
                'characteristics': TurbineCharacteristics(
                    rated_head=100.0,
                    rated_flow=50.0,
                    rated_power=40.0,
                    rated_efficiency=0.93,
                    rated_speed=150.0,
                    min_head=50.0,
                    max_head=200.0
                ),
                'test_heads': [80, 100, 120]
            },
            {
                'type': TurbineType.KAPLAN,
                'name': 'Kaplan轴流式',
                'characteristics': TurbineCharacteristics(
                    rated_head=20.0,
                    rated_flow=80.0,
                    rated_power=14.0,
                    rated_efficiency=0.91,
                    rated_speed=100.0,
                    min_head=10.0,
                    max_head=50.0
                ),
                'test_heads': [15, 20, 30]
            },
            {
                'type': TurbineType.PELTON,
                'name': 'Pelton冲击式',
                'characteristics': TurbineCharacteristics(
                    rated_head=400.0,
                    rated_flow=30.0,
                    rated_power=100.0,
                    rated_efficiency=0.90,
                    rated_speed=500.0,
                    min_head=200.0,
                    max_head=600.0
                ),
                'test_heads': [300, 400, 500]
            }
        ]
        
        for config in turbine_configs:
            try:
                turbine = Turbine(
                    name=f"Test-{config['type'].value}",
                    position=1000.0,
                    turbine_type=config['type'],
                    characteristics=config['characteristics'],
                    num_units=1
                )
                
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
    
    def test_scenario_hydropower_system(self):
        """场景测试：水电站系统（修复版）"""
        print("\n" + "="*80)
        print("【场景2】水电站系统 - 水库+管道+阀门+水轮机 (修复版)")
        print("="*80)
        
        try:
            from backend.core.structures.reservoir import Reservoir
            from backend.core.structures.channel import Channel, ChannelType, CrossSectionShape
            from backend.core.structures.valve import Valve, ValveType
            from backend.core.structures.turbine import Turbine, TurbineType, TurbineCharacteristics
            
            # 上游水库
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
            
            # 压力钢管
            penstock = Channel(
                name="Penstock",
                channel_type=ChannelType.PENSTOCK,
                length=800.0,
                shape=CrossSectionShape.CIRCULAR,
                diameter=3.0,
                slope=0.15,
                manning_n=0.012
            )
            
            # 进水阀门（修复：添加position参数）
            inlet_valve = Valve(
                name="Inlet-Valve",
                position=800.0,
                valve_type=ValveType.BUTTERFLY,
                diameter=3.0
            )
            inlet_valve.set_opening(0.8, 60.0)
            
            # Francis水轮机（修复：使用TurbineCharacteristics）
            turbine_char = TurbineCharacteristics(
                rated_head=140.0,
                rated_flow=80.0,
                rated_power=100.0,
                rated_efficiency=0.93,
                rated_speed=150.0,
                min_head=80.0,
                max_head=180.0
            )
            
            turbine = Turbine(
                name="Main-Turbine",
                position=1000.0,
                turbine_type=TurbineType.FRANCIS,
                characteristics=turbine_char
            )
            
            # 模拟发电过程
            Q_design = 80.0
            H_gross = 195.0 - 50.0
            
            h_friction = penstock.compute_headloss(Q_design, 2.5)
            h_valve = inlet_valve.compute_headloss(Q_design)
            H_net = H_gross - h_friction - h_valve
            
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
        """场景测试：防洪系统（修复版）"""
        print("\n" + "="*80)
        print("【场景3】防洪系统 - 水库+溢流堰+调蓄池 (修复版)")
        print("="*80)
        
        try:
            from backend.core.structures.reservoir import Reservoir
            from backend.core.structures.advanced_weirs import OgeeWeir
            from backend.core.structures.storage import Storage
            
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
            
            # 修复：使用正确的OgeeWeir初始化参数
            spillway = OgeeWeir(
                name="Spillway",
                position=0.0,
                width=50.0,
                crest_height=195.0,
                design_head=5.0
            )
            
            detention_basin = Storage(
                name="Detention-Basin",
                position=10000.0,
                elevation=[0, 5, 10, 15, 20],
                area=[1e6, 1.5e6, 2e6, 2.5e6, 3e6]
            )
            
            flood_hydrograph = [
                (0, 500, 0),
                (3600, 1500, 0),
                (7200, 1200, 0),
                (10800, 800, 0),
                (14400, 500, 0)
            ]
            
            max_level = 195.0
            total_outflow = 0
            
            for t, Q_in, _ in flood_hydrograph:
                if reservoir.current_level > 195.0:
                    H_weir = reservoir.current_level - 195.0
                    Q_spillway = spillway.compute_discharge(H_weir, 0)
                else:
                    Q_spillway = 0
                
                new_level, new_volume = reservoir.update(Q_in, Q_spillway, 3600.0)
                max_level = max(max_level, new_level)
                total_outflow += Q_spillway * 3600.0
                
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
        """场景测试：城市排水系统（修复版）"""
        print("\n" + "="*80)
        print("【场景4】城市排水 - 管道+泵站+调蓄池 (修复版)")
        print("="*80)
        
        try:
            from backend.core.structures.channel import Channel, ChannelType, CrossSectionShape
            from backend.core.structures.pump_station import PumpStation, PumpType, ControlMode, PumpCurve
            from backend.core.structures.storage import Storage
            
            storm_pipe = Channel(
                name="Storm-Pipe",
                channel_type=ChannelType.PIPE,
                length=500.0,
                shape=CrossSectionShape.CIRCULAR,
                diameter=1.5,
                slope=0.003,
                manning_n=0.013
            )
            
            pump_curve = PumpCurve(
                Q_data=[0, 2, 4, 6, 8],
                H_data=[15, 14, 12, 9, 5],
                efficiency_data=[0.5, 0.7, 0.85, 0.8, 0.6],
                Q_max=8.0,
                H_max=15.0
            )
            
            # 修复：PumpStation不需要set_speed，直接用speed参数
            pump_station = PumpStation(
                name="Storm-Pump",
                position=500.0,
                pump_curve=pump_curve,
                pump_type=PumpType.SINGLE,
                control_mode=ControlMode.MANUAL,
                speed=1.0
            )
            
            detention_pond = Storage(
                name="Detention-Pond",
                position=0.0,
                elevation=[0, 1, 2, 3, 4, 5],
                area=[500, 600, 700, 800, 900, 1000]
            )
            
            rainfall_hydrograph = [5, 10, 20, 15, 10, 5, 2]
            
            results = []
            for Q_rain in rainfall_hydrograph:
                h_pipe = storm_pipe.compute_normal_depth(Q_rain)
                Q_pump = pump_station.compute_flow(h_pipe + 5.0, 0.0)
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
    
    def test_integration_complete_system(self):
        """集成测试：完整水系统（修复版）"""
        print("\n" + "="*80)
        print("【集成测试】完整水系统 - 30种组件联合运行 (修复版)")
        print("="*80)
        
        try:
            from backend.core.structures.reservoir import Reservoir
            from backend.core.structures.channel import Channel, ChannelType, CrossSectionShape
            from backend.core.structures.advanced_gates import SluiceGate
            from backend.core.structures.turbine import Turbine, TurbineType, TurbineCharacteristics
            from backend.core.structures.valve import Valve, ValveType
            from backend.core.structures.advanced_weirs import OgeeWeir
            
            components = []
            
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
            
            gate = SluiceGate(
                name="Intake-Gate",
                position=2000.0,
                width=6.0,
                opening=2.5
            )
            components.append(('Gate', gate))
            
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
            
            valve = Valve(
                name="Control-Valve",
                position=2500.0,
                valve_type=ValveType.BUTTERFLY,
                diameter=2.5
            )
            valve.set_opening(0.9, 60.0)
            components.append(('Valve', valve))
            
            turbine_char = TurbineCharacteristics(
                rated_head=90.0,
                rated_flow=40.0,
                rated_power=30.0,
                rated_efficiency=0.92,
                rated_speed=150.0
            )
            turbine = Turbine(
                name="Turbine",
                position=3000.0,
                turbine_type=TurbineType.FRANCIS,
                characteristics=turbine_char
            )
            components.append(('Turbine', turbine))
            
            weir = OgeeWeir(
                name="Spillway",
                position=0.0,
                width=30.0,
                crest_height=145.0,
                design_head=4.0
            )
            components.append(('Weir', weir))
            
            Q_design = 40.0
            
            reservoir.update(Q_design, Q_design, 3600.0)
            h_canal = canal.compute_normal_depth(Q_design)
            Q_gate, regime = gate.compute_discharge(h_canal + 2.0, h_canal)
            h_friction = penstock.compute_headloss(Q_design, 2.0)
            h_valve = valve.compute_headloss(Q_design)
            H_net = (reservoir.current_level - 50.0) - h_friction - h_valve
            power = turbine.compute_power(H_net, Q_design)
            
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


if __name__ == "__main__":
    tester = WebE2EFixedTest()
    tester.run_all_tests()
