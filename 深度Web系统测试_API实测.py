#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HydroClaude Web系统深度测试 - API实际调用测试
"""

import requests
import json
import time
from datetime import datetime

# API基础URL
BASE_URL = "http://localhost:8000"

# 测试结果记录
test_results = {
    "timestamp": datetime.now().isoformat(),
    "tests": [],
    "summary": {}
}

def log_test(name, passed, details="", response=None):
    """记录测试结果"""
    result = {
        "name": name,
        "passed": passed,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }
    if response:
        result["response_status"] = response.status_code
        result["response_time"] = response.elapsed.total_seconds()
    test_results["tests"].append(result)
    
    status = " PASS" if passed else " FAIL"
    print(f"{status} | {name}")
    if details:
        print(f"      {details}")
    print()

def test_health_check():
    """测试1: 健康检查"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        passed = response.status_code == 200
        data = response.json() if response.status_code == 200 else {}
        log_test(
            "健康检查 API",
            passed,
            f"状态: {data.get('status', 'unknown')}",
            response
        )
        return passed
    except Exception as e:
        log_test("健康检查 API", False, f"错误: {str(e)}")
        return False

def test_engine_info():
    """测试2: 引擎信息"""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/engine/info", timeout=5)
        passed = response.status_code == 200
        
        if passed:
            data = response.json()
            details = f"引擎版本: {data.get('engine_version', 'unknown')}"
            details += f"\n      求解器数量: Canal={len(data.get('solvers', {}).get('canal', []))}"
            details += f", Pipe={len(data.get('solvers', {}).get('pipe', []))}"
            details += f", Network={len(data.get('solvers', {}).get('network', []))}"
            
            # 检查功能
            features = data.get('features', {})
            details += f"\n      Numba加速: {features.get('numba_acceleration', False)}"
            details += f", 3D可视化: {features.get('3d_visualization', False)}"
        else:
            details = f"HTTP {response.status_code}"
        
        log_test("引擎信息 API", passed, details, response)
        return passed
    except Exception as e:
        log_test("引擎信息 API", False, f"错误: {str(e)}")
        return False

def test_create_simulation():
    """测试3: 创建仿真任务"""
    try:
        # 创建测试仿真配置
        simulation_request = {
            "name": "API深度测试仿真",
            "description": "自动化API测试",
            "config": {
                "width": 10.0,
                "length": 10000.0,
                "n_cells": 100,
                "manning_n": 0.03,
                "slope": 0.001,
                "cfl": 0.9,
                "order": 1,
                "use_numba": True,
                "t_end": 100.0,
                "dt_max": 1.0,
                "output_interval": 10.0,
                "initial_conditions": {
                    "type": "uniform",
                    "h": 2.0,
                    "Q": 50.0
                },
                "boundary_conditions": {
                    "upstream": {"type": "Q", "value": 50.0},
                    "downstream": {"type": "h", "value": 2.0}
                }
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/simulations",
            json=simulation_request,
            timeout=30
        )
        
        passed = response.status_code in [200, 201]
        
        if passed:
            data = response.json()
            task_id = data.get('task_id')
            status = data.get('status')
            details = f"任务ID: {task_id}, 状态: {status}"
            
            # 保存task_id供后续测试使用
            test_results['task_id'] = task_id
        else:
            details = f"HTTP {response.status_code}: {response.text[:200]}"
        
        log_test("创建仿真任务 API", passed, details, response)
        return passed, test_results.get('task_id')
    except Exception as e:
        log_test("创建仿真任务 API", False, f"错误: {str(e)}")
        return False, None

def test_get_simulation_status(task_id):
    """测试4: 获取仿真状态"""
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/simulations/{task_id}/status",
            timeout=5
        )
        
        passed = response.status_code == 200
        
        if passed:
            data = response.json()
            status = data.get('status')
            progress = data.get('progress', 'N/A')
            details = f"状态: {status}, 进度: {progress}"
            
            if 'duration' in data:
                details += f", 耗时: {data['duration']:.2f}s"
        else:
            details = f"HTTP {response.status_code}"
        
        log_test("获取仿真状态 API", passed, details, response)
        return passed, data.get('status') if passed else None
    except Exception as e:
        log_test("获取仿真状态 API", False, f"错误: {str(e)}")
        return False, None

