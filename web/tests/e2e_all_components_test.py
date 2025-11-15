#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全流程端到端测试 - 30种水工结构
End-to-End Test for All 30 Components

闸泵阀轮+河管渠+库湖池 全覆盖

Author: HydroClaude Team
Date: 2025-11-15
"""

import sys
import os

script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
sys.path.insert(0, project_root)

import traceback
from typing import Dict, List


class E2EAllComponentsTest:
    """全流程端到端测试"""
    
    def __init__(self):
        self.results = {
            'gates': [],      # 闸门
            'pumps': [],      # 泵站
            'valves': [],     # 阀门
            'turbines': [],   # 水轮机
            'channels': [],   # 河管渠
            'reservoirs': [], # 库湖池
            'weirs': [],      # 堰
            'others': []      # 其他
        }
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
    
    def test_component(self, name: str, category: str, test_func) -> bool:
        """测试单个组件"""
        self.total_tests += 1
        
        try:
            test_func()
            self.passed_tests += 1
            self.results[category].append({
                'name': name,
                'status': 'PASS',
                'message': 'OK'
            })
            print(f"  ✅ {name:<30} PASS")
            return True
        except Exception as e:
            self.failed_tests += 1
            error_msg = str(e)
            self.results[category].append({
                'name': name,
                'status': 'FAIL',
                'message': error_msg
            })
            print(f"  ❌ {name:<30} FAIL: {error_msg}")
            # print(f"     {traceback.format_exc()}")
            return False
    
    def test_gates(self):
        """测试闸门系统（5种）"""
        print("\n" + "="*70)
        print("第1批：闸门系统测试（5种）")
        print("="*70)
        
        from backend.core.structures.advanced_gates import (
            SluiceGate, RadialGate, VerticalLiftGate, RollerGate, FlapGate
        )
        
        # 1. SluiceGate
        def test_sluice():
            gate = SluiceGate(
                name="Test-Sluice",
                position=5000.0,
                width=10.0,
                opening=2.0
            )
            Q, regime = gate.compute_discharge(5.0, 3.0)
            assert Q > 0, "流量应为正"
            assert gate.get_status()['type'] == 'SluiceGate'
        
        self.test_component("SluiceGate (滑动闸门)", 'gates', test_sluice)
        
        # 2. RadialGate
        def test_radial():
            gate = RadialGate(
                name="Test-Radial",
                position=5000.0,
                width=12.0,
                opening=3.0,
                radius=8.0
            )
            Q, regime = gate.compute_discharge(6.0, 4.0)
            assert Q > 0
        
        self.test_component("RadialGate (径向闸门)", 'gates', test_radial)
        
        # 3. VerticalLiftGate
        def test_vertical():
            gate = VerticalLiftGate(
                name="Test-Vertical",
                position=5000.0,
                width=10.0,
                opening=2.5
            )
            Q, regime = gate.compute_discharge(6.0, 4.0)
            assert Q > 0
        
        self.test_component("VerticalLiftGate (垂直提升闸门)", 'gates', test_vertical)
        
        # 4. RollerGate
        def test_roller():
            gate = RollerGate(
                name="Test-Roller",
                position=5000.0,
                width=15.0,
                opening=4.0
            )
            Q, regime = gate.compute_discharge(7.0, 5.0)
            assert Q > 0
        
        self.test_component("RollerGate (滚轮闸门)", 'gates', test_roller)
        
        # 5. FlapGate
        def test_flap():
            gate = FlapGate(
                name="Test-Flap",
                position=5000.0,
                width=8.0,
                opening=3.0,
                height=3.0,
                target_level=102.0
            )
            Q, regime = gate.compute_discharge(6.0, 4.0)
            assert Q >= 0
        
        self.test_component("FlapGate (翻板闸门)", 'gates', test_flap)
    
    def test_pumps(self):
        """测试泵站系统（1种）"""
        print("\n" + "="*70)
        print("第2批：泵站系统测试（1种）")
        print("="*70)
        
        from backend.core.structures.pump_station import (
            PumpStation, PumpType, ControlMode, PumpCurve
        )
        
        def test_pump_station():
            pump_curve = PumpCurve(
                Q_data=[0, 5, 10, 15],
                H_data=[25, 23, 18, 10],
                efficiency_data=[0.6, 0.8, 0.85, 0.7],
                Q_max=15.0,
                H_max=25.0
            )
            
            station = PumpStation(
                name="Test-Pump",
                position=1000.0,
                pump_curve=pump_curve,
                pump_type=PumpType.SINGLE,
                control_mode=ControlMode.MANUAL
            )
            station.set_speed(1.0)
            Q = station.compute_flow(10.0, 5.0)
            assert Q >= 0
        
        self.test_component("PumpStation (泵站)", 'pumps', test_pump_station)
    
    def test_valves(self):
        """测试阀门系统（7种）"""
        print("\n" + "="*70)
        print("第3批：阀门系统测试（7种）")
        print("="*70)
        
        from backend.core.structures.valve import Valve, ValveType
        
        valve_types = [
            (ValveType.BUTTERFLY, "Butterfly (蝶阀)"),
            (ValveType.BALL, "Ball (球阀)"),
            (ValveType.GATE, "Gate (闸阀)"),
            (ValveType.GLOBE, "Globe (截止阀)"),
            (ValveType.CHECK, "Check (止回阀)"),
            (ValveType.NEEDLE, "Needle (针阀)"),
            (ValveType.CONE, "Cone (锥阀)")
        ]
        
        for valve_type, name in valve_types:
            def test_valve_func(vt=valve_type):
                valve = Valve(
                    name=f"Test-{vt.value}",
                    valve_type=vt,
                    diameter=0.5,
                    max_pressure=50.0
                )
                valve.set_opening(0.8, 10.0)
                Cv = valve.get_flow_coefficient()
                assert 0 <= Cv <= 1.0
                h_loss = valve.compute_headloss(5.0)
                assert h_loss >= 0
            
            self.test_component(name, 'valves', test_valve_func)
    
    def test_turbines(self):
        """测试水轮机系统（3类型）"""
        print("\n" + "="*70)
        print("第4批：水轮机系统测试（3类型）")
        print("="*70)
        
        from backend.core.structures.turbine import Turbine, TurbineType
        
        turbine_types = [
            (TurbineType.FRANCIS, "Francis (混流式)", 200.0, 50.0),
            (TurbineType.KAPLAN, "Kaplan (轴流式)", 20.0, 80.0),
            (TurbineType.PELTON, "Pelton (冲击式)", 500.0, 30.0)
        ]
        
        for turb_type, name, head, flow in turbine_types:
            def test_turbine_func(tt=turb_type, h=head, q=flow):
                turbine = Turbine(
                    name=f"Test-{tt.value}",
                    turbine_type=tt,
                    rated_head=h,
                    rated_flow=q,
                    rated_power=h * q * 9.81 * 0.9 / 1000
                )
                eff = turbine.compute_efficiency(h, q)
                assert 0 < eff <= 1.0
                power = turbine.compute_power(h, q)
                assert power >= 0
            
            self.test_component(name, 'turbines', test_turbine_func)
    
    def test_channels(self):
        """测试河管渠系统（5种）"""
        print("\n" + "="*70)
        print("第5批：河管渠系统测试（5种）⭐新增")
        print("="*70)
        
        from backend.core.structures.channel import (
            Channel, ChannelType, CrossSectionShape
        )
        
        channel_configs = [
            (ChannelType.RIVER, "River (天然河道)", CrossSectionShape.NATURAL),
            (ChannelType.CANAL, "Canal (人工渠道)", CrossSectionShape.TRAPEZOIDAL),
            (ChannelType.PIPE, "Pipe (压力管道)", CrossSectionShape.CIRCULAR),
            (ChannelType.TUNNEL, "Tunnel (隧洞)", CrossSectionShape.CIRCULAR),
            (ChannelType.PENSTOCK, "Penstock (压力钢管)", CrossSectionShape.CIRCULAR)
        ]
        
        for ch_type, name, shape in channel_configs:
            def test_channel_func(ct=ch_type, s=shape):
                if s == CrossSectionShape.CIRCULAR:
                    channel = Channel(
                        name=f"Test-{ct.value}",
                        channel_type=ct,
                        length=1000.0,
                        shape=s,
                        diameter=2.0,
                        slope=0.001,
                        manning_n=0.015
                    )
                elif s == CrossSectionShape.TRAPEZOIDAL:
                    channel = Channel(
                        name=f"Test-{ct.value}",
                        channel_type=ct,
                        length=1000.0,
                        shape=s,
                        width=5.0,
                        depth=3.0,
                        side_slope=1.5,
                        slope=0.001,
                        manning_n=0.025
                    )
                else:  # NATURAL
                    channel = Channel(
                        name=f"Test-{ct.value}",
                        channel_type=ct,
                        length=1000.0,
                        shape=CrossSectionShape.RECTANGULAR,
                        width=10.0,
                        depth=5.0,
                        slope=0.0005,
                        manning_n=0.030
                    )
                
                Q = 10.0
                h_n = channel.compute_normal_depth(Q)
                assert h_n > 0
                h_c = channel.compute_critical_depth(Q)
                assert h_c > 0
            
            self.test_component(name, 'channels', test_channel_func)
    
    def test_reservoirs(self):
        """测试库湖池系统（3种）"""
        print("\n" + "="*70)
        print("第6批：库湖池系统测试（3种）⭐新增")
        print("="*70)
        
        # 1. Reservoir
        def test_reservoir():
            from backend.core.structures.reservoir import Reservoir
            
            elevation = [100, 110, 120, 130, 140, 150]
            area = [1e6, 2e6, 3.5e6, 5e6, 7e6, 9e6]
            
            reservoir = Reservoir(
                name="Test-Reservoir",
                dead_level=110.0,
                normal_level=140.0,
                flood_limit_level=135.0,
                design_flood_level=145.0,
                check_flood_level=150.0,
                elevation=elevation,
                area=area,
                initial_level=130.0
            )
            
            # 测试水位-容积
            V = reservoir.get_volume(130.0)
            assert V > 0
            
            # 测试水量平衡
            new_level, new_volume = reservoir.update(100.0, 50.0, 3600.0)
            assert new_level > 130.0
            
            # 测试特征库容
            char_vol = reservoir.get_characteristic_volumes()
            assert 'active_storage' in char_vol
        
        self.test_component("Reservoir (水库)", 'reservoirs', test_reservoir)
        
        # 2. Lake (使用相同的Reservoir类)
        def test_lake():
            from backend.core.structures.reservoir import Reservoir
            
            elevation = [200, 205, 210, 215, 220]
            area = [5e6, 6e6, 7e6, 8e6, 9e6]
            
            lake = Reservoir(
                name="Test-Lake",
                dead_level=200.0,
                normal_level=210.0,
                flood_limit_level=215.0,
                design_flood_level=220.0,
                check_flood_level=222.0,
                elevation=elevation,
                area=area,
                initial_level=210.0
            )
            
            V = lake.get_volume(210.0)
            assert V > 0
        
        self.test_component("Lake (湖泊)", 'reservoirs', test_lake)
        
        # 3. Storage Basin
        def test_storage():
            from backend.core.structures.storage import Storage
            
            elevation = [0, 2, 4, 6, 8, 10]
            area = [100, 200, 300, 400, 500, 600]
            
            storage = Storage(
                name="Test-Basin",
                elevation=elevation,
                area=area,
                initial_volume=1000.0
            )
            
            # 测试溢流
            Q_spill = storage.compute_spillway_flow(8.0, 6.0, 5.0)
            assert Q_spill >= 0
            
            # 测试调蓄
            new_elev = storage.route(50.0, 20.0, 3600.0)
            assert new_elev > 0
        
        self.test_component("Storage Basin (调蓄池)", 'reservoirs', test_storage)
    
    def test_weirs(self):
        """测试堰系统（6种）"""
        print("\n" + "="*70)
        print("第7批：堰系统测试（6种）")
        print("="*70)
        
        from backend.core.structures.advanced_weirs import (
            SharpCrestedWeir, BroadCrestedWeir, VNotchWeir,
            RectangularWeir, TrapezoidalWeir, OgeeWeir
        )
        
        weir_configs = [
            (SharpCrestedWeir, "SharpCrestedWeir (尖顶堰)", {'name': 'Test-Sharp', 'width': 5.0, 'crest_elevation': 100.0}),
            (BroadCrestedWeir, "BroadCrestedWeir (宽顶堰)", {'name': 'Test-Broad', 'width': 8.0, 'crest_elevation': 100.0, 'crest_length': 2.0}),
            (VNotchWeir, "VNotchWeir (V型堰)", {'name': 'Test-V', 'angle': 90.0, 'crest_elevation': 100.0}),
            (RectangularWeir, "RectangularWeir (矩形堰)", {'name': 'Test-Rect', 'width': 6.0, 'crest_elevation': 100.0}),
            (TrapezoidalWeir, "TrapezoidalWeir (梯形堰)", {'name': 'Test-Trap', 'bottom_width': 5.0, 'side_slope': 1.0, 'crest_elevation': 100.0}),
            (OgeeWeir, "OgeeWeir (溢流堰)", {'name': 'Test-Ogee', 'width': 10.0, 'crest_elevation': 100.0, 'design_head': 3.0})
        ]
        
        for weir_class, name, kwargs in weir_configs:
            def test_weir_func(wc=weir_class, kw=kwargs):
                weir = wc(position=5000.0, **kw)
                # 使用水头而不是水深
                Q = weir.compute_discharge(3.0, 1.0)
                assert Q >= 0
            
            self.test_component(name, 'weirs', test_weir_func)
    
    def test_others(self):
        """测试其他辅助结构（6种）"""
        print("\n" + "="*70)
        print("第8批：其他辅助结构测试（6种）")
        print("="*70)
        
        # 1. Culvert
        def test_culvert():
            from backend.core.structures.culvert import Culvert, CulvertType
            culvert = Culvert(
                name="Test-Culvert",
                culvert_type=CulvertType.CIRCULAR,
                diameter=1.5,
                length=50.0,
                inlet_elevation=100.0,
                outlet_elevation=99.5,
                manning_n=0.013
            )
            Q = culvert.compute_discharge(102.0, 101.0)
            assert Q >= 0
        
        self.test_component("Culvert (涵洞)", 'others', test_culvert)
        
        # 2. Side Weir
        def test_side_weir():
            from backend.core.structures.side_weir import SideWeir
            side_weir = SideWeir(
                name="Test-SideWeir",
                position=5000.0,
                length=20.0,
                crest_elevation=100.0,
                channel_width=10.0
            )
            Q_div, Q_main = side_weir.compute_discharge(30.0, 102.0, 10.0, 0.001)
            assert Q_div >= 0
            assert Q_main >= 0
        
        self.test_component("Side Weir (侧堰)", 'others', test_side_weir)
        
        # 3. Drop Structure
        def test_drop():
            from backend.core.structures.drop_structure import DropStructure
            drop = DropStructure(
                name="Test-Drop",
                position=5000.0,
                drop_height=2.0,
                channel_width=8.0
            )
            h_c = drop.compute_critical_depth(20.0)
            assert h_c > 0
            E_loss = drop.compute_energy_loss(20.0, 3.0, 2.0)
            assert E_loss >= 0
        
        self.test_component("Drop Structure (跌水)", 'others', test_drop)
        
        # 4. Bridge
        def test_bridge():
            from backend.core.structures.bridge import Bridge
            bridge = Bridge(
                name="Test-Bridge",
                position=5000.0,
                bridge_length=30.0,
                deck_elevation=110.0,
                num_piers=2,
                pier_width=1.0,
                channel_width=20.0
            )
            Q = bridge.compute_discharge(105.0, 104.0, 20.0)
            assert Q >= 0
        
        self.test_component("Bridge (桥梁)", 'others', test_bridge)
        
        # 5. Surge Tank
        def test_surge_tank():
            from backend.core.structures.surge_tank import SurgeTank, SurgeTankType
            tank = SurgeTank(
                name="Test-SurgeTank",
                tank_type=SurgeTankType.SIMPLE,
                cross_section_area=50.0,
                initial_level=100.0
            )
            tank.update(10.0, 3600.0)
            assert tank.current_level != 100.0
        
        self.test_component("Surge Tank (调压井)", 'others', test_surge_tank)
        
        # 6. Hydropower Station
        def test_hydropower():
            from backend.core.structures.hydropower_station import (
                HydropowerStation, HydropowerConfig
            )
            from backend.core.structures.turbine import Turbine, TurbineType
            
            turbine = Turbine(
                name="Test-Turbine",
                turbine_type=TurbineType.FRANCIS,
                rated_head=100.0,
                rated_flow=50.0,
                rated_power=40.0
            )
            
            config = HydropowerConfig(
                gross_head=120.0,
                penstock_length=500.0,
                penstock_diameter=2.5
            )
            
            station = HydropowerStation(
                name="Test-Station",
                turbines=[turbine],
                config=config
            )
            
            net_head = station.compute_net_head(50.0)
            assert net_head > 0
            power = station.compute_station_output(50.0)
            assert power >= 0
        
        self.test_component("Hydropower Station (水电站)", 'others', test_hydropower)
    
    def test_integration(self):
        """集成测试：完整水系统"""
        print("\n" + "="*70)
        print("第9批：系统集成测试")
        print("="*70)
        
        def test_full_system():
            """
            测试完整水系统：
            水库 → 渠道 → 闸门 → 管道 → 水轮机 → 尾水
            """
            from backend.core.structures.reservoir import Reservoir
            from backend.core.structures.channel import Channel, ChannelType, CrossSectionShape
            from backend.core.structures.advanced_gates import SluiceGate
            from backend.core.structures.turbine import Turbine, TurbineType
            
            # 1. 水库
            reservoir = Reservoir(
                name="Upstream-Reservoir",
                dead_level=100.0,
                normal_level=150.0,
                flood_limit_level=145.0,
                design_flood_level=155.0,
                check_flood_level=160.0,
                elevation=[100, 120, 140, 150, 160],
                area=[1e6, 2e6, 3e6, 4e6, 5e6],
                initial_level=145.0
            )
            
            # 2. 引水渠道
            canal = Channel(
                name="Intake-Canal",
                channel_type=ChannelType.CANAL,
                length=2000.0,
                shape=CrossSectionShape.TRAPEZOIDAL,
                width=10.0,
                depth=5.0,
                side_slope=1.5,
                slope=0.001,
                manning_n=0.025
            )
            
            # 3. 进水闸门
            gate = SluiceGate(
                position=2000.0,
                width=8.0,
                sill_elevation=140.0,
                opening=3.0,
                max_opening=5.0
            )
            
            # 4. 压力钢管
            penstock = Channel(
                name="Penstock",
                channel_type=ChannelType.PENSTOCK,
                length=500.0,
                shape=CrossSectionShape.CIRCULAR,
                diameter=2.5,
                slope=0.2,
                manning_n=0.012
            )
            
            # 5. 水轮机
            turbine = Turbine(
                name="Main-Turbine",
                turbine_type=TurbineType.FRANCIS,
                rated_head=100.0,
                rated_flow=50.0,
                rated_power=40.0
            )
            
            # 测试流程
            Q_design = 50.0
            
            # 水库出流
            reservoir.update(Q_design, Q_design, 3600.0)
            assert reservoir.current_level > 100.0
            
            # 渠道输水
            h_normal = canal.compute_normal_depth(Q_design)
            assert h_normal > 0
            
            # 闸门控制
            Q_gate = gate.compute_discharge(145.0, 140.0)
            assert Q_gate > 0
            
            # 管道损失
            h_loss = penstock.compute_headloss(Q_design, 2.0)
            assert h_loss >= 0
            
            # 水轮机发电
            power = turbine.compute_power(100.0, Q_design)
            assert power > 0
            
            print(f"    水库水位: {reservoir.current_level:.2f}m")
            print(f"    渠道水深: {h_normal:.2f}m")
            print(f"    闸门流量: {Q_gate:.2f}m³/s")
            print(f"    管道损失: {h_loss:.2f}m")
            print(f"    发电功率: {power:.2f}MW")
        
        self.test_component("Full System Integration (完整系统)", 'others', test_full_system)
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "🎯"*35)
        print("全流程端到端测试开始".center(70))
        print("30种水工结构 - 闸泵阀轮+河管渠+库湖池".center(70))
        print("🎯"*35)
        
        # 运行各批次测试
        self.test_gates()        # 5种
        self.test_pumps()        # 1种
        self.test_valves()       # 7种
        self.test_turbines()     # 3种
        self.test_channels()     # 5种 ⭐新增
        self.test_reservoirs()   # 3种 ⭐新增
        self.test_weirs()        # 6种
        self.test_others()       # 6种 + 1集成
        self.test_integration()  # 系统集成
        
        # 生成测试报告
        self.generate_report()
    
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "="*70)
        print("测试报告".center(70))
        print("="*70)
        
        # 分类统计
        print("\n分类统计:")
        print("-"*70)
        print(f"{'类别':<20} {'总数':<10} {'通过':<10} {'失败':<10} {'通过率':<10}")
        print("-"*70)
        
        for category, name in [
            ('gates', '闸门'),
            ('pumps', '泵站'),
            ('valves', '阀门'),
            ('turbines', '水轮机'),
            ('channels', '河管渠 ⭐'),
            ('reservoirs', '库湖池 ⭐'),
            ('weirs', '堰'),
            ('others', '其他')
        ]:
            results = self.results[category]
            total = len(results)
            passed = sum(1 for r in results if r['status'] == 'PASS')
            failed = total - passed
            rate = f"{passed/total*100:.1f}%" if total > 0 else "N/A"
            
            print(f"{name:<20} {total:<10} {passed:<10} {failed:<10} {rate:<10}")
        
        print("-"*70)
        print(f"{'总计':<20} {self.total_tests:<10} {self.passed_tests:<10} {self.failed_tests:<10} {self.passed_tests/self.total_tests*100:.1f}%")
        print("="*70)
        
        # 失败详情
        if self.failed_tests > 0:
            print("\n失败测试详情:")
            print("-"*70)
            for category, results in self.results.items():
                for result in results:
                    if result['status'] == 'FAIL':
                        print(f"❌ [{category}] {result['name']}")
                        print(f"   {result['message']}")
        
        # 最终结论
        print("\n" + "🎉"*35)
        if self.failed_tests == 0:
            print("✅ 所有测试通过！30种组件全部正常！".center(70))
            print("闸泵阀轮+河管渠+库湖池 全覆盖 ✅".center(70))
        else:
            print(f"⚠️  {self.failed_tests}个测试失败，需要修复".center(70))
        print("🎉"*35)


if __name__ == "__main__":
    tester = E2EAllComponentsTest()
    tester.run_all_tests()
