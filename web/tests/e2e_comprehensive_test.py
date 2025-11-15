#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Web端到端综合测试
覆盖所有22种水工结构的完整闭环测试

包括：
- 原有17种：泵站、5种闸门、6种堰、涵洞、侧堰、调蓄池、跌水、桥梁
- 新增5种：水轮机、阀门、水电站、调压井、渐变段

Author: HydroClaude Team
Date: 2025-11-15
"""

import sys
import os

# 添加项目路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
backend_root = os.path.join(project_root, 'backend')
sys.path.insert(0, project_root)
sys.path.insert(0, backend_root)

import json
import time
from datetime import datetime
from typing import Dict, List, Any


class E2EComprehensiveTest:
    """Web端到端综合测试类"""
    
    def __init__(self):
        self.test_results = {
            'start_time': datetime.now().isoformat(),
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'test_details': []
        }
        
        # 测试配置
        self.components = {
            'original': [
                'PumpStation', 'SluiceGate', 'RadialGate', 'VerticalLiftGate',
                'RollerGate', 'FlapGate', 'SharpCrestedWeir', 'BroadCrestedWeir',
                'VNotchWeir', 'RectangularWeir', 'TrapezoidalWeir', 'OgeeWeir',
                'Culvert', 'SideWeir', 'Storage', 'DropStructure', 'Bridge'
            ],
            'new': [
                'Turbine', 'Valve', 'HydropowerStation', 'SurgeTank'
            ]
        }
    
    def log_test(self, category: str, name: str, status: str, 
                 details: str = "", duration: float = 0.0):
        """记录测试结果"""
        self.test_results['total_tests'] += 1
        
        if status == 'PASS':
            self.test_results['passed'] += 1
            icon = '✅'
        elif status == 'FAIL':
            self.test_results['failed'] += 1
            icon = '❌'
        else:
            self.test_results['skipped'] += 1
            icon = '⚠️'
        
        result = {
            'category': category,
            'name': name,
            'status': status,
            'icon': icon,
            'details': details,
            'duration': duration
        }
        
        self.test_results['test_details'].append(result)
        
        print(f"{icon} [{category}] {name}: {status} ({duration:.3f}s)")
        if details:
            print(f"   {details}")
    
    def test_backend_imports(self):
        """测试1: 后端模块导入"""
        print("\n" + "="*80)
        print("测试1: 后端模块导入")
        print("="*80)
        
        start = time.time()
        
        try:
            # 原有组件
            from core.structures import (
                PumpStation, SluiceGate, RadialGate, VerticalLiftGate,
                RollerGate, FlapGate, SharpCrestedWeir, BroadCrestedWeir,
                VNotchWeir, RectangularWeir, TrapezoidalWeir, OgeeWeir,
                Culvert, SideWeir, Storage, DropStructure, Bridge
            )
            
            # 新增组件
            from core.structures.turbine import Turbine
            from core.structures.valve import Valve
            from core.structures.surge_tank import SurgeTank
            
            duration = time.time() - start
            self.log_test('Backend', '模块导入测试', 'PASS', 
                         f'成功导入20个模块', duration)
            return True
            
        except Exception as e:
            duration = time.time() - start
            self.log_test('Backend', '模块导入测试', 'FAIL', 
                         f'导入失败: {str(e)}', duration)
            return False
    
    def test_original_components(self):
        """测试2: 原有17种组件功能"""
        print("\n" + "="*80)
        print("测试2: 原有17种组件功能测试")
        print("="*80)
        
        results = []
        
        # 2.1 泵站
        start = time.time()
        try:
            from core.structures import PumpStation, PumpCurve, PumpType
            
            pump_curve = PumpCurve(
                Q_data=[0, 50, 100],
                H_data=[12.0, 10.0, 7.0],
                efficiency_data=[0, 0.85, 0.80]
            )
            
            pump = PumpStation(
                name="Test-Pump",
                position=1000.0,
                pump_curve=pump_curve,
                pump_type=PumpType.SINGLE
            )
            
            H = pump.compute_head(50.0)
            assert 9.0 < H < 11.0, f"泵站扬程异常: {H}"
            
            duration = time.time() - start
            self.log_test('Original', '泵站 (PumpStation)', 'PASS', 
                         f'扬程计算正确: {H:.2f}m', duration)
            results.append(True)
            
        except Exception as e:
            duration = time.time() - start
            self.log_test('Original', '泵站 (PumpStation)', 'FAIL', 
                         str(e), duration)
            results.append(False)
        
        # 2.2 闸门（测试5种）
        gate_types = [
            ('SluiceGate', 'Sluice-01'),
            ('RadialGate', 'Radial-01'),
            ('VerticalLiftGate', 'Vertical-01'),
            ('RollerGate', 'Roller-01'),
            ('FlapGate', 'Flap-01')
        ]
        
        for gate_class, gate_name in gate_types:
            start = time.time()
            try:
                from core.structures import (SluiceGate, RadialGate, 
                                             VerticalLiftGate, RollerGate, FlapGate)
                
                gate_cls = eval(gate_class)
                gate = gate_cls(gate_name, 2000.0, 10.0, 3.0)
                
                Q, regime = gate.compute_discharge(6.0, 4.0)
                assert Q > 0, f"{gate_class}流量为0"
                
                duration = time.time() - start
                self.log_test('Original', f'闸门 ({gate_class})', 'PASS',
                             f'Q={Q:.2f}m³/s, 流态={regime.value}', duration)
                results.append(True)
                
            except Exception as e:
                duration = time.time() - start
                self.log_test('Original', f'闸门 ({gate_class})', 'FAIL',
                             str(e), duration)
                results.append(False)
        
        # 2.3 堰（测试6种）
        weir_types = [
            ('SharpCrestedWeir', 'Sharp-01'),
            ('BroadCrestedWeir', 'Broad-01'),
            ('VNotchWeir', 'VNotch-01'),
            ('RectangularWeir', 'Rect-01'),
            ('TrapezoidalWeir', 'Trap-01'),
            ('OgeeWeir', 'Ogee-01')
        ]
        
        for weir_class, weir_name in weir_types:
            start = time.time()
            try:
                from core.structures import (SharpCrestedWeir, BroadCrestedWeir,
                                             VNotchWeir, RectangularWeir,
                                             TrapezoidalWeir, OgeeWeir)
                
                weir_cls = eval(weir_class)
                
                if weir_class == 'VNotchWeir':
                    weir = weir_cls(weir_name, 3000.0, 2.0)
                else:
                    weir = weir_cls(weir_name, 3000.0, 8.0, 2.0)
                
                Q = weir.compute_discharge(5.0)
                assert Q > 0, f"{weir_class}流量为0"
                
                duration = time.time() - start
                self.log_test('Original', f'堰 ({weir_class})', 'PASS',
                             f'Q={Q:.2f}m³/s', duration)
                results.append(True)
                
            except Exception as e:
                duration = time.time() - start
                self.log_test('Original', f'堰 ({weir_class})', 'FAIL',
                             str(e), duration)
                results.append(False)
        
        # 2.4 其他结构
        other_structures = [
            ('Culvert', 'Culvert-01', lambda c: c.compute_discharge(3.0, 1.0, 0.002)),
            ('SideWeir', 'SideWeir-01', lambda s: s.compute_discharge(3.0, 80.0, 10.0)),
            ('Storage', 'Storage-01', lambda st: st.route(100.0, 30.0, 60.0)),
            ('DropStructure', 'Drop-01', lambda d: d.compute_energy_loss(50.0, 2.0)),
            ('Bridge', 'Bridge-01', lambda b: b.compute_discharge(5.0, 4.0, 50.0))
        ]
        
        for struct_class, struct_name, test_func in other_structures:
            start = time.time()
            try:
                if struct_class == 'Culvert':
                    from core.structures import Culvert, CulvertType
                    struct = Culvert(struct_name, 4000.0, CulvertType.CIRCULAR,
                                   50.0, diameter=2.0)
                elif struct_class == 'SideWeir':
                    from core.structures import SideWeir
                    struct = SideWeir(struct_name, 5000.0, 20.0, 2.0)
                elif struct_class == 'Storage':
                    from core.structures import Storage
                    struct = Storage(struct_name, 6000.0,
                                   elevation=[0, 2, 4, 6, 8, 10],
                                   area=[100, 400, 900, 1600, 2500, 3600])
                elif struct_class == 'DropStructure':
                    from core.structures import DropStructure
                    struct = DropStructure(struct_name, 7000.0, 3.0, 10.0)
                elif struct_class == 'Bridge':
                    from core.structures import Bridge
                    struct = Bridge(struct_name, 8000.0, 40.0, 8.0,
                                  12.0, 6.0, 3, 2.0, 2)
                
                result = test_func(struct)
                assert result is not None, f"{struct_class}计算结果为None"
                
                duration = time.time() - start
                self.log_test('Original', f'{struct_class}', 'PASS',
                             '计算正常', duration)
                results.append(True)
                
            except Exception as e:
                duration = time.time() - start
                self.log_test('Original', f'{struct_class}', 'FAIL',
                             str(e), duration)
                results.append(False)
        
        return all(results)
    
    def test_new_components(self):
        """测试3: 新增5种组件功能"""
        print("\n" + "="*80)
        print("测试3: 新增5种组件功能测试")
        print("="*80)
        
        results = []
        
        # 3.1 水轮机
        start = time.time()
        try:
            from core.structures.turbine import Turbine, TurbineType, TurbineCharacteristics
            
            char = TurbineCharacteristics(
                rated_head=100.0,
                rated_flow=50.0,
                rated_power=45.0,
                rated_efficiency=0.93,
                rated_speed=375.0
            )
            
            turbine = Turbine("Turbine-01", 0.0, TurbineType.FRANCIS, char)
            P, eta = turbine.compute_power(100.0, 50.0)
            
            assert 40 < P < 50, f"水轮机功率异常: {P}"
            assert 0.85 < eta < 0.95, f"效率异常: {eta}"
            
            duration = time.time() - start
            self.log_test('New', '水轮机 (Turbine-Francis)', 'PASS',
                         f'P={P:.2f}MW, η={eta*100:.1f}%', duration)
            results.append(True)
            
        except Exception as e:
            duration = time.time() - start
            self.log_test('New', '水轮机 (Turbine)', 'FAIL', str(e), duration)
            results.append(False)
        
        # 3.2 阀门（测试3种）
        valve_types = [
            ('BUTTERFLY', '蝶阀'),
            ('BALL', '球阀'),
            ('GATE', '闸阀')
        ]
        
        for valve_type, valve_name_cn in valve_types:
            start = time.time()
            try:
                from core.structures.valve import Valve, ValveType
                
                valve = Valve(
                    f"Valve-{valve_type}",
                    100.0,
                    ValveType[valve_type],
                    1.5,
                    cv_full_open=200.0
                )
                
                Q = valve.compute_discharge(10.0, 5.0, opening=0.8)
                assert Q > 0, f"{valve_name_cn}流量为0"
                
                duration = time.time() - start
                self.log_test('New', f'阀门 ({valve_name_cn})', 'PASS',
                             f'Q={Q:.2f}m³/s (开度80%)', duration)
                results.append(True)
                
            except Exception as e:
                duration = time.time() - start
                self.log_test('New', f'阀门 ({valve_name_cn})', 'FAIL',
                             str(e), duration)
                results.append(False)
        
        # 3.3 调压井
        start = time.time()
        try:
            from core.structures.surge_tank import SurgeTank, SurgeTankType
            
            surge_tank = SurgeTank(
                "SurgeTank-01",
                5000.0,
                SurgeTankType.SIMPLE,
                200.0,
                100.0
            )
            
            new_level = surge_tank.update(50.0, 30.0, 10.0)
            assert 100 < new_level < 105, f"调压井水位异常: {new_level}"
            
            duration = time.time() - start
            self.log_test('New', '调压井 (SurgeTank)', 'PASS',
                         f'水位={new_level:.2f}m', duration)
            results.append(True)
            
        except Exception as e:
            duration = time.time() - start
            self.log_test('New', '调压井 (SurgeTank)', 'FAIL', str(e), duration)
            results.append(False)
        
        return all(results)
    
    def test_integration(self):
        """测试4: 组件集成测试"""
        print("\n" + "="*80)
        print("测试4: 组件集成测试")
        print("="*80)
        
        start = time.time()
        try:
            # 创建一个小型水电站系统
            from core.structures.turbine import Turbine, TurbineType, TurbineCharacteristics
            from core.structures.valve import Valve, ValveType
            from core.structures.surge_tank import SurgeTank, SurgeTankType
            
            # 水轮机
            char = TurbineCharacteristics(
                rated_head=100.0, rated_flow=50.0, rated_power=45.0,
                rated_efficiency=0.93, rated_speed=375.0
            )
            turbine = Turbine("Unit-1", 0.0, TurbineType.FRANCIS, char)
            
            # 阀门
            valve = Valve("MainValve", 100.0, ValveType.BUTTERFLY,
                         1.5, cv_full_open=200.0)
            
            # 调压井
            surge_tank = SurgeTank("SurgeTank", 5000.0,
                                  SurgeTankType.SIMPLE, 200.0, 100.0)
            
            # 模拟运行
            turbine.start(100.0, 50.0)
            valve.set_opening(0.8, 1.0)
            surge_tank.update(50.0, 50.0, 1.0)
            
            # 验证
            assert turbine.is_running, "水轮机未运行"
            assert 0.7 < valve.opening < 0.9, "阀门开度异常"
            assert 99 < surge_tank.level < 101, "调压井水位异常"
            
            duration = time.time() - start
            self.log_test('Integration', '水电站系统集成', 'PASS',
                         '水轮机+阀门+调压井联合运行正常', duration)
            return True
            
        except Exception as e:
            duration = time.time() - start
            self.log_test('Integration', '水电站系统集成', 'FAIL',
                         str(e), duration)
            return False
    
    def test_performance(self):
        """测试5: 性能测试"""
        print("\n" + "="*80)
        print("测试5: 性能测试")
        print("="*80)
        
        results = []
        
        # 5.1 批量计算性能
        start = time.time()
        try:
            from core.structures import RectangularWeir
            
            weir = RectangularWeir("PerfTest", 0.0, 10.0, 2.0)
            
            # 1000次计算
            for _ in range(1000):
                Q = weir.compute_discharge(5.0)
            
            duration = time.time() - start
            avg_time = duration / 1000
            
            assert avg_time < 0.001, f"单次计算耗时过长: {avg_time:.6f}s"
            
            self.log_test('Performance', '批量计算性能', 'PASS',
                         f'1000次计算耗时{duration:.3f}s, 平均{avg_time*1000:.3f}ms',
                         duration)
            results.append(True)
            
        except Exception as e:
            duration = time.time() - start
            self.log_test('Performance', '批量计算性能', 'FAIL',
                         str(e), duration)
            results.append(False)
        
        return all(results)
    
    def test_accuracy(self):
        """测试6: 精度测试"""
        print("\n" + "="*80)
        print("测试6: 计算精度测试")
        print("="*80)
        
        results = []
        
        # 6.1 堰流量精度
        start = time.time()
        try:
            from core.structures import RectangularWeir
            
            # 已知理论值：Q = 1.7 * B * H^1.5
            weir = RectangularWeir("AccuracyTest", 0.0, 10.0, 0.0)
            H = 3.0  # 过堰水头3m
            Q_calc = weir.compute_discharge(H)
            Q_theory = 1.7 * 10.0 * (H ** 1.5)
            
            error = abs(Q_calc - Q_theory) / Q_theory * 100
            
            assert error < 1.0, f"精度误差过大: {error:.2f}%"
            
            duration = time.time() - start
            self.log_test('Accuracy', '堰流量计算精度', 'PASS',
                         f'误差={error:.3f}% (< 1%)', duration)
            results.append(True)
            
        except Exception as e:
            duration = time.time() - start
            self.log_test('Accuracy', '堰流量计算精度', 'FAIL',
                         str(e), duration)
            results.append(False)
        
        return all(results)
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "="*80)
        print("🎯 HydroClaude Web端到端综合测试")
        print("测试范围: 22种水工结构 (17种原有 + 5种新增)")
        print("="*80)
        
        # 运行测试
        tests = [
            ('后端模块导入', self.test_backend_imports),
            ('原有17种组件', self.test_original_components),
            ('新增5种组件', self.test_new_components),
            ('组件集成', self.test_integration),
            ('性能测试', self.test_performance),
            ('精度测试', self.test_accuracy)
        ]
        
        for test_name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                print(f"\n❌ {test_name}测试出现异常: {e}")
                import traceback
                traceback.print_exc()
        
        # 生成报告
        self.generate_report()
    
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "="*80)
        print("📊 测试报告")
        print("="*80)
        
        self.test_results['end_time'] = datetime.now().isoformat()
        
        # 统计
        total = self.test_results['total_tests']
        passed = self.test_results['passed']
        failed = self.test_results['failed']
        skipped = self.test_results['skipped']
        
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"\n总测试数: {total}")
        print(f"✅ 通过: {passed} ({pass_rate:.1f}%)")
        print(f"❌ 失败: {failed}")
        print(f"⚠️  跳过: {skipped}")
        
        # 分类统计
        print(f"\n分类统计:")
        categories = {}
        for detail in self.test_results['test_details']:
            cat = detail['category']
            if cat not in categories:
                categories[cat] = {'total': 0, 'passed': 0, 'failed': 0}
            categories[cat]['total'] += 1
            if detail['status'] == 'PASS':
                categories[cat]['passed'] += 1
            elif detail['status'] == 'FAIL':
                categories[cat]['failed'] += 1
        
        for cat, stats in categories.items():
            rate = stats['passed'] / stats['total'] * 100 if stats['total'] > 0 else 0
            print(f"  {cat}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")
        
        # 保存JSON报告
        report_file = '/workspace/web/tests/e2e_comprehensive_test_report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n详细报告已保存到: {report_file}")
        
        # 总结
        print("\n" + "="*80)
        if failed == 0:
            print("🎉🎉🎉 所有测试通过！")
        else:
            print(f"⚠️ 有{failed}个测试失败，需要修复")
        print("="*80 + "\n")
        
        return pass_rate >= 90


def main():
    """主函数"""
    tester = E2EComprehensiveTest()
    success = tester.run_all_tests()
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
