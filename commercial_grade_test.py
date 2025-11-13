#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
商业级完整测试套件
测试所有7个场景，确保达到商业软件标准
"""

import requests
import time
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

# 定义7个完整的测试场景
SCENARIOS = [
    {
        "name": "Scenario 1: Basic Rectangular Canal",
        "description": "Basic uniform flow in rectangular canal",
        "config": {
            "width": 10.0,
            "length": 1000.0,
            "n_cells": 100,
            "manning_n": 0.025,
            "slope": 0.001,
            "t_end": 50.0,
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
    },
    {
        "name": "Scenario 2: Steep Slope Canal",
        "description": "Flow in steep slope canal",
        "config": {
            "width": 8.0,
            "length": 500.0,
            "n_cells": 100,
            "manning_n": 0.03,
            "slope": 0.01,
            "t_end": 30.0,
            "dt_max": 0.3,
            "output_interval": 3.0,
            "cfl": 0.5,
            "order": 2,
            "use_numba": True,
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
    },
    {
        "name": "Scenario 3: Wide Gentle Canal",
        "description": "Wide canal with gentle slope",
        "config": {
            "width": 20.0,
            "length": 1500.0,
            "n_cells": 150,
            "manning_n": 0.02,
            "slope": 0.0005,
            "t_end": 80.0,
            "dt_max": 0.8,
            "output_interval": 8.0,
            "cfl": 0.5,
            "order": 2,
            "use_numba": True,
            "initial_conditions": {
                "type": "uniform",
                "h": 4.0,
                "Q": 200.0
            },
            "boundary_conditions": {
                "upstream": {"type": "Q", "value": 200.0},
                "downstream": {"type": "h", "value": 4.0}
            }
        }
    },
    {
        "name": "Scenario 4: Small Narrow Canal",
        "description": "Small discharge in narrow canal",
        "config": {
            "width": 3.0,
            "length": 300.0,
            "n_cells": 60,
            "manning_n": 0.015,
            "slope": 0.002,
            "t_end": 20.0,
            "dt_max": 0.2,
            "output_interval": 2.0,
            "cfl": 0.5,
            "order": 2,
            "use_numba": True,
            "initial_conditions": {
                "type": "uniform",
                "h": 1.5,
                "Q": 10.0
            },
            "boundary_conditions": {
                "upstream": {"type": "Q", "value": 10.0},
                "downstream": {"type": "h", "value": 1.5}
            }
        }
    },
    {
        "name": "Scenario 5: Large River Canal",
        "description": "Large discharge wide canal",
        "config": {
            "width": 30.0,
            "length": 2000.0,
            "n_cells": 200,
            "manning_n": 0.028,
            "slope": 0.0008,
            "t_end": 100.0,
            "dt_max": 1.0,
            "output_interval": 10.0,
            "cfl": 0.5,
            "order": 2,
            "use_numba": True,
            "initial_conditions": {
                "type": "uniform",
                "h": 5.0,
                "Q": 500.0
            },
            "boundary_conditions": {
                "upstream": {"type": "Q", "value": 500.0},
                "downstream": {"type": "h", "value": 5.0}
            }
        }
    },
    {
        "name": "Scenario 6: Very Gentle Slope",
        "description": "Canal with very gentle slope",
        "config": {
            "width": 12.0,
            "length": 800.0,
            "n_cells": 100,
            "manning_n": 0.022,
            "slope": 0.0001,
            "t_end": 60.0,
            "dt_max": 0.6,
            "output_interval": 6.0,
            "cfl": 0.5,
            "order": 2,
            "use_numba": True,
            "initial_conditions": {
                "type": "uniform",
                "h": 3.5,
                "Q": 80.0
            },
            "boundary_conditions": {
                "upstream": {"type": "Q", "value": 80.0},
                "downstream": {"type": "h", "value": 3.5}
            }
        }
    },
    {
        "name": "Scenario 7: High Roughness",
        "description": "Canal with high Manning coefficient",
        "config": {
            "width": 15.0,
            "length": 1200.0,
            "n_cells": 120,
            "manning_n": 0.04,
            "slope": 0.003,
            "t_end": 70.0,
            "dt_max": 0.7,
            "output_interval": 7.0,
            "cfl": 0.5,
            "order": 2,
            "use_numba": True,
            "initial_conditions": {
                "type": "uniform",
                "h": 2.5,
                "Q": 150.0
            },
            "boundary_conditions": {
                "upstream": {"type": "Q", "value": 150.0},
                "downstream": {"type": "h", "value": 2.5}
            }
        }
    }
]


def test_health():
    """测试健康端点"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def test_scenario(scenario, index, total):
    """测试单个场景"""
    print(f"\n{'='*70}")
    print(f" Test {index}/{total}: {scenario['name']}")
    print(f"{'='*70}")
    
    # 1. 提交任务
    print("\n[1] Submitting simulation...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/simulations",
            json=scenario,
            timeout=10
        )
        
        if response.status_code != 201:
            print(f"[X] Submit failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
        result = response.json()
        task_id = result.get("task_id")
        print(f"[OK] Task submitted: {task_id}")
        
    except Exception as e:
        print(f"[X] Exception during submission: {e}")
        return False
    
    # 2. 等待完成
    print("\n[2] Waiting for completion...")
    max_wait = 120  # 2分钟超时
    start = time.time()
    
    while time.time() - start < max_wait:
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/simulations/{task_id}/status",
                timeout=5
            )
            
            if response.status_code != 200:
                print(f"[!] Status query failed: {response.status_code}")
                time.sleep(2)
                continue
                
            status = response.json()
            state = status.get("status")
            progress = status.get("progress", 0)
            
            print(f"    Status: {state}, Progress: {progress}%", end="\r")
            
            if state == "completed":
                print(f"\n[OK] Completed in {time.time() - start:.1f}s")
                
                # 获取结果
                response = requests.get(
                    f"{BASE_URL}/api/v1/simulations/{task_id}/results",
                    timeout=5
                )
                
                if response.status_code == 200:
                    result = response.json()
                    metrics = result.get('metrics', {})
                    print(f"    Duration: {result.get('duration', 0):.2f}s")
                    print(f"    Max depth: {metrics.get('max_depth', 0):.2f}m")
                    print(f"    Converged: {metrics.get('converged', False)}")
                    return True
                else:
                    print(f"[!] Results fetch failed: {response.status_code}")
                    return False
            
            elif state == "failed":
                error = status.get("error", "Unknown")
                print(f"\n[X] Simulation failed: {error}")
                return False
            
            time.sleep(2)
            
        except Exception as e:
            print(f"\n[X] Exception while checking status: {e}")
            return False
    
    print(f"\n[!] Timeout after {max_wait}s")
    return False


