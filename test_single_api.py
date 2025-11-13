#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
单场景API测试
"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"

def test_single_scenario():
    """测试单个简单场景"""
    
    scenario = {
        "name": "Simple Test",
        "description": "Basic test case",
        "config": {
            "width": 10.0,
            "length": 1000.0,
            "n_cells": 100,
            "manning_n": 0.025,
            "slope": 0.001,
            "t_end": 10.0,  # 短时间
            "dt_max": 0.5,
            "output_interval": 5.0,
            "cfl": 0.5,
            "order": 2,
            "use_numba": True,
            "initial_conditions": {
                "type": "uniform",
                "h": 3.0,
                "Q": 100.0
            },
            "boundary_conditions": {
                "upstream": {"type": "Q", "value": 100.0},
                "downstream": {"type": "h", "value": 3.0}
            }
        }
    }
    
    print("="*60)
    print(" Single Scenario API Test")
    print("="*60)
    
    # 1. 提交任务
    print("\n[1] Submitting simulation...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/simulations",
            json=scenario,
            timeout=10
        )
        
        if response.status_code == 201:
            result = response.json()
            task_id = result.get("task_id")
            print(f"[OK] Task submitted: {task_id}")
        else:
            print(f"[!] Submit failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"[X] Exception: {e}")
        return False
    
    # 2. 等待完成
    print("\n[2] Waiting for completion...")
    max_wait = 30
    start = time.time()
    
    while time.time() - start < max_wait:
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/simulations/{task_id}/status",
                timeout=5
            )
            
            if response.status_code == 200:
                status = response.json()
                state = status.get("status")
                
                print(f"    Status: {state}, Progress: {status.get('progress', 0)}%")
                
                if state == "completed":
                    print(f"[OK] Completed in {time.time() - start:.1f}s")
                    
                    # 获取结果
                    print("\n[3] Fetching results...")
                    response = requests.get(
                        f"{BASE_URL}/api/v1/simulations/{task_id}/results",
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        print(f"[OK] Results retrieved")
                        print(f"    Duration: {result.get('duration')}s")
                        metrics = result.get('metrics', {})
                        print(f"    Max depth: {metrics.get('max_depth')}m")
                        print(f"    Converged: {metrics.get('converged')}")
                        return True
                    else:
                        print(f"[!] Results fetch failed: {response.status_code}")
                        return False
                
                elif state == "failed":
                    error = status.get("error", "Unknown")
                    print(f"[X] Simulation failed: {error}")
                    return False
                
                time.sleep(2)
            else:
                print(f"[!] Status query failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"[X] Exception while checking status: {e}")
            return False
    
    print(f"[!] Timeout after {max_wait}s")
    return False

if __name__ == "__main__":
    success = test_single_scenario()
    
    print("\n" + "="*60)
    if success:
        print(" TEST PASSED!")
    else:
        print(" TEST FAILED!")
    print("="*60)






