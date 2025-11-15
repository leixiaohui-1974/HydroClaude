#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Week 1-2 功能测试
测试泵站和闸门集成功能

Author: HydroClaude Team
Date: 2025-11-15
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from web.backend.core.hydraulic_engine_v2 import HydraulicEngineV2


def test_pump_simulation():
    """测试1: 泵站仿真"""
    print("\n" + "="*80)
    print("测试1: 泵站仿真")
    print("="*80)
    
    engine = HydraulicEngineV2()
    
    config = {
        'pump': {
            'name': 'Test-Pump',
            'flow_rate': 10.0,
            'head': 15.0,
            'num_pumps': 2,
            'pump_type': 'parallel'
        },
        'upstream': {'water_level': 5.0},
        'downstream': {'elevation': 20.0},
        'operation': {'duration': 100.0}
    }
    
    result = engine.run_pump_simulation('test_pump_001', config)
    
    assert result.status == 'completed', f"泵站仿真失败: {result.error}"
    assert 'avg_flow' in result.metrics
    assert 'avg_efficiency' in result.metrics
    assert result.metrics['avg_flow'] > 0
    
    print(f"  ✅ 状态: {result.status}")
    print(f"  ✅ 平均流量: {result.metrics['avg_flow']:.2f} m³/s")
    print(f"  ✅ 平均效率: {result.metrics['avg_efficiency']*100:.1f}%")
    print(f"  ✅ 总抽水量: {result.metrics['total_volume']:.0f} m³")
    
    return True


def test_gate_simulation():
    """测试2: 闸门仿真"""
    print("\n" + "="*80)
    print("测试2: 闸门仿真")
    print("="*80)
    
    engine = HydraulicEngineV2()
    
    config = {
        'gate': {
            'type': 'sluice',
            'name': 'Test-Gate',
            'width': 5.0,
            'opening': 2.0,
            'discharge_coeff': 0.6
        },
        'upstream': {'water_depth': 5.0},
        'downstream': {'water_depth': 2.0}
    }
    
    result = engine.run_gate_simulation('test_gate_001', config)
    
    assert result.status == 'completed', f"闸门仿真失败: {result.error}"
    assert 'discharge' in result.metrics
    assert 'flow_regime' in result.metrics
    assert result.metrics['discharge'] > 0
    
    print(f"  ✅ 状态: {result.status}")
    print(f"  ✅ 过闸流量: {result.metrics['discharge']:.2f} m³/s")
    print(f"  ✅ 流态: {result.metrics['flow_regime']}")
    print(f"  ✅ 淹没比: {result.metrics['submergence_ratio']:.2f}")
    
    return True


def test_radial_gate():
    """测试3: 弧形闸门"""
    print("\n" + "="*80)
    print("测试3: 弧形闸门")
    print("="*80)
    
    engine = HydraulicEngineV2()
    
    config = {
        'gate': {
            'type': 'radial',
            'width': 8.0,
            'opening': 3.0,
            'discharge_coeff': 0.65
        },
        'upstream': {'water_depth': 10.0},
        'downstream': {'water_depth': 5.0}
    }
    
    result = engine.run_gate_simulation('test_radial_001', config)
    
    assert result.status == 'completed'
    assert result.metrics['gate_type'] == 'radial'
    
    print(f"  ✅ 状态: {result.status}")
    print(f"  ✅ 过闸流量: {result.metrics['discharge']:.2f} m³/s")
    print(f"  ✅ 闸门类型: {result.metrics['gate_type']}")
    
    return True


