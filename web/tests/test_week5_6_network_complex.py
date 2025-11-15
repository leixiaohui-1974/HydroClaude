#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Week 5-6功能测试：管网和复杂系统
Test Week 5-6: Network and Complex System

测试HydraulicEngineV2新增的4个方法：
1. run_pipe_flow - 管道流动计算
2. run_network_simulation - 管网仿真
3. run_complex_system - 复杂组合系统
4. run_integrated_operation - 综合调度优化

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


def test_pipe_flow_manning():
    """测试1: 管道流动计算（Manning公式）"""
    print("\n" + "="*70)
    print("测试1: 管道流动计算（Manning公式）")
    print("="*70)
    
    engine = HydraulicEngineV2()
    
    config = {
        'pipe': {
            'name': 'Test-Pipe-Manning',
            'length': 1000.0,
            'diameter': 1.0,
            'roughness': 0.025,
            'slope': 0.001,
            'formula': 'manning'
        },
        'flow': {
            'discharge': 1.5,
            'upstream_pressure': 100.0
        }
    }
    
    result = engine.run_pipe_flow('test_pipe_manning', config)
    
    print(f"状态: {result.status}")
    assert result.status == 'completed', f"仿真失败: {result.error}"
    
    print(f"✅ 流量: {result.metrics['discharge']:.2f} m³/s")
    print(f"✅ 流速: {result.metrics['velocity']:.2f} m/s")
    print(f"✅ 水头损失: {result.metrics['head_loss']:.2f} m")
    print(f"✅ 上游压力: {result.metrics['upstream_pressure']:.1f} kPa")
    print(f"✅ 下游压力: {result.metrics['downstream_pressure']:.1f} kPa")
    print(f"✅ 摩阻坡度: {result.metrics['friction_slope']:.6f}")
    print(f"✅ Reynolds数: {result.metrics['reynolds_number']:.0f}")
    print(f"✅ 计算公式: {result.metrics['formula']}")
    
    # 验证
    assert result.metrics['discharge'] == 1.5, "流量错误"
    assert result.metrics['head_loss'] > 0, "水头损失应大于0"
    assert result.metrics['downstream_pressure'] < result.metrics['upstream_pressure'], "下游压力应小于上游"
    
    print("✅ 测试1通过")
    return True


def test_pipe_flow_hazen_williams():
    """测试2: 管道流动计算（Hazen-Williams公式）"""
    print("\n" + "="*70)
    print("测试2: 管道流动计算（Hazen-Williams公式）")
    print("="*70)
    
    engine = HydraulicEngineV2()
    
    config = {
        'pipe': {
            'name': 'Test-Pipe-HW',
            'length': 500.0,
            'diameter': 0.8,
            'roughness': 0.02,
            'slope': 0.002,
            'formula': 'hazen_williams'
        },
        'flow': {
            'discharge': 1.0,
            'upstream_pressure': 80.0
        }
    }
    
    result = engine.run_pipe_flow('test_pipe_hw', config)
    
    print(f"状态: {result.status}")
    assert result.status == 'completed', f"仿真失败: {result.error}"
    
    print(f"✅ 计算公式: {result.metrics['formula']}")
    print(f"✅ 水头损失: {result.metrics['head_loss']:.2f} m")
    print(f"✅ 摩阻坡度: {result.metrics['friction_slope']:.6f}")
    
    assert result.metrics['formula'] == 'hazen_williams', "公式错误"
    assert result.metrics['head_loss'] > 0, "水头损失应大于0"
    
    print("✅ 测试2通过")
    return True


