#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时API测试
Live API Testing

启动服务器并进行真实的HTTP API调用测试

Author: HydroClaude Team
Date: 2025-11-17
"""

import requests
import time
import json
import subprocess
import sys
import os
from datetime import datetime

API_BASE = "http://localhost:8000"


def wait_for_server(max_wait=30):
    """等待服务器启动"""
    print("等待服务器启动...")
    for i in range(max_wait):
        try:
            response = requests.get(f"{API_BASE}/api/structures/health", timeout=2)
            if response.status_code == 200:
                print(f"✅ 服务器已就绪（{i+1}秒）")
                return True
        except:
            time.sleep(1)
            print(f"   等待中... {i+1}/{max_wait}秒")
    return False


def test_health_check():
    """测试1: 健康检查"""
    print("\n" + "="*80)
    print("测试1: 健康检查")
    print("="*80)
    
    try:
        response = requests.get(f"{API_BASE}/api/structures/health")
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False


def test_structure_types():
    """测试2: 获取组件类型"""
    print("\n" + "="*80)
    print("测试2: 获取组件类型")
    print("="*80)
    
    try:
        response = requests.get(f"{API_BASE}/api/structures/types")
        data = response.json()
        print(f"状态码: {response.status_code}")
        print(f"\n支持的组件:")
        for struct_type, info in data.get('structures', {}).items():
            print(f"  • {info['name']} ({struct_type})")
        print(f"\n总组件数: {data.get('total_components', 0)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False


def test_pump_simulation():
    """测试3: 泵站仿真"""
    print("\n" + "="*80)
    print("测试3: 泵站仿真")
    print("="*80)
    
    payload = {
        "pump": {
            "flow_rate": 10.0,
            "head": 15.0,
            "num_pumps": 2,
            "pump_type": "parallel"
        },
        "upstream": {"water_level": 5.0},
        "downstream": {"elevation": 20.0},
        "operation": {"duration": 100.0}
    }
    
    try:
        start = time.time()
        response = requests.post(
            f"{API_BASE}/api/structures/pump",
            json=payload,
            timeout=10
        )
        elapsed = time.time() - start
        
        print(f"状态码: {response.status_code}")
        print(f"响应时间: {elapsed:.3f}秒")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n结果:")
            print(f"  任务ID: {data.get('task_id', 'N/A')}")
            print(f"  状态: {data.get('status', 'N/A')}")
            print(f"  耗时: {data.get('duration', 0):.4f}秒")
            metrics = data.get('metrics', {})
            print(f"\n关键指标:")
            print(f"  平均流量: {metrics.get('avg_flow', 0):.2f} m³/s")
            print(f"  平均效率: {metrics.get('avg_efficiency', 0)*100:.1f}%")
            print(f"  平均扬程: {metrics.get('avg_head', 0):.2f} m")
            print(f"  泵站类型: {metrics.get('pump_type', 'N/A')}")
            print(f"  泵数量: {metrics.get('num_pumps', 0)}")
        else:
            print(f"响应: {response.text}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False


def test_turbine_simulation():
    """测试4: 水轮机仿真 ⭐"""
    print("\n" + "="*80)
    print("测试4: 水轮机仿真 ⭐ 市场独有")
    print("="*80)
    
    payload = {
        "turbine": {
            "type": "francis",
            "rated_power": 50.0,
            "rated_head": 100.0,
            "rated_flow": 60.0
        },
        "operation": {
            "head": 100.0,
            "flow": 60.0
        }
    }
    
    try:
        start = time.time()
        response = requests.post(
            f"{API_BASE}/api/structures/turbine",
            json=payload,
            timeout=10
        )
        elapsed = time.time() - start
        
        print(f"状态码: {response.status_code}")
        print(f"响应时间: {elapsed:.3f}秒")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n结果:")
            print(f"  任务ID: {data.get('task_id', 'N/A')}")
            print(f"  状态: {data.get('status', 'N/A')}")
            metrics = data.get('metrics', {})
            print(f"\n关键指标:")
            print(f"  发电功率: {metrics.get('power_MW', 0):.2f} MW")
            print(f"  运行效率: {metrics.get('efficiency', 0)*100:.1f}%")
            print(f"  水轮机类型: {metrics.get('turbine_type', 'N/A')}")
        else:
            print(f"响应: {response.text}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False


def test_gate_simulation():
    """测试5: 闸门仿真"""
    print("\n" + "="*80)
    print("测试5: 闸门仿真")
    print("="*80)
    
    payload = {
        "gate": {
            "type": "sluice",
            "width": 10.0,
            "opening": 2.0
        },
        "upstream": {"water_depth": 5.0},
        "downstream": {"water_depth": 2.0}
    }
    
    try:
        start = time.time()
        response = requests.post(
            f"{API_BASE}/api/structures/gate",
            json=payload,
            timeout=10
        )
        elapsed = time.time() - start
        
        print(f"状态码: {response.status_code}")
        print(f"响应时间: {elapsed:.3f}秒")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n结果:")
            metrics = data.get('metrics', {})
            print(f"  过闸流量: {metrics.get('discharge', 0):.2f} m³/s")
            print(f"  流态: {metrics.get('flow_regime', 'N/A')}")
            print(f"  闸门类型: {metrics.get('gate_type', 'N/A')}")
            print(f"  闸门宽度: {metrics.get('gate_width', 0):.2f} m")
            print(f"  闸门开度: {metrics.get('gate_opening', 0):.2f} m")
        else:
            print(f"响应: {response.text}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False


def test_valve_simulation():
    """测试6: 阀门仿真 ⭐"""
    print("\n" + "="*80)
    print("测试6: 阀门仿真 ⭐ 市场独有")
    print("="*80)
    
    payload = {
        "valve": {
            "type": "butterfly",
            "diameter": 1.0,
            "opening_percent": 80.0
        },
        "operation": {
            "pressure_drop": 100.0
        }
    }
    
    try:
        start = time.time()
        response = requests.post(
            f"{API_BASE}/api/structures/valve",
            json=payload,
            timeout=10
        )
        elapsed = time.time() - start
        
        print(f"状态码: {response.status_code}")
        print(f"响应时间: {elapsed:.3f}秒")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n结果:")
            metrics = data.get('metrics', {})
            print(f"  流量: {metrics.get('flow_rate_m3s', 0):.2f} m³/s")
            print(f"  阀门类型: {metrics.get('valve_type', 'N/A')}")
            print(f"  开度: {metrics.get('opening_percent', 0):.1f}%")
        else:
            print(f"响应: {response.text}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False


def main():
    """主函数"""
    print("\n" + "="*80)
    print("🚀 HydroClaude 实时API测试")
    print("="*80)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API地址: {API_BASE}")
    print("="*80)
    
    # 检查服务器是否运行
    print("\n检查服务器状态...")
    try:
        response = requests.get(f"{API_BASE}/api/structures/health", timeout=2)
        print("✅ 服务器正在运行")
    except:
        print("❌ 服务器未运行")
        print("\n请先启动服务器:")
        print("  cd /workspace/web")
        print("  ./start_server.sh")
        print("\n或者:")
        print("  cd /workspace/web/backend")
        print("  python3 -m uvicorn api_gateway.main:app --reload --host 0.0.0.0 --port 8000")
        return False
    
    # 运行测试
    tests = [
        ("健康检查", test_health_check),
        ("组件类型", test_structure_types),
        ("泵站仿真", test_pump_simulation),
        ("水轮机仿真", test_turbine_simulation),
        ("闸门仿真", test_gate_simulation),
        ("阀门仿真", test_valve_simulation)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ {name}测试异常: {e}")
            results.append((name, False))
        time.sleep(0.5)
    
    # 总结
    print("\n" + "="*80)
    print("📊 测试总结")
    print("="*80)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\n总测试数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {total - passed}")
    print(f"通过率: {passed/total*100:.1f}%")
    
    print("\n详细结果:")
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {status} - {name}")
    
    print("\n" + "="*80)
    if passed == total:
        print("✅ 所有测试通过！")
    else:
        print(f"⚠️ {total-passed}个测试失败")
    print("="*80)
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
