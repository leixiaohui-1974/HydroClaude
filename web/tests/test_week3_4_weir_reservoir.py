#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Week 3-4功能测试：堰和水库集成
Test Week 3-4: Weir and Reservoir Integration

测试HydraulicEngineV2新增的4个方法：
1. run_weir_simulation - 堰流计算
2. run_canal_with_weir - 明渠+堰组合
3. run_reservoir_simulation - 水库调度仿真
4. run_reservoir_operation - 水库优化调度

Author: HydroClaude Team
Date: 2025-11-15
"""

import sys
import os

# 添加路径
test_dir = os.path.dirname(os.path.abspath(__file__))
web_dir = os.path.dirname(test_dir)
backend_dir = os.path.join(web_dir, 'backend')
workspace_root = os.path.dirname(web_dir)

# 将必要路径添加到sys.path
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# 尝试导入
try:
    from web.backend.core.hydraulic_engine_v2 import HydraulicEngineV2
except ImportError:
    # 备用导入
    from core.hydraulic_engine_v2 import HydraulicEngineV2


def test_weir_simulation():
    """测试1: 堰流计算（宽顶堰）"""
    print("\n" + "="*70)
    print("测试1: 宽顶堰流量计算")
    print("="*70)
    
    engine = HydraulicEngineV2()
    
    config = {
        'weir': {
            'type': 'broad_crested',
            'name': 'Test-Weir-BroadCrested',
            'position': 500.0,
            'width': 10.0,
            'crest_height': 1.5,
            'discharge_coeff': 1.7
        },
        'upstream': {
            'water_depth': 3.0
        },
        'downstream': {
            'water_depth': 1.0
        }
    }
    
    result = engine.run_weir_simulation('test_weir_broad', config)
    
    print(f"状态: {result.status}")
    assert result.status == 'completed', f"仿真失败: {result.error}"
    
    print(f"✅ 堰类型: {result.metrics['weir_type']}")
    print(f"✅ 过堰流量: {result.metrics['discharge']:.2f} m³/s")
    print(f"✅ 单宽流量: {result.metrics['unit_discharge']:.2f} m²/s")
    print(f"✅ 堰上水头: {result.metrics['head_over_weir']:.2f} m")
    print(f"✅ 是否淹没: {result.metrics['is_submerged']}")
    
    # 验证流量计算合理性
    assert result.metrics['discharge'] > 0, "过堰流量应大于0"
    assert result.metrics['head_over_weir'] == 3.0 - 1.5, "堰上水头计算错误"
    assert not result.metrics['is_submerged'], "应为自由流"
    
    print("✅ 测试1通过")
    return True


def test_sharp_crested_weir():
    """测试2: 尖顶堰流量计算"""
    print("\n" + "="*70)
    print("测试2: 尖顶堰流量计算")
    print("="*70)
    
    engine = HydraulicEngineV2()
    
    config = {
        'weir': {
            'type': 'sharp_crested',
            'name': 'Test-Weir-SharpCrested',
            'position': 300.0,
            'width': 5.0,
            'crest_height': 1.0,
            'discharge_coeff': 1.84
        },
        'upstream': {
            'water_depth': 2.5
        },
        'downstream': {
            'water_depth': 0.8
        }
    }
    
    result = engine.run_weir_simulation('test_weir_sharp', config)
    
    print(f"状态: {result.status}")
    assert result.status == 'completed', f"仿真失败: {result.error}"
    
    print(f"✅ 堰类型: {result.metrics['weir_type']}")
    print(f"✅ 过堰流量: {result.metrics['discharge']:.2f} m³/s")
    print(f"✅ 堰上水头: {result.metrics['head_over_weir']:.2f} m")
    
    assert result.metrics['discharge'] > 0, "过堰流量应大于0"
    
    print("✅ 测试2通过")
    return True


def test_v_notch_weir():
    """测试3: V形堰流量计算"""
    print("\n" + "="*70)
    print("测试3: V形堰流量计算")
    print("="*70)
    
    engine = HydraulicEngineV2()
    
    config = {
        'weir': {
            'type': 'v_notch',
            'name': 'Test-Weir-VNotch',
            'position': 200.0,
            'angle': 90.0,
            'crest_height': 0.5
        },
        'upstream': {
            'water_depth': 1.5
        },
        'downstream': {
            'water_depth': 0.3
        }
    }
    
    result = engine.run_weir_simulation('test_weir_vnotch', config)
    
    print(f"状态: {result.status}")
    assert result.status == 'completed', f"仿真失败: {result.error}"
    
    print(f"✅ 堰类型: {result.metrics['weir_type']}")
    print(f"✅ 过堰流量: {result.metrics['discharge']:.2f} m³/s")
    print(f"✅ 堰上水头: {result.metrics['head_over_weir']:.2f} m")
    
    assert result.metrics['discharge'] > 0, "过堰流量应大于0"
    
    print("✅ 测试3通过")
    return True


def test_canal_with_weir():
    """测试4: 明渠+堰组合仿真"""
    print("\n" + "="*70)
    print("测试4: 明渠+堰组合仿真")
    print("="*70)
    
    engine = HydraulicEngineV2()
    
    config = {
        'canal': {
            'length': 1000.0,
            'width': 10.0,
            'slope': 0.001,
            'manning_n': 0.025,
            'dx': 10.0,
            'initial_conditions': {
                'type': 'uniform',
                'h': 3.0,
                'Q': 50.0
            },
            'simulation': {
                'duration': 100.0,
                'dt': 0.5,
                'output_interval': 50.0
            }
        },
        'weir': {
            'type': 'broad_crested',
            'position': 500.0,
            'width': 10.0,
            'crest_height': 1.5,
            'discharge_coeff': 1.7
        }
    }
    
    result = engine.run_canal_with_weir('test_canal_weir', config)
    
    print(f"状态: {result.status}")
    assert result.status == 'completed', f"组合仿真失败: {result.error}"
    
    print(f"✅ 系统类型: {result.metrics.get('system_type', 'unknown')}")
    print(f"✅ 过堰流量: {result.metrics.get('weir_discharge', 0):.2f} m³/s")
    print(f"✅ 堰位置: {result.metrics.get('weir_position', 0):.1f} m")
    print(f"✅ 堰上水头: {result.metrics.get('weir_head', 0):.2f} m")
    
    assert result.metrics.get('weir_discharge', 0) > 0, "过堰流量应大于0"
    assert result.metrics.get('system_type') == 'canal_with_weir', "系统类型错误"
    
    print("✅ 测试4通过")
    return True


def test_reservoir_simulation():
    """测试5: 水库调度仿真"""
    print("\n" + "="*70)
    print("测试5: 水库调度仿真")
    print("="*70)
    
    engine = HydraulicEngineV2()
    
    config = {
        'reservoir': {
            'name': 'Test-Reservoir',
            'position': 0.0,
            'elevation': [0, 10, 20, 30],
            'area': [0, 1000, 4000, 9000],
            'initial_elevation': 15.0,
            'spillway_elevation': 25.0,
            'spillway_width': 20.0
        },
        'inflow': {
            'type': 'constant',
            'value': 50.0
        },
        'outflow': {
            'type': 'constant',
            'value': 30.0
        },
        'simulation': {
            'duration': 86400.0,  # 1天
            'dt': 60.0
        }
    }
    
    result = engine.run_reservoir_simulation('test_reservoir', config)
    
    print(f"状态: {result.status}")
    assert result.status == 'completed', f"水库仿真失败: {result.error}"
    
    print(f"✅ 初始水位: {result.metrics['initial_elevation']:.2f} m")
    print(f"✅ 最终水位: {result.metrics['final_elevation']:.2f} m")
    print(f"✅ 最高水位: {result.metrics['max_elevation']:.2f} m")
    print(f"✅ 最低水位: {result.metrics['min_elevation']:.2f} m")
    print(f"✅ 入流总量: {result.metrics['total_inflow_volume']:.0f} m³")
    print(f"✅ 出流总量: {result.metrics['total_outflow_volume']:.0f} m³")
    
    assert result.metrics['max_elevation'] >= result.metrics['initial_elevation'], "最高水位不应低于初始水位（入流>出流）"
    assert len(result.time) > 0, "应有时间序列输出"
    
    print("✅ 测试5通过")
    return True


def test_reservoir_operation():
    """测试6: 水库优化调度"""
    print("\n" + "="*70)
    print("测试6: 水库优化调度")
    print("="*70)
    
    engine = HydraulicEngineV2()
    
    config = {
        'reservoir': {
            'name': 'Test-Reservoir-Operation',
            'position': 0.0,
            'elevation': [0, 10, 20, 30],
            'area': [0, 1000, 4000, 9000],
            'initial_elevation': 15.0,
            'spillway_elevation': 28.0,
            'spillway_width': 20.0
        },
        'inflow_hydrograph': {
            'time': [0, 3600, 7200, 10800, 14400],
            'flow': [30, 80, 120, 60, 30]
        },
        'operation_rule': {
            'normal_level': 20.0,
            'flood_limit': 18.0,
            'dead_level': 10.0,
            'max_release': 100.0
        }
    }
    
    result = engine.run_reservoir_operation('test_reservoir_op', config)
    
    print(f"状态: {result.status}")
    assert result.status == 'completed', f"优化调度失败: {result.error}"
    
    print(f"✅ 调度类型: {result.metrics.get('operation_type', 'unknown')}")
    print(f"✅ 正常蓄水位: {result.metrics.get('normal_level', 0):.1f} m")
    print(f"✅ 汛限水位: {result.metrics.get('flood_limit', 0):.1f} m")
    print(f"✅ 最大水位: {result.metrics.get('max_elevation', 0):.2f} m")
    print(f"✅ 最小水位: {result.metrics.get('min_elevation', 0):.2f} m")
    print(f"✅ 峰值泄流: {result.metrics.get('peak_release', 0):.2f} m³/s")
    print(f"✅ 总泄流量: {result.metrics.get('total_release_volume', 0):.0f} m³")
    
    assert result.metrics.get('operation_type') == 'rule_based', "调度类型错误"
    assert len(result.time) == len(config['inflow_hydrograph']['time']), "输出时间点数量错误"
    
    print("✅ 测试6通过")
    return True


def test_engine_info():
    """测试7: 引擎信息更新"""
    print("\n" + "="*70)
    print("测试7: 引擎信息验证")
    print("="*70)
    
    engine = HydraulicEngineV2()
    info = engine.get_engine_info()
    
    print(f"✅ 引擎版本: {info['version']}")
    print(f"✅ 可用方法数: {len(info['available_methods'])}")
    print(f"✅ 支持结构数: {len(info['supported_structures'])}")
    
    # 验证Week 3-4新增方法
    week3_4_methods = [
        'run_weir_simulation',
        'run_canal_with_weir',
        'run_reservoir_simulation',
        'run_reservoir_operation'
    ]
    
    for method in week3_4_methods:
        assert method in info['available_methods'], f"缺少方法: {method}"
        print(f"  ✓ {method}")
    
    # 验证Week 3-4新增结构
    week3_4_structures = [
        'broad_crested_weir',
        'sharp_crested_weir',
        'ogee_weir',
        'v_notch_weir',
        'reservoir',
        'storage'
    ]
    
    for structure in week3_4_structures:
        assert structure in info['supported_structures'], f"缺少结构: {structure}"
        print(f"  ✓ {structure}")
    
    assert info['version'] == '2.0.0', "版本号错误"
    
    print("✅ 测试7通过")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "Week 3-4功能测试套件" + " "*33 + "║")
    print("║" + " "*15 + "堰和水库集成测试" + " "*36 + "║")
    print("╚" + "="*68 + "╝")
    
    tests = [
        ("宽顶堰流量计算", test_weir_simulation),
        ("尖顶堰流量计算", test_sharp_crested_weir),
        ("V形堰流量计算", test_v_notch_weir),
        ("明渠+堰组合仿真", test_canal_with_weir),
        ("水库调度仿真", test_reservoir_simulation),
        ("水库优化调度", test_reservoir_operation),
        ("引擎信息验证", test_engine_info)
    ]
    
    results = []
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            results.append((name, "✅ PASSED"))
            passed += 1
        except Exception as e:
            results.append((name, f"❌ FAILED: {str(e)}"))
            failed += 1
    
    print("\n" + "="*70)
    print("测试结果汇总")
    print("="*70)
    
    for name, status in results:
        print(f"{name:<25} {status}")
    
    print("\n" + "="*70)
    print(f"总计: {len(tests)} | 通过: {passed} | 失败: {failed}")
    print(f"通过率: {passed/len(tests)*100:.1f}%")
    print("="*70)
    
    if failed == 0:
        print("\n🎉 Week 3-4所有测试通过！")
        return True
    else:
        print(f"\n⚠️  有 {failed} 个测试失败")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
