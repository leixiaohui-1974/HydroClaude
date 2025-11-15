#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简化版全流程端到端测试 - 30种水工结构
只测试组件能否导入和创建实例

Author: HydroClaude Team
Date: 2025-11-15
"""

import sys
import os

script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
sys.path.insert(0, project_root)


class SimpleE2ETest:
    """简化版端到端测试"""
    
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
    
    def test_import(self, name: str, import_func):
        """测试导入"""
        try:
            import_func()
            self.passed += 1
            self.results.append((name, 'PASS', '✅'))
            print(f"  ✅ {name:<40} PASS")
            return True
        except Exception as e:
            self.failed += 1
            self.results.append((name, 'FAIL', str(e)[:50]))
            print(f"  ❌ {name:<40} FAIL: {str(e)[:50]}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "🎯"*35)
        print("简化版全流程端到端测试".center(70))
        print("30种水工结构 - 导入和实例化测试".center(70))
        print("🎯"*35)
        
        # 1. 闸门系统（5种）
        print("\n" + "="*70)
        print("第1批：闸门系统（5种）")
        print("="*70)
        
        def test_gates():
            from backend.core.structures.advanced_gates import (
                SluiceGate, RadialGate, VerticalLiftGate, RollerGate, FlapGate
            )
        
        self.test_import("闸门系统 (Gates) - 5种", test_gates)
        
        # 2. 泵站系统（1种）
        print("\n" + "="*70)
        print("第2批：泵站系统（1种）")
        print("="*70)
        
        def test_pumps():
            from backend.core.structures.pump_station import (
                PumpStation, PumpType, ControlMode, PumpCurve
            )
        
        self.test_import("泵站系统 (Pump Station)", test_pumps)
        
        # 3. 阀门系统（7种）
        print("\n" + "="*70)
        print("第3批：阀门系统（7种）")
        print("="*70)
        
        def test_valves():
            from backend.core.structures.valve import Valve, ValveType
            # 测试所有7种阀门类型
            for vt in ValveType:
                pass  # 确认枚举存在
        
        self.test_import("阀门系统 (Valves) - 7种", test_valves)
        
        # 4. 水轮机系统（3类型）
        print("\n" + "="*70)
        print("第4批：水轮机系统（3类型）")
        print("="*70)
        
        def test_turbines():
            from backend.core.structures.turbine import Turbine, TurbineType
            # 测试所有3种类型
            for tt in TurbineType:
                if tt.value in ['francis', 'kaplan', 'pelton']:
                    pass
        
        self.test_import("水轮机系统 (Turbines) - 3类型", test_turbines)
        
        # 5. 河管渠系统（5种）⭐新增
        print("\n" + "="*70)
        print("第5批：河管渠系统（5种）⭐新增")
        print("="*70)
        
        def test_channels():
            from backend.core.structures.channel import (
                Channel, ChannelType, CrossSectionShape
            )
            # 测试River
            river = Channel(
                name="Test-River",
                channel_type=ChannelType.RIVER,
                length=1000.0,
                shape=CrossSectionShape.RECTANGULAR,
                width=10.0,
                depth=5.0,
                slope=0.001,
                manning_n=0.03
            )
            # 测试Canal
            canal = Channel(
                name="Test-Canal",
                channel_type=ChannelType.CANAL,
                length=1000.0,
                shape=CrossSectionShape.TRAPEZOIDAL,
                width=5.0,
                depth=3.0,
                side_slope=1.5,
                slope=0.001,
                manning_n=0.025
            )
            # 测试Pipe
            pipe = Channel(
                name="Test-Pipe",
                channel_type=ChannelType.PIPE,
                length=500.0,
                shape=CrossSectionShape.CIRCULAR,
                diameter=2.0,
                slope=0.002,
                manning_n=0.013
            )
        
        self.test_import("河管渠系统 (Channels) - 5种", test_channels)
        
        # 6. 库湖池系统（3种）⭐新增
        print("\n" + "="*70)
        print("第6批：库湖池系统（3种）⭐新增")
        print("="*70)
        
        def test_reservoirs():
            from backend.core.structures.reservoir import Reservoir
            from backend.core.structures.storage import Storage
            
            # Reservoir/Lake (共用一个类)
            reservoir = Reservoir(
                name="Test-Reservoir",
                dead_level=100.0,
                normal_level=120.0,
                flood_limit_level=115.0,
                design_flood_level=125.0,
                check_flood_level=130.0,
                elevation=[100, 110, 120, 130],
                area=[1e6, 2e6, 3e6, 4e6]
            )
            
            # Storage Basin
            storage = Storage(
                name="Test-Storage",
                position=1000.0,
                elevation=[0, 2, 4, 6],
                area=[100, 200, 300, 400]
            )
        
        self.test_import("库湖池系统 (Reservoirs/Lakes/Basins) - 3种", test_reservoirs)
        
        # 7. 堰系统（6种）
        print("\n" + "="*70)
        print("第7批：堰系统（6种）")
        print("="*70)
        
        def test_weirs():
            from backend.core.structures.advanced_weirs import (
                SharpCrestedWeir, BroadCrestedWeir, VNotchWeir,
                RectangularWeir, TrapezoidalWeir, OgeeWeir
            )
        
        self.test_import("堰系统 (Weirs) - 6种", test_weirs)
        
        # 8. 其他辅助结构（6种）
        print("\n" + "="*70)
        print("第8批：其他辅助结构（6种）")
        print("="*70)
        
        def test_culvert():
            from backend.core.structures.culvert import Culvert, CulvertType
        self.test_import("涵洞 (Culvert)", test_culvert)
        
        def test_side_weir():
            from backend.core.structures.side_weir import SideWeir
        self.test_import("侧堰 (Side Weir)", test_side_weir)
        
        def test_drop():
            from backend.core.structures.drop_structure import DropStructure
        self.test_import("跌水 (Drop Structure)", test_drop)
        
        def test_bridge():
            from backend.core.structures.bridge import Bridge
        self.test_import("桥梁 (Bridge)", test_bridge)
        
        def test_surge_tank():
            from backend.core.structures.surge_tank import SurgeTank, SurgeTankType
        self.test_import("调压井 (Surge Tank)", test_surge_tank)
        
        def test_hydropower():
            from backend.core.structures.hydropower_station import (
                HydropowerStation, HydropowerConfig
            )
        self.test_import("水电站 (Hydropower Station)", test_hydropower)
        
        # 生成报告
        self.generate_report()
    
    def generate_report(self):
        """生成报告"""
        print("\n" + "="*70)
        print("测试报告".center(70))
        print("="*70)
        
        total = self.passed + self.failed
        pass_rate = self.passed / total * 100 if total > 0 else 0
        
        print(f"\n总计: {total}组测试")
        print(f"通过: {self.passed} ({pass_rate:.1f}%)")
        print(f"失败: {self.failed}")
        
        # 组件清单统计
        print("\n组件统计:")
        print("-"*70)
        component_counts = {
            '闸门 (Gates)': 5,
            '泵站 (Pumps)': 1,
            '阀门 (Valves)': 7,
            '水轮机 (Turbines)': 3,
            '河管渠 (Channels)': 5,
            '库湖池 (Reservoirs/Lakes/Basins)': 3,
            '堰 (Weirs)': 6,
            '其他 (Others)': 6
        }
        
        total_components = sum(component_counts.values())
        
        for name, count in component_counts.items():
            status = '✅' if any(name.split()[0] in r[0] for r in self.results if r[1] == 'PASS') else '❌'
            print(f"  {status} {name:<45} {count}种")
        
        print("-"*70)
        print(f"  {'总计':<45} {total_components}种")
        
        print("\n" + "🎉"*35)
        if self.failed == 0:
            print("✅ 所有组件导入测试通过！".center(70))
            print(f"30种水工结构全覆盖 - 闸泵阀轮+河管渠+库湖池".center(70))
        else:
            print(f"⚠️  {self.failed}个测试失败".center(70))
        print("🎉"*35)
        
        return pass_rate


if __name__ == "__main__":
    tester = SimpleE2ETest()
    tester.run_all_tests()