def test_canal_with_pump():
    """测试4: 明渠+泵站组合"""
    print("\n" + "="*80)
    print("测试4: 明渠+泵站组合")
    print("="*80)
    
    engine = HydraulicEngineV2()
    
    config = {
        'canal': {
            'width': 10.0,
            'length': 1000.0,
            'n_cells': 100,
            'manning_n': 0.025,
            'slope': 0.001,
            't_end': 50.0,
            'initial_conditions': {
                'type': 'uniform',
                'h': 3.0,
                'Q': 0.0
            }
        },
        'pump': {
            'position': 500.0,
            'flow_rate': 5.0,
            'head': 10.0
        }
    }
    
    result = engine.run_canal_with_pump('test_canal_pump_001', config)
    
    assert result.status == 'completed', f"组合仿真失败: {result.error}"
    assert 'pump_flow' in result.metrics
    assert result.metrics['system_type'] == 'canal_with_pump'
    
    print(f"  ✅ 状态: {result.status}")
    print(f"  ✅ 系统类型: {result.metrics['system_type']}")
    print(f"  ✅ 泵站流量: {result.metrics['pump_flow']:.2f} m³/s")
    print(f"  ✅ 泵站位置: {result.metrics['pump_position']:.0f} m")
    
    return True


def test_canal_with_gate():
    """测试5: 明渠+闸门组合"""
    print("\n" + "="*80)
    print("测试5: 明渠+闸门组合")
    print("="*80)
    
    engine = HydraulicEngineV2()
    
    config = {
        'canal': {
            'width': 10.0,
            'length': 1000.0,
            'n_cells': 100,
            'manning_n': 0.0,
            'slope': 0.0,
            't_end': 30.0,
            'initial_conditions': {
                'type': 'dam_break',
                'dam_position': 500.0,
                'h_left': 8.0,
                'h_right': 2.0
            }
        },
        'gate': {
            'position': 500.0,
            'width': 10.0,
            'opening': 3.0,
            'type': 'sluice'
        }
    }
    
    result = engine.run_canal_with_gate('test_canal_gate_001', config)
    
    assert result.status == 'completed', f"组合仿真失败: {result.error}"
    assert 'gate_discharge' in result.metrics
    assert result.metrics['system_type'] == 'canal_with_gate'
    
    print(f"  ✅ 状态: {result.status}")
    print(f"  ✅ 系统类型: {result.metrics['system_type']}")
    print(f"  ✅ 闸门流量: {result.metrics['gate_discharge']:.2f} m³/s")
    print(f"  ✅ 闸门流态: {result.metrics['gate_regime']}")
    
    return True


def test_engine_info():
    """测试6: 引擎信息"""
    print("\n" + "="*80)
    print("测试6: 引擎信息")
    print("="*80)
    
    engine = HydraulicEngineV2()
    info = engine.get_engine_info()
    
    assert info['version'] == '2.0.0'
    assert len(info['available_methods']) == 5
    assert 'run_pump_simulation' in info['available_methods']
    assert 'run_gate_simulation' in info['available_methods']
    
    print(f"  ✅ 版本: {info['version']}")
    print(f"  ✅ 可用方法数: {len(info['available_methods'])}")
    print(f"  ✅ 支持结构数: {len(info['supported_structures'])}")
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "🎯"*40)
    print("Week 1-2 功能测试".center(80))
    print("🎯"*40)
    
    tests = [
        ("泵站仿真", test_pump_simulation),
        ("闸门仿真", test_gate_simulation),
        ("弧形闸门", test_radial_gate),
        ("明渠+泵站", test_canal_with_pump),
        ("明渠+闸门", test_canal_with_gate),
        ("引擎信息", test_engine_info)
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, True))
        except Exception as e:
            print(f"\n❌ {name}测试失败: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 生成报告
    print("\n" + "="*80)
    print("测试结果总结".center(80))
    print("="*80)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} - {name}")
    
    print("-"*80)
    print(f"总计: {passed}/{total} 通过 ({passed/total*100:.1f}%)")
    
    print("\n" + "🎉"*40)
    if passed == total:
        print("✅ Week 1-2所有测试通过！".center(80))
    else:
        print(f"⚠️  {total-passed}个测试失败".center(80))
    print("🎉"*40)
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