def main():
    """主测试函数"""
    print("="*70)
    print(" COMMERCIAL-GRADE WEB API TEST SUITE")
    print(" Testing all 7 simulation scenarios")
    print(" Start time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*70)
    
    # 1. 测试健康端点
    print("\n[Step 1] Testing backend health...")
    if test_health():
        print("[OK] Backend is healthy")
    else:
        print("[X] Backend is not responding!")
        print("\nPlease ensure backend is running:")
        print("  cd web/backend/api_gateway")
        print("  python -m uvicorn main:app --host 0.0.0.0 --port 8000")
        return
    
    # 2. 测试所有场景
    print("\n[Step 2] Running all simulation scenarios...")
    
    results = []
    passed = 0
    failed = 0
    
    for i, scenario in enumerate(SCENARIOS, 1):
        success = test_scenario(scenario, i, len(SCENARIOS))
        results.append({
            "name": scenario["name"],
            "passed": success
        })
        if success:
            passed += 1
        else:
            failed += 1
    
    # 3. 总结
    print("\n" + "="*70)
    print(" TEST SUMMARY")
    print("="*70)
    print(f"\nTotal scenarios: {len(SCENARIOS)}")
    print(f"Passed: {passed} ({passed/len(SCENARIOS)*100:.1f}%)")
    print(f"Failed: {failed}")
    
    print("\nDetailed results:")
    for i, result in enumerate(results, 1):
        status = "[PASS]" if result["passed"] else "[FAIL]"
        print(f"  {i}. {status} {result['name']}")
    
    # 保存结果
    output_file = "commercial_test_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total": len(SCENARIOS),
            "passed": passed,
            "failed": failed,
            "success_rate": f"{passed/len(SCENARIOS)*100:.1f}%",
            "results": results
        }, f, indent=2)
    
    print(f"\n[OK] Results saved to: {output_file}")
    
    print("\n" + "="*70)
    if passed == len(SCENARIOS):
        print(" ALL TESTS PASSED! COMMERCIAL-GRADE QUALITY ACHIEVED!")
    elif passed >= len(SCENARIOS) * 0.7:
        print(" GOOD QUALITY - Most tests passed")
    else:
        print(" NEEDS IMPROVEMENT - Many tests failed")
    print("="*70)


if __name__ == "__main__":
    main()






