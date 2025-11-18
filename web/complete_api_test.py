#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整的API端点测试 - 测试所有17个端点
"""

import requests
import json
import time
from datetime import datetime

API_BASE = "http://localhost:8000"

def test_endpoint(name, method, url, payload=None):
    """测试单个端点"""
    print(f"\n{'='*70}")
    print(f"测试: {name}")
    print(f"{'='*70}")
    
    try:
        start = time.time()
        if method == "GET":
            response = requests.get(url, timeout=10)
        else:
            response = requests.post(url, json=payload, timeout=10)
        elapsed = time.time() - start
        
        print(f"方法: {method}")
        print(f"URL: {url}")
        print(f"状态码: {response.status_code}")
        print(f"响应时间: {elapsed:.3f}秒")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功")
            
            # 显示关键指标
            if 'metrics' in data:
                print(f"\n关键指标:")
                for key, value in list(data['metrics'].items())[:5]:
                    print(f"  {key}: {value}")
            elif 'total_components' in data:
                print(f"\n总组件数: {data['total_components']}")
            elif 'status' in data:
                print(f"\n状态: {data['status']}")
            
            return True
        else:
            print(f"❌ 失败: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False


def main():
    print("="*70)
    print("🚀 完整API端点测试 - 测试所有17个端点")
    print("="*70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API地址: {API_BASE}")
    
    # 检查服务器
    try:
        response = requests.get(f"{API_BASE}/health", timeout=2)
        if response.status_code == 200:
            print("\n✅ 服务器正在运行")
        else:
            print("\n❌ 服务器异常")
            return
    except:
        print("\n❌ 服务器未运行，请先启动服务器")
        print("cd /workspace/web/backend && python3 start_server_working.py")
        return
    
    results = []
    
    # 1. 查询端点
    tests = [
        ("健康检查", "GET", f"{API_BASE}/health", None),
        ("组件类型", "GET", f"{API_BASE}/api/structures/types", None),
        ("版本信息", "GET", f"{API_BASE}/api/structures/version", None),
    ]
    
    # 2. 泵站系统
    tests.append((
        "泵站仿真 - 单泵",
        "POST",
        f"{API_BASE}/api/structures/pump",
        {
            "pump": {"flow_rate": 10.0, "head": 15.0, "num_pumps": 1, "pump_type": "single"},
            "upstream": {"water_level": 5.0},
            "downstream": {"elevation": 20.0},
            "operation": {"duration": 100.0}
        }
    ))
    
    tests.append((
        "泵站仿真 - 并联",
        "POST",
        f"{API_BASE}/api/structures/pump",
        {
            "pump": {"flow_rate": 10.0, "head": 15.0, "num_pumps": 2, "pump_type": "parallel"},
            "upstream": {"water_level": 5.0},
            "downstream": {"elevation": 20.0},
            "operation": {"duration": 100.0}
        }
    ))
    
    # 3. 闸门系统
    tests.append((
        "平板闸门",
        "POST",
        f"{API_BASE}/api/structures/gate",
        {
            "gate": {"type": "sluice", "width": 10.0, "opening": 2.0},
            "upstream": {"water_depth": 5.0},
            "downstream": {"water_depth": 2.0}
        }
    ))
    
    tests.append((
        "径向闸门",
        "POST",
        f"{API_BASE}/api/structures/radial-gate",
        {
            "gate": {"width": 10.0, "opening": 2.0, "radius": 8.0},
            "upstream": {"water_depth": 5.0},
            "downstream": {"water_depth": 2.0}
        }
    ))
    
    # 4. 堰系统
    tests.append((
        "宽顶堰",
        "POST",
        f"{API_BASE}/api/structures/weir",
        {
            "weir": {"type": "broad_crested", "crest_width": 10.0, "crest_height": 0.5},
            "upstream": {"water_depth": 2.0},
            "downstream": {"water_depth": 1.0}
        }
    ))
    
    # 5. 水电系统
    tests.append((
        "水轮机 - Francis",
        "POST",
        f"{API_BASE}/api/structures/turbine",
        {
            "turbine": {"type": "francis", "rated_power": 50.0, "rated_head": 100.0, "rated_flow": 60.0},
            "operation": {"head": 100.0, "flow": 60.0}
        }
    ))
    
    tests.append((
        "阀门 - 蝶阀",
        "POST",
        f"{API_BASE}/api/structures/valve",
        {
            "valve": {"type": "butterfly", "diameter": 1.0, "opening_percent": 80.0},
            "operation": {"pressure_drop": 100.0}
        }
    ))
    
    tests.append((
        "调压井",
        "POST",
        f"{API_BASE}/api/structures/surge-tank",
        {
            "surge_tank": {"diameter": 10.0, "height": 50.0},
            "operation": {"initial_level": 25.0, "flow_change": 20.0}
        }
    ))
    
    # 6. 其他结构
    tests.append((
        "涵洞",
        "POST",
        f"{API_BASE}/api/structures/culvert",
        {
            "culvert": {"diameter": 2.0, "length": 50.0, "roughness": 0.013},
            "upstream": {"water_level": 5.0},
            "downstream": {"water_level": 3.0}
        }
    ))
    
    tests.append((
        "桥梁",
        "POST",
        f"{API_BASE}/api/structures/bridge",
        {
            "bridge": {"opening_width": 20.0, "pier_width": 2.0, "num_piers": 2},
            "flow": {"discharge": 100.0, "water_depth": 5.0}
        }
    ))
    
    # 7. 明渠系统
    tests.append((
        "明渠 - 矩形",
        "POST",
        f"{API_BASE}/api/structures/canal",
        {
            "canal": {"shape": "rectangular", "width": 10.0, "slope": 0.001, "roughness": 0.013, "length": 1000.0},
            "flow": {"discharge": 50.0}
        }
    ))
    
    # 8. 组合系统
    tests.append((
        "明渠+泵站",
        "POST",
        f"{API_BASE}/api/structures/canal-with-pump",
        {
            "canal": {"width": 10.0, "slope": 0.001, "roughness": 0.013, "length": 1000.0},
            "pump": {"flow_rate": 10.0, "head": 15.0, "position": 500.0},
            "boundary": {"upstream_depth": 3.0, "downstream_depth": 2.0}
        }
    ))
    
    tests.append((
        "明渠+闸门",
        "POST",
        f"{API_BASE}/api/structures/canal-with-gate",
        {
            "canal": {"width": 10.0, "slope": 0.001, "roughness": 0.013, "length": 1000.0},
            "gate": {"type": "sluice", "width": 10.0, "opening": 2.0, "position": 500.0},
            "boundary": {"upstream_depth": 5.0, "downstream_depth": 2.0}
        }
    ))
    
    tests.append((
        "明渠+堰",
        "POST",
        f"{API_BASE}/api/structures/canal-with-weir",
        {
            "canal": {"width": 10.0, "slope": 0.001, "roughness": 0.013, "length": 1000.0},
            "weir": {"type": "broad_crested", "crest_width": 10.0, "crest_height": 0.5, "position": 500.0},
            "boundary": {"upstream_depth": 3.0}
        }
    ))
    
    # 运行所有测试
    for name, method, url, payload in tests:
        success = test_endpoint(name, method, url, payload)
        results.append((name, success))
        time.sleep(0.2)
    
    # 总结
    print("\n" + "="*70)
    print("📊 测试总结")
    print("="*70)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\n总测试数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {total - passed}")
    print(f"通过率: {passed/total*100:.1f}%")
    
    print("\n详细结果:")
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}")
    
    print("\n" + "="*70)
    if passed == total:
        print("🎉 所有测试通过！系统完全可用！")
    elif passed >= total * 0.8:
        print(f"✅ 大部分测试通过 ({passed}/{total})，系统基本可用")
    else:
        print(f"⚠️ 部分测试失败 ({total-passed}/{total})，需要修复")
    print("="*70)
    
    return passed == total


if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
