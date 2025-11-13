#!/usr/bin/env python3
"""
手动测试脚本 - 不使用浏览器，直接测试API
"""

import requests
import json
import time
from datetime import datetime

print("=" * 70)
print("HydroClaude Web API 手动测试")
print("=" * 70)
print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

results = {}

# 测试1: 健康检查
print("[1/6] 测试: 健康检查")
try:
    response = requests.get("http://127.0.0.1:8000/health", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"    成功 - 服务: {data.get('service')}, 版本: {data.get('version')}")
        results['健康检查'] = True
    else:
        print(f"    失败 - 状态码: {response.status_code}")
        results['健康检查'] = False
except Exception as e:
    print(f"    失败 - {str(e)}")
    results['健康检查'] = False

time.sleep(1)

# 测试2: 引擎信息
print("\n[2/6] 测试: 引擎信息")
try:
    response = requests.get("http://127.0.0.1:8000/api/v1/engine/info", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"    成功 - 引擎版本: {data.get('engine_version')}")
        print(f"   Numba加速: {data.get('features', {}).get('numba_acceleration')}")
        results['引擎信息'] = True
    else:
        print(f"    失败 - 状态码: {response.status_code}")
        results['引擎信息'] = False
except Exception as e:
    print(f"    失败 - {str(e)}")
    results['引擎信息'] = False

time.sleep(1)

# 测试3: 创建仿真
print("\n[3/6] 测试: 创建仿真")
test_config = {
    "name": "API手动测试",
    "description": "测试仿真创建",
    "config": {
        "width": 10.0,
        "length": 1000.0,
        "n_cells": 100,
        "manning_n": 0.025,
        "slope": 0.001,
        "t_end": 30.0,
        "dt_max": 1.0,
        "output_interval": 1.0,
        "cfl": 0.5,
        "order": 2,
        "initial_conditions": {
            "type": "uniform",
            "h": 5.0,
            "Q": 0.0
        },
        "boundary_conditions": {
            "upstream": {"type": "h", "value": 5.0},
            "downstream": {"type": "h", "value": 5.0}
        }
    }
}

task_id = None
try:
    response = requests.post(
        "http://127.0.0.1:8000/api/v1/simulations",
        json=test_config,
        timeout=30
    )
    if response.status_code in [200, 201]:
        data = response.json()
        task_id = data.get('task_id')
        print(f"    成功 - 任务ID: {task_id}")
        results['创建仿真'] = True
    else:
        print(f"    失败 - 状态码: {response.status_code}")
        print(f"   响应: {response.text[:200]}")
        results['创建仿真'] = False
except Exception as e:
    print(f"    失败 - {str(e)}")
    results['创建仿真'] = False

time.sleep(2)

# 测试4: 查询状态
if task_id:
    print("\n[4/6] 测试: 查询仿真状态")
    try:
        response = requests.get(
            f"http://127.0.0.1:8000/api/v1/simulations/{task_id}/status",
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            status = data.get('status')
            print(f"    成功 - 状态: {status}")
            results['查询状态'] = True
        else:
            print(f"    失败 - 状态码: {response.status_code}")
            results['查询状态'] = False
    except Exception as e:
        print(f"    失败 - {str(e)}")
        results['查询状态'] = False
    
    # 等待仿真完成
    print("\n   等待仿真完成...", end="", flush=True)
    for i in range(30):
        try:
            response = requests.get(
                f"http://127.0.0.1:8000/api/v1/simulations/{task_id}/status",
                timeout=5
            )
            if response.status_code == 200:
                status = response.json().get('status')
                if status == 'completed':
                    print(f" 完成！(耗时 ~{i}秒)")
                    break
                elif status == 'failed':
                    print(f" 失败！")
                    break
                else:
                    print(".", end="", flush=True)
            time.sleep(1)
        except:
            break
    print()
    
    time.sleep(1)
    
    # 测试5: 获取结果
    print("\n[5/6] 测试: 获取仿真结果")
    try:
        response = requests.get(
            f"http://127.0.0.1:8000/api/v1/simulations/{task_id}/results",
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            results_data = data.get('results', {})
            print(f"    成功")
            print(f"   时间点数: {len(results_data.get('time', []))}")
            print(f"   空间点数: {len(results_data.get('x', []))}")
            
            if 'metrics' in results_data:
                metrics = results_data['metrics']
                mass_error = metrics.get('mass_conservation_error', 0)
                print(f"   质量守恒误差: {mass_error:.2e}")
            
            results['获取结果'] = True
        else:
            print(f"    失败 - 状态码: {response.status_code}")
            results['获取结果'] = False
    except Exception as e:
        print(f"    失败 - {str(e)}")
        results['获取结果'] = False
    
    time.sleep(1)
    
    # 测试6: 删除仿真
    print("\n[6/6] 测试: 删除仿真")
    try:
        response = requests.delete(
            f"http://127.0.0.1:8000/api/v1/simulations/{task_id}",
            timeout=5
        )
        if response.status_code in [200, 204]:
            print(f"    成功 - 仿真已删除")
            results['删除仿真'] = True
        else:
            print(f"    失败 - 状态码: {response.status_code}")
            results['删除仿真'] = False
    except Exception as e:
        print(f"    失败 - {str(e)}")
        results['删除仿真'] = False
else:
    print("\n[4/6] 测试: 查询仿真状态 - 跳过（无任务ID）")
    print("[5/6] 测试: 获取仿真结果 - 跳过（无任务ID）")
    print("[6/6] 测试: 删除仿真 - 跳过（无任务ID）")
    results['查询状态'] = False
    results['获取结果'] = False
    results['删除仿真'] = False

# 统计结果
print("\n" + "=" * 70)
print("测试结果汇总")
print("=" * 70)

total = len(results)
passed = sum(1 for v in results.values() if v)
failed = total - passed

for name, result in results.items():
    status = " PASS" if result else " FAIL"
    print(f"{name:20s} {status}")

print(f"\n总计: {total}")
print(f"通过: {passed}")
print(f"失败: {failed}")
print(f"成功率: {passed/total*100:.1f}%")

# 保存结果
report = {
    "timestamp": datetime.now().isoformat(),
    "total": total,
    "passed": passed,
    "failed": failed,
    "success_rate": passed/total*100,
    "results": {k: ("PASS" if v else "FAIL") for k, v in results.items()}
}

with open("/workspace/web/api_test_report.json", "w") as f:
    json.dump(report, f, indent=2)

print(f"\n 测试报告已保存: api_test_report.json")

# 返回退出码
exit(0 if passed == total else 1)
