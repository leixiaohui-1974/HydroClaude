#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
继续仿真测试 - 修复编码问题
避免emoji字符，完成所有仿真场景测试
"""

import requests
import json
import time
import sys
import io

# 设置UTF-8编码输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BACKEND_URL = "http://localhost:8000"

# 测试场景（避免emoji和特殊字符）
TEST_SCENARIOS = {
    "uniform_flow": {
        "name": "Test-UniformFlow",
        "config": {
            "width": 10.0,
            "length": 1000.0,
            "n_cells": 100,
            "manning_n": 0.025,
            "slope": 0.001,
            "t_end": 10.0,
            "dt_max": 0.1,
            "output_interval": 0.5,
            "initial_conditions": {"type": "uniform", "h": 5.0, "Q": 0.0},
            "boundary_conditions": {
                "upstream": {"type": "h", "value": 5.0},
                "downstream": {"type": "h", "value": 5.0}
            }
        }
    },
    "dam_break": {
        "name": "Test-DamBreak",
        "config": {
            "width": 10.0,
            "length": 1000.0,
            "n_cells": 100,
            "manning_n": 0.025,
            "slope": 0.0,
            "t_end": 20.0,
            "dt_max": 0.05,
            "output_interval": 0.5,
            "initial_conditions": {
                "type": "dam_break",
                "dam_position": 500.0,
                "h_left": 10.0,
                "h_right": 1.0,
                "Q_left": 0.0,
                "Q_right": 0.0
            },
            "boundary_conditions": {
                "upstream": {"type": "h", "value": 10.0},
                "downstream": {"type": "h", "value": 1.0}
            }
        }
    },
    "flow_boundary": {
        "name": "Test-FlowBoundary",
        "config": {
            "width": 10.0,
            "length": 1000.0,
            "n_cells": 100,
            "manning_n": 0.025,
            "slope": 0.001,
            "t_end": 15.0,
            "dt_max": 0.1,
            "output_interval": 0.5,
            "initial_conditions": {"type": "uniform", "h": 3.0, "Q": 50.0},
            "boundary_conditions": {
                "upstream": {"type": "Q", "value": 50.0},
                "downstream": {"type": "h", "value": 3.0}
            }
        }
    },
    "steep_slope": {
        "name": "Test-SteepSlope",
        "config": {
            "width": 5.0,
            "length": 500.0,
            "n_cells": 50,
            "manning_n": 0.02,
            "slope": 0.01,
            "t_end": 10.0,
            "dt_max": 0.05,
            "output_interval": 0.5,
            "initial_conditions": {"type": "uniform", "h": 2.0, "Q": 10.0},
            "boundary_conditions": {
                "upstream": {"type": "Q", "value": 10.0},
                "downstream": {"type": "h", "value": 1.5}
            }
        }
    },
    "wide_channel": {
        "name": "Test-WideChannel",
        "config": {
            "width": 50.0,
            "length": 2000.0,
            "n_cells": 200,
            "manning_n": 0.03,
            "slope": 0.0005,
            "t_end": 30.0,
            "dt_max": 0.2,
            "output_interval": 1.0,
            "initial_conditions": {"type": "uniform", "h": 8.0, "Q": 200.0},
            "boundary_conditions": {
                "upstream": {"type": "Q", "value": 200.0},
                "downstream": {"type": "h", "value": 8.0}
            }
        }
    }
}

results = {"total": 0, "passed": 0, "failed": 0, "details": []}

def test_simulation(scenario_id, scenario):
    """测试单个仿真场景"""
    print(f"\n{'='*60}")
    print(f"Testing: {scenario['name']}")
    print(f"{'='*60}")
    
    results["total"] += 1
    
    try:
        # 创建仿真
        payload = {
            "name": scenario['name'],
            "description": f"Automated test - {scenario_id}",
            "config": scenario['config']
        }
        
        print(f"[1/4] Creating simulation...")
        response = requests.post(
            f"{BACKEND_URL}/api/v1/simulations",
            json=payload,
            timeout=30
        )
        
        print(f"      Status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            task_id = data.get('task_id')
            print(f"      Task ID: {task_id}")
            
            # 轮询状态
            print(f"\n[2/4] Monitoring simulation...")
            max_wait = 60  # 最多等待60秒
            
            for i in range(max_wait):
                time.sleep(1)
                
                try:
                    status_resp = requests.get(
                        f"{BACKEND_URL}/api/v1/simulations/{task_id}/status",
                        timeout=5
                    )
                    
                    if status_resp.status_code == 200:
                        status = status_resp.json()
                        current_status = status.get('status')
                        progress = status.get('progress', 0)
                        
                        if i % 5 == 0 or current_status in ['completed', 'failed']:
                            print(f"      [{i+1}s] Status: {current_status}, Progress: {progress:.1f}%")
                        
                        if current_status == 'completed':
                            print(f"\n[3/4] Fetching results...")
                            
                            # 获取结果
                            results_resp = requests.get(
                                f"{BACKEND_URL}/api/v1/simulations/{task_id}/results",
                                timeout=10
                            )
                            
                            if results_resp.status_code == 200:
                                result_data = results_resp.json()
                                
                                print(f"[4/4] Analyzing results...")
                                print(f"      Task ID: {result_data.get('task_id')}")
                                print(f"      Status: {result_data.get('status')}")
                                
                                if 'time' in result_data:
                                    print(f"      Time steps: {len(result_data['time'])}")
                                if 'x' in result_data:
                                    print(f"      Spatial points: {len(result_data['x'])}")
                                if 'h' in result_data:
                                    print(f"      Water depth data: {len(result_data['h'])} time steps")
                                if 'Q' in result_data:
                                    print(f"      Flow rate data: {len(result_data['Q'])} time steps")
                                if 'metrics' in result_data:
                                    print(f"      Metrics available: {list(result_data['metrics'].keys())}")
                                
                                print(f"\n[SUCCESS] Simulation completed in {i+1}s")
                                results["passed"] += 1
                                results["details"].append({
                                    "scenario": scenario['name'],
                                    "status": "pass",
                                    "duration": i+1,
                                    "time_steps": len(result_data.get('time', [])),
                                    "spatial_points": len(result_data.get('x', []))
                                })
                                return True
                            else:
                                print(f"[ERROR] Failed to get results: {results_resp.status_code}")
                                print(f"        Response: {results_resp.text[:200]}")
                                results["failed"] += 1
                                results["details"].append({
                                    "scenario": scenario['name'],
                                    "status": "fail",
                                    "error": "Failed to fetch results"
                                })
                                return False
                        
                        elif current_status == 'failed':
                            error_msg = status.get('error', 'Unknown error')
                            print(f"\n[ERROR] Simulation failed: {error_msg}")
                            results["failed"] += 1
                            results["details"].append({
                                "scenario": scenario['name'],
                                "status": "fail",
                                "error": error_msg
                            })
                            return False
                    
                    else:
                        print(f"      [Warning] Status check returned {status_resp.status_code}")
                
                except Exception as e:
                    print(f"      [Warning] Status check error: {str(e)[:100]}")
                    continue
            
            # 超时
            print(f"\n[TIMEOUT] Simulation did not complete in {max_wait}s")
            results["failed"] += 1
            results["details"].append({
                "scenario": scenario['name'],
                "status": "fail",
                "error": f"Timeout after {max_wait}s"
            })
            return False
        
        else:
            print(f"[ERROR] Failed to create simulation")
            print(f"        Response: {response.text[:200]}")
            results["failed"] += 1
            results["details"].append({
                "scenario": scenario['name'],
                "status": "fail",
                "error": f"Create failed: {response.status_code}"
            })
            return False
    
    except Exception as e:
        print(f"[ERROR] Exception: {str(e)}")
        results["failed"] += 1
        results["details"].append({
            "scenario": scenario['name'],
            "status": "fail",
            "error": str(e)
        })
        return False

def main():
    print("="*80)
    print("Simulation Scenarios Testing - Fixed Encoding")
    print("="*80)
    
    start_time = time.time()
    
    # 测试所有场景
    for scenario_id, scenario in TEST_SCENARIOS.items():
        test_simulation(scenario_id, scenario)
    
    # 打印总结
    duration = time.time() - start_time
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Total Tests: {results['total']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Success Rate: {(results['passed']/results['total']*100):.1f}%")
    print(f"Duration: {duration:.1f}s")
    
    print("\nDetails:")
    for detail in results['details']:
        status_icon = "[PASS]" if detail['status'] == 'pass' else "[FAIL]"
        print(f"  {status_icon} {detail['scenario']}")
        if 'duration' in detail:
            print(f"        Duration: {detail['duration']}s")
        if 'error' in detail:
            print(f"        Error: {detail['error']}")
    
    # 保存结果
    with open('simulation_test_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to: simulation_test_results.json")
    print("="*80)

if __name__ == '__main__':
    main()







