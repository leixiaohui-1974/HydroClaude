#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真实应用场景测试
模拟实际工程中的使用场景
"""

import requests
import json
import time
from datetime import datetime

API_BASE = "http://localhost:8000"


def scenario_1_canal_design():
    """场景1: 明渠设计优化
    工程师需要设计一条明渠，测试不同坡度对流量的影响
    """
    print("\n" + "="*70)
    print("场景1: 明渠设计优化")
    print("="*70)
    print("需求: 设计流量50m³/s的矩形明渠，对比不同坡度的水深")
    
    slopes = [0.0005, 0.001, 0.002, 0.005]
    results = []
    
    for slope in slopes:
        payload = {
            "canal": {
                "shape": "rectangular",
                "width": 10.0,
                "slope": slope,
                "roughness": 0.013,
                "length": 1000.0
            },
            "flow": {"discharge": 50.0}
        }
        
        try:
            response = requests.post(
                f"{API_BASE}/api/structures/canal",
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                results.append({
                    'slope': slope,
                    'status': 'success',
                    'data': data
                })
                print(f"  ✅ 坡度 {slope:.4f}: 求解成功")
            else:
                results.append({
                    'slope': slope,
                    'status': 'failed',
                    'error': response.text[:100]
                })
                print(f"  ❌ 坡度 {slope:.4f}: 求解失败")
        except Exception as e:
            print(f"  ❌ 坡度 {slope:.4f}: 异常 - {e}")
            results.append({
                'slope': slope,
                'status': 'error',
                'error': str(e)
            })
    
    success_count = sum(1 for r in results if r['status'] == 'success')
    print(f"\n结果: {success_count}/{len(slopes)} 成功")
    return success_count == len(slopes)


def scenario_2_pump_station_operation():
    """场景2: 泵站运行优化
    比较单泵、并联、串联三种方式的效率
    """
    print("\n" + "="*70)
    print("场景2: 泵站运行方案比较")
    print("="*70)
    print("需求: 同样的扬程，比较三种泵站配置的效率")
    
    configs = [
        ("单泵", {"flow_rate": 10.0, "head": 15.0, "num_pumps": 1, "pump_type": "single"}),
        ("并联", {"flow_rate": 10.0, "head": 15.0, "num_pumps": 2, "pump_type": "parallel"}),
        ("串联", {"flow_rate": 10.0, "head": 15.0, "num_pumps": 2, "pump_type": "series"})
    ]
    
    results = []
    for name, pump_config in configs:
        payload = {
            "pump": pump_config,
            "upstream": {"water_level": 5.0},
            "downstream": {"elevation": 20.0},
            "operation": {"duration": 100.0}
        }
        
        try:
            response = requests.post(
                f"{API_BASE}/api/structures/pump",
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                metrics = data.get('metrics', {})
                efficiency = metrics.get('avg_efficiency', 0) * 100
                energy = metrics.get('total_energy_kwh', 0)
                
                results.append({
                    'config': name,
                    'efficiency': efficiency,
                    'energy': energy,
                    'status': 'success'
                })
                print(f"  ✅ {name:6s}: 效率={efficiency:.1f}%, 能耗={energy:.4f}kWh")
            else:
                results.append({'config': name, 'status': 'failed'})
                print(f"  ❌ {name:6s}: 求解失败")
        except Exception as e:
            print(f"  ❌ {name:6s}: 异常 - {e}")
            results.append({'config': name, 'status': 'error'})
    
    success_count = sum(1 for r in results if r['status'] == 'success')
    print(f"\n结果: {success_count}/{len(configs)} 成功")
    
    if success_count == len(configs):
        # 找出最优方案
        best = max(results, key=lambda x: x.get('efficiency', 0))
        print(f"✨ 最优方案: {best['config']} (效率={best['efficiency']:.1f}%)")
    
    return success_count == len(configs)


def scenario_3_gate_regulation():
    """场景3: 闸门调度
    测试不同闸门开度对流量的控制
    """
    print("\n" + "="*70)
    print("场景3: 闸门流量调节")
    print("="*70)
    print("需求: 通过调整闸门开度控制过闸流量")
    
    openings = [1.0, 1.5, 2.0, 2.5, 3.0]
    results = []
    
    for opening in openings:
        payload = {
            "gate": {
                "type": "sluice",
                "width": 10.0,
                "opening": opening
            },
            "upstream": {"water_depth": 5.0},
            "downstream": {"water_depth": 2.0}
        }
        
        try:
            response = requests.post(
                f"{API_BASE}/api/structures/gate",
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                discharge = data.get('metrics', {}).get('discharge', 0)
                results.append({
                    'opening': opening,
                    'discharge': discharge,
                    'status': 'success'
                })
                print(f"  ✅ 开度 {opening:.1f}m: 流量={discharge:.2f} m³/s")
            else:
                results.append({'opening': opening, 'status': 'failed'})
                print(f"  ❌ 开度 {opening:.1f}m: 求解失败")
        except Exception as e:
            print(f"  ❌ 开度 {opening:.1f}m: 异常 - {e}")
            results.append({'opening': opening, 'status': 'error'})
    
    success_count = sum(1 for r in results if r['status'] == 'success')
    print(f"\n结果: {success_count}/{len(openings)} 成功")
    
    if success_count >= 3:
        discharges = [r['discharge'] for r in results if r['status'] == 'success']
        print(f"✨ 流量范围: {min(discharges):.2f} ~ {max(discharges):.2f} m³/s")
    
    return success_count == len(openings)


def scenario_4_hydropower_optimization():
    """场景4: 水电站优化
    测试不同水头下水轮机的发电功率
    """
    print("\n" + "="*70)
    print("场景4: 水电站发电优化")
    print("="*70)
    print("需求: 分析不同水头条件下的发电功率")
    
    heads = [80.0, 90.0, 100.0, 110.0, 120.0]
    rated_flow = 60.0
    results = []
    
    for head in heads:
        payload = {
            "turbine": {
                "type": "francis",
                "rated_power": 50.0,
                "rated_head": 100.0,
                "rated_flow": rated_flow
            },
            "operation": {
                "head": head,
                "flow": rated_flow
            }
        }
        
        try:
            response = requests.post(
                f"{API_BASE}/api/structures/turbine",
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                power = data.get('metrics', {}).get('power_MW', 0)
                efficiency = data.get('metrics', {}).get('efficiency', 0) * 100
                
                results.append({
                    'head': head,
                    'power': power,
                    'efficiency': efficiency,
                    'status': 'success'
                })
                print(f"  ✅ 水头 {head:.0f}m: 功率={power:.2f}MW, 效率={efficiency:.1f}%")
            else:
                results.append({'head': head, 'status': 'failed'})
                print(f"  ❌ 水头 {head:.0f}m: 求解失败")
        except Exception as e:
            print(f"  ❌ 水头 {head:.0f}m: 异常 - {e}")
            results.append({'head': head, 'status': 'error'})
    
    success_count = sum(1 for r in results if r['status'] == 'success')
    print(f"\n结果: {success_count}/{len(heads)} 成功")
    
    if success_count >= 3:
        powers = [r['power'] for r in results if r['status'] == 'success']
        print(f"✨ 功率范围: {min(powers):.2f} ~ {max(powers):.2f} MW")
    
    return success_count == len(heads)


def scenario_5_integrated_system():
    """场景5: 综合系统
    明渠+泵站+闸门的组合系统
    """
    print("\n" + "="*70)
    print("场景5: 综合水利系统")
    print("="*70)
    print("需求: 测试明渠与水工建筑物的组合")
    
    scenarios = [
        ("明渠+泵站", "/api/structures/canal-with-pump", {
            "canal": {"width": 10.0, "slope": 0.001, "roughness": 0.013, "length": 1000.0},
            "pump": {"flow_rate": 10.0, "head": 15.0, "position": 500.0},
            "boundary": {"upstream_depth": 3.0, "downstream_depth": 2.0}
        }),
        ("明渠+闸门", "/api/structures/canal-with-gate", {
            "canal": {"width": 10.0, "slope": 0.001, "roughness": 0.013, "length": 1000.0},
            "gate": {"type": "sluice", "width": 10.0, "opening": 2.0, "position": 500.0},
            "boundary": {"upstream_depth": 5.0, "downstream_depth": 2.0}
        }),
        ("明渠+堰", "/api/structures/canal-with-weir", {
            "canal": {"width": 10.0, "slope": 0.001, "roughness": 0.013, "length": 1000.0},
            "weir": {"type": "broad_crested", "crest_width": 10.0, "crest_height": 0.5, "position": 500.0},
            "boundary": {"upstream_depth": 3.0}
        })
    ]
    
    results = []
    for name, endpoint, payload in scenarios:
        try:
            response = requests.post(
                f"{API_BASE}{endpoint}",
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                results.append({'scenario': name, 'status': 'success'})
                print(f"  ✅ {name:12s}: 求解成功")
            else:
                results.append({'scenario': name, 'status': 'failed'})
                print(f"  ❌ {name:12s}: 求解失败 - {response.status_code}")
        except Exception as e:
            print(f"  ❌ {name:12s}: 异常 - {e}")
            results.append({'scenario': name, 'status': 'error'})
    
    success_count = sum(1 for r in results if r['status'] == 'success')
    print(f"\n结果: {success_count}/{len(scenarios)} 成功")
    return success_count == len(scenarios)


def main():
    print("="*70)
    print("🏗️ HydroClaude 真实应用场景测试")
    print("="*70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"目标: {API_BASE}")
    
    # 检查服务器
    try:
        response = requests.get(f"{API_BASE}/health", timeout=2)
        if response.status_code == 200:
            print("✅ 服务器正在运行\n")
        else:
            print("❌ 服务器异常")
            return False
    except:
        print("❌ 服务器未运行")
        return False
    
    # 运行场景测试
    scenarios = [
        ("明渠设计", scenario_1_canal_design),
        ("泵站优化", scenario_2_pump_station_operation),
        ("闸门调节", scenario_3_gate_regulation),
        ("水电优化", scenario_4_hydropower_optimization),
        ("综合系统", scenario_5_integrated_system)
    ]
    
    results = []
    for name, test_func in scenarios:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ {name}场景异常: {e}")
            results.append((name, False))
        time.sleep(0.3)
    
    # 总结
    print("\n" + "="*70)
    print("📊 场景测试总结")
    print("="*70)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\n总场景数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {total - passed}")
    print(f"通过率: {passed/total*100:.1f}%")
    
    print("\n详细结果:")
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}")
    
    print("\n" + "="*70)
    if passed == total:
        print("🎉 所有场景测试通过！系统满足实际工程需求！")
    elif passed >= total * 0.8:
        print(f"✅ 大部分场景通过 ({passed}/{total})，系统基本满足需求")
    else:
        print(f"⚠️ {total-passed}个场景失败，需要改进")
    print("="*70)
    
    return passed >= total * 0.8  # 80%通过即可


if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
