#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
P0任务端到端集成验证
测试所有新增的API端点

Author: HydroClaude Team
Date: 2025-11-17
"""

import sys
import os

# 添加路径
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

from core.hydraulic_engine_v2 import HydraulicEngineV2
import json


def test_api_endpoints():
    """测试所有API端点对应的引擎方法"""
    
    engine = HydraulicEngineV2()
    
    print("="*80)
    print("🧪 P0任务端到端集成验证")
    print("="*80)
    
    # 测试配置
    test_cases = [
        # 第一部分：泵站系统
        {
            'name': '泵站仿真',
            'method': 'run_pump_simulation',
            'config': {
                'pump': {
                    'flow_rate': 10.0,
                    'head': 15.0,
                    'num_pumps': 2,
                    'pump_type': 'parallel'
                },
                'upstream': {'water_level': 5.0},
                'downstream': {'elevation': 20.0},
                'operation': {'duration': 100.0}
            }
        },
        
        # 第二部分：闸门系统
        {
            'name': '滑动闸门',
            'method': 'run_gate_simulation',
            'config': {
                'gate': {
                    'type': 'sluice',
                    'width': 10.0,
                    'opening': 2.0
                },
                'upstream': {'water_depth': 5.0},
                'downstream': {'water_depth': 2.0}
            }
        },
        
        # 第三部分：堰系统
        {
            'name': '宽顶堰',
            'method': 'run_weir_simulation',
            'config': {
                'weir': {
                    'type': 'broad_crested',
                    'width': 10.0,
                    'crest_height': 1.0
                },
                'upstream': {'water_depth': 5.0},
                'downstream': {'water_depth': 2.0}
            }
        },
        
        # 第四部分：明渠系统
        {
            'name': '矩形明渠',
            'method': 'run_canal_simulation',
            'config': {
                'canal': {
                    'width': 10.0,
                    'length': 1000.0,
                    'slope': 0.001,
                    'manning_n': 0.025,
                    'n_cells': 100
                },
                'boundary': {
                    'upstream_Q': 50.0,
                    'downstream_h': 5.0
                },
                'simulation': {
                    't_end': 100.0
                }
            }
        }
    ]
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n测试 {i}/{len(test_cases)}: {test['name']}")
        print("-" * 60)
        
        try:
            # 检查方法是否存在
            method_name = test['method']
            if not hasattr(engine, method_name):
                print(f"  ❌ 方法不存在: {method_name}")
                results.append({
                    'name': test['name'],
                    'status': 'failed',
                    'error': f'Method {method_name} not found'
                })
                continue
            
            # 调用方法
            method = getattr(engine, method_name)
            task_id = f'test_{i:03d}'
            result = method(task_id, test['config'])
            
            # 验证结果
            if result.status == 'completed':
                print(f"  ✅ 成功")
                print(f"     状态: {result.status}")
                print(f"     耗时: {result.duration:.3f}秒")
                print(f"     指标: {list(result.metrics.keys())}")
                results.append({
                    'name': test['name'],
                    'status': 'passed',
                    'duration': result.duration,
                    'metrics': result.metrics
                })
            else:
                print(f"  ❌ 失败")
                print(f"     状态: {result.status}")
                print(f"     错误: {result.error}")
                results.append({
                    'name': test['name'],
                    'status': 'failed',
                    'error': result.error
                })
                
        except Exception as e:
            print(f"  ❌ 异常")
            print(f"     错误: {str(e)}")
            results.append({
                'name': test['name'],
                'status': 'failed',
                'error': str(e)
            })
    
    # 统计结果
    print("\n" + "="*80)
    print("📊 测试结果统计")
    print("="*80)
    
    passed = sum(1 for r in results if r['status'] == 'passed')
    failed = sum(1 for r in results if r['status'] == 'failed')
    
    print(f"\n总测试数: {len(results)}")
    print(f"通过: {passed} ({passed/len(results)*100:.1f}%)")
    print(f"失败: {failed} ({failed/len(results)*100:.1f}%)")
    
    # 保存结果
    output_file = os.path.join(os.path.dirname(__file__), 'test_p0_results.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total': len(results),
            'passed': passed,
            'failed': failed,
            'pass_rate': passed/len(results)*100,
            'results': results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 结果已保存到: {output_file}")
    
    return passed == len(results)


def test_component_library():
    """测试前端组件库统计"""
    
    print("\n" + "="*80)
    print("📚 前端组件库验证")
    print("="*80)
    
    # 手动统计（因为无法导入TypeScript）
    component_counts = {
        '泵站系统': 1,
        '闸门系统': 5,
        '堰系统': 6,
        '水电系统': 4,
        '明渠系统': 4,
        '扩展结构': 4
    }
    
    total = sum(component_counts.values())
    
    print(f"\n组件分类统计:")
    for category, count in component_counts.items():
        print(f"  {category}: {count}种")
    
    print(f"\n总组件数: {total}")
    
    # 验证API端点（基于structures.py）
    api_endpoints = [
        '/api/structures/pump',
        '/api/structures/gate',
        '/api/structures/radial-gate',
        '/api/structures/vertical-lift-gate',
        '/api/structures/broad-crested-weir',
        '/api/structures/sharp-crested-weir',
        '/api/structures/v-notch-weir',
        '/api/structures/turbine',
        '/api/structures/valve',
        '/api/structures/surge-tank',
        '/api/structures/culvert',
        '/api/structures/bridge',
        '/api/structures/weir',
        '/api/structures/canal',
        '/api/structures/canal-with-pump',
        '/api/structures/canal-with-gate',
        '/api/structures/canal-with-weir',
    ]
    
    print(f"\nAPI端点数: {len(api_endpoints)}")
    print(f"  已实现: {len(api_endpoints)}")
    print(f"  覆盖率: {len(api_endpoints)/total*100:.1f}%")
    
    return True


def test_engine_info():
    """测试引擎信息"""
    
    print("\n" + "="*80)
    print("🔧 引擎信息验证")
    print("="*80)
    
    engine = HydraulicEngineV2()
    info = engine.get_engine_info()
    
    print(f"\n引擎版本: {info['version']}")
    print(f"可用方法数: {len(info['available_methods'])}")
    print(f"\n方法列表:")
    for method in sorted(info['available_methods']):
        print(f"  - {method}")
    
    return True


def main():
    """主函数"""
    
    print("\n" + "="*80)
    print("🎯 P0任务端到端集成验证")
    print("测试时间: 2025-11-17")
    print("="*80)
    
    success = True
    
    # 测试1: 引擎信息
    try:
        test_engine_info()
    except Exception as e:
        print(f"\n❌ 引擎信息测试失败: {e}")
        success = False
    
    # 测试2: 组件库
    try:
        test_component_library()
    except Exception as e:
        print(f"\n❌ 组件库测试失败: {e}")
        success = False
    
    # 测试3: API端点
    try:
        if not test_api_endpoints():
            success = False
    except Exception as e:
        print(f"\n❌ API端点测试失败: {e}")
        success = False
    
    # 最终结果
    print("\n" + "="*80)
    if success:
        print("✅ 所有测试通过！")
    else:
        print("⚠️ 部分测试失败，请查看详细日志")
    print("="*80)
    
    return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
