#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
直接测试仿真API，查看详细的错误信息
"""

import requests
import json
import time

BACKEND_URL = "http://localhost:8000"

print("=" * 80)
print("Testing Simulation API Directly")
print("=" * 80)

# 准备测试数据
simulation_request = {
    "name": "API直接测试仿真",
    "description": "测试仿真API是否正常工作",
    "config": {
        "width": 10.0,
        "length": 1000.0,
        "n_cells": 100,
        "manning_n": 0.025,
        "slope": 0.001,
        "t_end": 10.0,
        "dt_max": 0.1,
        "output_interval": 0.5,
        "initial_conditions": {
            "type": "uniform",
            "h": 5.0,
            "Q": 0.0
        },
        "boundary_conditions": {
            "upstream": {
                "type": "h",
                "value": 5.0
            },
            "downstream": {
                "type": "h",
                "value": 5.0
            }
        }
    }
}

print("\n[Step 1] Testing POST /api/v1/simulations")
print("-" * 80)
print("Request payload:")
print(json.dumps(simulation_request, indent=2))

try:
    response = requests.post(
        f"{BACKEND_URL}/api/v1/simulations",
        json=simulation_request,
        timeout=30
    )
    
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        print("\n[SUCCESS] Simulation created!")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        task_id = result.get('task_id')
        print(f"\nTask ID: {task_id}")
        
        # 轮询状态
        print("\n[Step 2] Polling simulation status...")
        print("-" * 80)
        
        for i in range(20):  # 最多等待20秒
            time.sleep(1)
            
            status_response = requests.get(
                f"{BACKEND_URL}/api/v1/simulations/{task_id}/status",
                timeout=5
            )
            
            if status_response.status_code == 200:
                status = status_response.json()
                print(f"[{i+1}s] Status: {status.get('status')} - {status.get('progress', 0):.1f}%")
                
                if status.get('status') == 'completed':
                    print("\n[SUCCESS] Simulation completed!")
                    
                    # 获取结果
                    print("\n[Step 3] Fetching results...")
                    print("-" * 80)
                    
                    results_response = requests.get(
                        f"{BACKEND_URL}/api/v1/simulations/{task_id}/results",
                        timeout=5
                    )
                    
                    if results_response.status_code == 200:
                        results = results_response.json()
                        print(f"Results keys: {list(results.keys())}")
                        print(f"Task ID: {results.get('task_id')}")
                        print(f"Status: {results.get('status')}")
                        
                        if 'metrics' in results:
                            print(f"\nMetrics:")
                            for key, value in results['metrics'].items():
                                print(f"  {key}: {value}")
                        
                        if 'time' in results:
                            print(f"\nTime steps: {len(results['time'])}")
                        if 'x' in results:
                            print(f"Spatial points: {len(results['x'])}")
                        if 'h' in results:
                            print(f"Water depth data: {len(results['h'])} time steps")
                    else:
                        print(f"[ERROR] Failed to get results: {results_response.status_code}")
                        print(results_response.text)
                    
                    break
                
                elif status.get('status') == 'failed':
                    print(f"\n[ERROR] Simulation failed!")
                    print(f"Error: {status.get('error')}")
                    break
        else:
            print("\n[TIMEOUT] Simulation did not complete in 20 seconds")
    
    else:
        print("\n[ERROR] Failed to create simulation!")
        print(f"Response: {response.text}")
        
        # 尝试解析JSON错误
        try:
            error_data = response.json()
            print(f"\nError details: {json.dumps(error_data, indent=2)}")
        except:
            pass

except requests.exceptions.Timeout:
    print("\n[ERROR] Request timeout!")
except requests.exceptions.ConnectionError:
    print("\n[ERROR] Connection error! Is the backend running?")
except Exception as e:
    print(f"\n[ERROR] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("Test Complete")
print("=" * 80)