def test_network_simulation():
    """测试3: 管网仿真"""
    print("\n" + "="*70)
    print("测试3: 管网仿真")
    print("="*70)
    
    engine = HydraulicEngineV2()
    
    config = {
        'nodes': [
            {'id': 'N1', 'elevation': 100.0, 'demand': 0.0},
            {'id': 'N2', 'elevation': 95.0, 'demand': 0.5},
            {'id': 'N3', 'elevation': 90.0, 'demand': 0.3}
        ],
        'pipes': [
            {'id': 'P1', 'from': 'N1', 'to': 'N2', 'length': 500.0, 'diameter': 0.5},
            {'id': 'P2', 'from': 'N2', 'to': 'N3', 'length': 400.0, 'diameter': 0.4}
        ],
        'source': {
            'node': 'N1',
            'head': 120.0
        }
    }
    
    result = engine.run_network_simulation('test_network', config)
    
    print(f"状态: {result.status}")
    assert result.status == 'completed', f"仿真失败: {result.error}"
    
    print(f"✅ 节点数: {result.metrics['num_nodes']}")
    print(f"✅ 管段数: {result.metrics['num_pipes']}")
    print(f"✅ 总需水量: {result.metrics['total_demand']:.2f} m³/s")
    print(f"✅ 求解器: {result.metrics['solver']}")
    
    print("\n节点水头:")
    for node_id, head in result.metrics['node_heads'].items():
        print(f"  {node_id}: {head:.2f} m")
    
    print("\n管段流量:")
    for pipe_id, flow in result.metrics['pipe_flows'].items():
        print(f"  {pipe_id}: {flow:.3f} m³/s")
    
    assert result.metrics['num_nodes'] == 3, "节点数错误"
    assert result.metrics['num_pipes'] == 2, "管段数错误"
    assert result.metrics['total_demand'] == 0.8, "总需水量错误"
    
    print("✅ 测试3通过")
    return True


def test_complex_system():
    """测试4: 复杂组合系统"""
    print("\n" + "="*70)
    print("测试4: 复杂组合系统")
    print("="*70)
    
    engine = HydraulicEngineV2()
    
    config = {
        'components': [
            {'type': 'pump', 'config': {'flow_rate': 10.0, 'head': 20.0}},
            {'type': 'pipe', 'config': {'length': 500.0, 'diameter': 0.8}},
            {'type': 'storage', 'config': {'initial_volume': 1000.0, 'initial_elevation': 10.0}}
        ],
        'connections': [
            {'from': 0, 'to': 1},
            {'from': 1, 'to': 2}
        ],
        'operation': {
            'duration': 3600.0,
            'timestep': 60.0
        }
    }
    
    result = engine.run_complex_system('test_complex', config)
    
    print(f"状态: {result.status}")
    assert result.status == 'completed', f"仿真失败: {result.error}"
    
    print(f"✅ 组件数: {result.metrics['num_components']}")
    print(f"✅ 连接数: {result.metrics['num_connections']}")
    print(f"✅ 仿真时长: {result.metrics['simulation_duration']:.0f} s")
    print(f"✅ 时间步数: {result.metrics['timesteps']}")
    print(f"✅ 平均流量: {result.metrics['avg_flow']:.2f} m³/s")
    print(f"✅ 最大流量: {result.metrics['max_flow']:.2f} m³/s")
    print(f"✅ 系统类型: {result.metrics['system_type']}")
    
    assert result.metrics['num_components'] == 3, "组件数错误"
    assert result.metrics['num_connections'] == 2, "连接数错误"
    assert result.metrics['avg_flow'] > 0, "平均流量应大于0"
    assert result.metrics['system_type'] == 'complex_integrated', "系统类型错误"
    
    print("✅ 测试4通过")
    return True


