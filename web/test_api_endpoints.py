#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API端点快速测试脚本
直接测试FastAPI路由，不需要启动服务器

Author: HydroClaude Team
Date: 2025-11-17
"""

import sys
import os

# 添加路径
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

def test_imports():
    """测试导入"""
    print("="*80)
    print("🧪 测试1: 导入验证")
    print("="*80)
    
    try:
        from core.hydraulic_engine_v2 import HydraulicEngineV2
        print("✅ HydraulicEngineV2 导入成功")
        
        engine = HydraulicEngineV2()
        print(f"✅ 引擎实例化成功")
        print(f"   版本: {engine.version}")
        
        info = engine.get_engine_info()
        print(f"✅ 引擎信息获取成功")
        print(f"   可用方法数: {len(info['available_methods'])}")
        
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_router():
    """测试API路由"""
    print("\n" + "="*80)
    print("🧪 测试2: API路由验证")
    print("="*80)
    
    try:
        from api_gateway.routers import structures
        print("✅ structures router 导入成功")
        
        # 检查路由器
        router = structures.router
        print(f"✅ 路由器实例化成功")
        print(f"   路由前缀: {router.prefix}")
        print(f"   标签: {router.tags}")
        
        # 统计路由数量
        route_count = len(router.routes)
        print(f"✅ 注册的路由数: {route_count}")
        
        # 列出所有路由
        print("\n注册的API端点:")
        for route in router.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                methods = ', '.join(route.methods) if route.methods else 'GET'
                print(f"  {methods:8} {route.path}")
        
        return True
    except Exception as e:
        print(f"❌ API路由测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pydantic_models():
    """测试Pydantic模型"""
    print("\n" + "="*80)
    print("🧪 测试3: Pydantic模型验证")
    print("="*80)
    
    try:
        from api_gateway.routers.structures import (
            PumpConfig, GateConfig, WeirConfig,
            TurbineConfig, ValveConfig, SurgeTankConfig,
            CulvertConfig, BridgeConfig
        )
        
        models = [
            ('PumpConfig', PumpConfig),
            ('GateConfig', GateConfig),
            ('WeirConfig', WeirConfig),
            ('TurbineConfig', TurbineConfig),
            ('ValveConfig', ValveConfig),
            ('SurgeTankConfig', SurgeTankConfig),
            ('CulvertConfig', CulvertConfig),
            ('BridgeConfig', BridgeConfig)
        ]
        
        print(f"✅ 导入了 {len(models)} 个Pydantic模型")
        
        for name, model in models:
            # 创建默认实例
            instance = model()
            print(f"  ✅ {name}: {len(instance.model_fields)} 个字段")
        
        return True
    except Exception as e:
        print(f"❌ Pydantic模型测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_engine_methods():
    """测试引擎方法"""
    print("\n" + "="*80)
    print("🧪 测试4: 引擎方法调用")
    print("="*80)
    
    try:
        from core.hydraulic_engine_v2 import HydraulicEngineV2
        
        engine = HydraulicEngineV2()
        
        # 测试泵站仿真
        print("\n测试: 泵站仿真")
        pump_config = {
            'pump': {
                'flow_rate': 10.0,
                'head': 15.0,
                'num_pumps': 1,
                'pump_type': 'single'
            },
            'upstream': {'water_level': 5.0},
            'downstream': {'elevation': 20.0},
            'operation': {'duration': 10.0}
        }
        
        result = engine.run_pump_simulation('test_001', pump_config)
        
        if result.status == 'completed':
            print(f"  ✅ 泵站仿真成功")
            print(f"     状态: {result.status}")
            print(f"     耗时: {result.duration:.3f}秒")
            print(f"     指标: {list(result.metrics.keys())[:5]}...")
        else:
            print(f"  ⚠️ 泵站仿真返回: {result.status}")
            if result.error:
                print(f"     错误: {result.error}")
        
        # 测试闸门仿真
        print("\n测试: 闸门仿真")
        gate_config = {
            'gate': {
                'type': 'sluice',
                'width': 5.0,
                'opening': 2.0
            },
            'upstream': {'water_depth': 5.0},
            'downstream': {'water_depth': 2.0}
        }
        
        result = engine.run_gate_simulation('test_002', gate_config)
        
        if result.status == 'completed':
            print(f"  ✅ 闸门仿真成功")
            print(f"     状态: {result.status}")
            print(f"     流量: {result.metrics.get('discharge', 0):.2f} m³/s")
        else:
            print(f"  ⚠️ 闸门仿真返回: {result.status}")
        
        return True
    except Exception as e:
        print(f"❌ 引擎方法测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("\n" + "="*80)
    print("🚀 API端点快速测试")
    print("="*80)
    
    results = []
    
    # 执行测试
    results.append(('导入验证', test_imports()))
    results.append(('API路由验证', test_api_router()))
    results.append(('Pydantic模型', test_pydantic_models()))
    results.append(('引擎方法调用', test_engine_methods()))
    
    # 统计结果
    print("\n" + "="*80)
    print("📊 测试结果汇总")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n总测试数: {total}")
    print(f"通过: {passed} ({passed/total*100:.1f}%)")
    print(f"失败: {total-passed}")
    
    print("\n详细结果:")
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status} - {name}")
    
    print("\n" + "="*80)
    if passed == total:
        print("✅ 所有测试通过！API就绪")
    else:
        print("⚠️ 部分测试失败，请检查")
    print("="*80)
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