def test_get_simulation_results(task_id):
    """测试5: 获取仿真结果"""
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/simulations/{task_id}/results",
            timeout=10
        )
        
        passed = response.status_code == 200
        
        if passed:
            data = response.json()
            metrics = data.get('metrics', {})
            
            details = f"数据点: {len(data.get('x', []))} cells, {len(data.get('time', []))} timesteps"
            details += f"\n      质量守恒误差: {metrics.get('mass_conservation_error', 0):.6f}%"
            details += f"\n      最大水深: {metrics.get('max_depth', 0):.3f}m"
            details += f", 最大流速: {metrics.get('max_velocity', 0):.3f}m/s"
            details += f"\n      Froude数: {metrics.get('max_froude', 0):.3f}"
            details += f", 收敛: {metrics.get('converged', False)}"
        else:
            details = f"HTTP {response.status_code}"
        
        log_test("获取仿真结果 API", passed, details, response)
        return passed
    except Exception as e:
        log_test("获取仿真结果 API", False, f"错误: {str(e)}")
        return False

def test_list_simulations():
    """测试6: 列出仿真任务"""
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/simulations",
            params={"limit": 10},
            timeout=5
        )
        
        passed = response.status_code == 200
        
        if passed:
            data = response.json()
            count = len(data) if isinstance(data, list) else 0
            details = f"返回 {count} 个仿真任务"
        else:
            details = f"HTTP {response.status_code}"
        
        log_test("列出仿真任务 API", passed, details, response)
        return passed
    except Exception as e:
        log_test("列出仿真任务 API", False, f"错误: {str(e)}")
        return False

def main():
    """主测试流程"""
    print("=" * 80)
    print("HydroClaude Web系统深度测试 - API实际调用测试")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试服务器: {BASE_URL}")
    print("=" * 80)
    print()
    
    # 阶段1: 基础服务测试
    print("【阶段1: 基础服务测试】")
    print("-" * 80)
    test_health_check()
    test_engine_info()
    print()
    
    # 阶段2: 仿真任务测试
    print("【阶段2: 仿真任务测试】")
    print("-" * 80)
    passed, task_id = test_create_simulation()
    
    if passed and task_id:
        # 等待仿真运行
        print("等待仿真运行...")
        max_wait = 60  # 最多等待60秒
        waited = 0
        status = None
        
        while waited < max_wait:
            time.sleep(2)
            waited += 2
            passed_status, status = test_get_simulation_status(task_id)
            
            if status in ['completed', 'failed']:
                break
            
            print(f"      等待中... ({waited}s / {max_wait}s)")
        
        if status == 'completed':
            test_get_simulation_results(task_id)
        else:
            print(f"      ️ 仿真未在{max_wait}秒内完成 (当前状态: {status})")
    print()
    
    # 阶段3: 查询功能测试
    print("【阶段3: 查询功能测试】")
    print("-" * 80)
    test_list_simulations()
    print()
    
    # 生成测试报告
    print("=" * 80)
    print("【测试总结】")
    print("=" * 80)
    
    passed_count = sum(1 for t in test_results['tests'] if t['passed'])
    total_count = len(test_results['tests'])
    success_rate = (passed_count / total_count * 100) if total_count > 0 else 0
    
    test_results['summary'] = {
        "total": total_count,
        "passed": passed_count,
        "failed": total_count - passed_count,
        "success_rate": success_rate
    }
    
    print(f"总测试数: {total_count}")
    print(f"通过: {passed_count}")
    print(f"失败: {total_count - passed_count}")
    print(f"成功率: {success_rate:.1f}%")
    print()
    
    # 保存测试结果
    output_file = "web_test_screenshots/API_test_results.json"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(test_results, f, indent=2, ensure_ascii=False)
        print(f"详细结果已保存到: {output_file}")
    except Exception as e:
        print(f"保存结果失败: {e}")
    
    print("=" * 80)
    print("测试完成!")
    print("=" * 80)
    
    return success_rate >= 80

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)