def test_integrated_operation():
    """测试5: 综合调度优化"""
    print("\n" + "="*70)
    print("测试5: 综合调度优化")
    print("="*70)
    
    engine = HydraulicEngineV2()
    
    config = {
        'system': {
            'pumps': [{'id': 'P1', 'capacity': 10.0}],
            'reservoirs': [{'id': 'R1', 'capacity': 5000.0}],
            'network': {}
        },
        'objectives': {
            'minimize_cost': True,
            'maximize_reliability': False,
            'minimize_energy': True
        },
        'constraints': {
            'min_pressure': 20.0,
            'max_flow': 50.0,
            'emergency_storage': 500.0
        },
        'forecast': {
            'demand': [10, 15, 20, 25, 20, 15, 10],
            'horizon': 7
        }
    }
    
    result = engine.run_integrated_operation('test_integrated', config)
    
    print(f"状态: {result.status}")
    assert result.status == 'completed', f"仿真失败: {result.error}"
    
    print(f"✅ 优化类型: {result.metrics['optimization_type']}")
    print(f"✅ 总成本: {result.metrics['total_cost']:.2f} 元")
    print(f"✅ 平均泵数: {result.metrics['avg_pumps_running']:.1f} 台")
    print(f"✅ 峰值需求: {result.metrics['peak_demand']:.1f} m³/s")
    print(f"✅ 预测时长: {result.metrics['forecast_horizon']} 步")
    
    print("\n泵站调度方案:")
    for i, num_pumps in enumerate(result.metrics['pump_schedule']):
        print(f"  时段{i+1}: {num_pumps} 台")
    
    print("\n成本分布:")
    for i, cost in enumerate(result.metrics['cost_schedule']):
        print(f"  时段{i+1}: {cost:.2f} 元")
    
    assert result.metrics['optimization_type'] == 'rule_based_heuristic', "优化类型错误"
    assert result.metrics['total_cost'] > 0, "总成本应大于0"
    assert result.metrics['peak_demand'] == 25.0, "峰值需求错误"
    assert result.metrics['forecast_horizon'] == 7, "预测时长错误"
    
    print("✅ 测试5通过")
    return True


def test_engine_info():
    """测试6: 引擎信息验证"""
    print("\n" + "="*70)
    print("测试6: 引擎信息验证")
    print("="*70)
    
    engine = HydraulicEngineV2()
    info = engine.get_engine_info()
    
    print(f"✅ 引擎版本: {info['version']}")
    print(f"✅ 可用方法数: {len(info['available_methods'])}")
    print(f"✅ 支持结构数: {len(info['supported_structures'])}")
    
    # 验证Week 5-6新增方法
    week5_6_methods = [
        'run_pipe_flow',
        'run_network_simulation',
        'run_complex_system',
        'run_integrated_operation'
    ]
    
    print("\nWeek 5-6新增方法:")
    for method in week5_6_methods:
        assert method in info['available_methods'], f"缺少方法: {method}"
        print(f"  ✓ {method}")
    
    # 验证Week 5-6新增结构
    week5_6_structures = [
        'channel',
        'pipe',
        'network',
        'junction'
    ]
    
    print("\nWeek 5-6新增结构:")
    for structure in week5_6_structures:
        assert structure in info['supported_structures'], f"缺少结构: {structure}"
        print(f"  ✓ {structure}")
    
    # 验证总方法数（1个原有 + 4个Week1-2 + 4个Week3-4 + 4个Week5-6 = 13）
    assert len(info['available_methods']) == 13, f"方法数错误: 应为13，实际{len(info['available_methods'])}"
    
    print("✅ 测试6通过")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*12 + "Week 5-6功能测试套件" + " "*36 + "║")
    print("║" + " "*12 + "管网和复杂系统测试" + " "*36 + "║")
    print("╚" + "="*68 + "╝")
    
    tests = [
        ("管道流动-Manning公式", test_pipe_flow_manning),
        ("管道流动-Hazen-Williams", test_pipe_flow_hazen_williams),
        ("管网仿真", test_network_simulation),
        ("复杂组合系统", test_complex_system),
        ("综合调度优化", test_integrated_operation),
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
        print(f"{name:<28} {status}")
    
    print("\n" + "="*70)
    print(f"总计: {len(tests)} | 通过: {passed} | 失败: {failed}")
    print(f"通过率: {passed/len(tests)*100:.1f}%")
    print("="*70)
    
    if failed == 0:
        print("\n🎉 Week 5-6所有测试通过！")
        return True
    else:
        print(f"\n⚠️  有 {failed} 个测试失败")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
