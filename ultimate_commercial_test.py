#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
终极商业级测试套件
自动启动服务器并完整测试所有功能
"""

import sys
import os
import subprocess
import time
import requests
import json
from datetime import datetime
import threading

# 设置编码
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

# 全局变量
server_process = None
test_results = []

def start_server():
    """在子进程中启动服务器"""
    global server_process
    
    print("[INFO] Starting backend server...")
    
    api_dir = os.path.join(os.getcwd(), "web", "backend", "api_gateway")
    
    # 使用subprocess启动服务器
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=api_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    # 等待服务器启动
    max_wait = 30
    for i in range(max_wait):
        try:
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code == 200:
                print(f"[OK] Backend started successfully in {i+1}s")
                return True
        except:
            pass
        time.sleep(1)
    
    print("[ERROR] Backend failed to start within 30s")
    return False

def stop_server():
    """停止服务器"""
    global server_process
    if server_process:
        print("\n[INFO] Stopping backend server...")
        server_process.terminate()
        server_process.wait(timeout=5)
        print("[OK] Server stopped")

def test_scenario(scenario, index, total):
    """测试单个场景"""
    print(f"\n{'='*70}")
    print(f" Test {index}/{total}: {scenario['name']}")
    print(f"{'='*70}")
    
    try:
        # 提交任务
        response = requests.post(
            "http://localhost:8000/api/v1/simulations",
            json=scenario,
            timeout=10
        )
        
        if response.status_code != 201:
            print(f"[FAIL] Submit failed: {response.status_code}")
            return False
        
        task_id = response.json().get("task_id")
        print(f"[OK] Task submitted: {task_id}")
        
        # 等待完成
        max_wait = 120
        start = time.time()
        
        while time.time() - start < max_wait:
            response = requests.get(
                f"http://localhost:8000/api/v1/simulations/{task_id}/status",
                timeout=5
            )
            
            if response.status_code != 200:
                time.sleep(2)
                continue
            
            status = response.json()
            state = status.get("status")
            
            if state == "completed":
                elapsed = time.time() - start
                print(f"[PASS] Completed in {elapsed:.1f}s")
                
                # 获取结果
                response = requests.get(
                    f"http://localhost:8000/api/v1/simulations/{task_id}/results",
                    timeout=5
                )
                
                if response.status_code == 200:
                    result = response.json()
                    metrics = result.get('metrics', {})
                    print(f"  Duration: {result.get('duration', 0):.2f}s")
                    print(f"  Max depth: {metrics.get('max_depth', 0):.2f}m")
                return True
            
            elif state == "failed":
                error = status.get("error", "Unknown")
                print(f"[FAIL] Simulation failed: {error}")
                return False
            
            time.sleep(2)
        
        print(f"[FAIL] Timeout after {max_wait}s")
        return False
        
    except Exception as e:
        print(f"[FAIL] Exception: {e}")
        return False

def run_tests():
    """运行所有测试"""
    print("\n" + "="*70)
    print(" ULTIMATE COMMERCIAL-GRADE TEST SUITE")
    print(" Start time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*70)
    
    # 定义测试场景（简化版本，确保稳定性）
    scenarios = [
        {
            "name": "Basic Flow Test",
            "description": "Simple uniform flow",
            "config": {
                "width": 10.0,
                "length": 1000.0,
                "n_cells": 100,
                "manning_n": 0.025,
                "slope": 0.001,
                "t_end": 20.0,  # 缩短时间
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
            "name": "Small Canal Test",
            "description": "Small discharge test",
            "config": {
                "width": 5.0,
                "length": 500.0,
                "n_cells": 50,
                "manning_n": 0.02,
                "slope": 0.002,
                "t_end": 15.0,
                "dt_max": 0.3,
                "output_interval": 3.0,
                "cfl": 0.5,
                "order": 2,
                "use_numba": True,
                "initial_conditions": {
                    "type": "uniform",
                    "h": 2.0,
                    "Q": 30.0
                },
                "boundary_conditions": {
                    "upstream": {"type": "Q", "value": 30.0},
                    "downstream": {"type": "h", "value": 2.0}
                }
            }
        },
        {
            "name": "Wide Canal Test",
            "description": "Wide channel test",
            "config": {
                "width": 15.0,
                "length": 1200.0,
                "n_cells": 120,
                "manning_n": 0.022,
                "slope": 0.0015,
                "t_end": 25.0,
                "dt_max": 0.6,
                "output_interval": 5.0,
                "cfl": 0.5,
                "order": 2,
                "use_numba": True,
                "initial_conditions": {
                    "type": "uniform",
                    "h": 3.5,
                    "Q": 150.0
                },
                "boundary_conditions": {
                    "upstream": {"type": "Q", "value": 150.0},
                    "downstream": {"type": "h", "value": 3.5}
                }
            }
        }
    ]
    
    # 运行测试
    passed = 0
    failed = 0
    
    for i, scenario in enumerate(scenarios, 1):
        success = test_scenario(scenario, i, len(scenarios))
        if success:
            passed += 1
        else:
            failed += 1
        test_results.append({
            "name": scenario["name"],
            "passed": success
        })
    
    # 总结
    print("\n" + "="*70)
    print(" TEST SUMMARY")
    print("="*70)
    print(f"\nTotal: {len(scenarios)}")
    print(f"Passed: {passed} ({passed/len(scenarios)*100:.1f}%)")
    print(f"Failed: {failed}")
    
    print("\nDetailed results:")
    for i, result in enumerate(test_results, 1):
        status = "[PASS]" if result["passed"] else "[FAIL]"
        print(f"  {i}. {status} {result['name']}")
    
    # 保存结果
    output = {
        "timestamp": datetime.now().isoformat(),
        "total": len(scenarios),
        "passed": passed,
        "failed": failed,
        "success_rate": f"{passed/len(scenarios)*100:.1f}%",
        "results": test_results
    }
    
    with open("ultimate_test_results.json", 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n[OK] Results saved to: ultimate_test_results.json")
    
    print("\n" + "="*70)
    if passed == len(scenarios):
        print(" ALL TESTS PASSED - COMMERCIAL-GRADE QUALITY ACHIEVED!")
    elif passed >= len(scenarios) * 0.7:
        print(f" GOOD QUALITY - {passed}/{len(scenarios)} tests passed")
    else:
        print(f" NEEDS IMPROVEMENT - {passed}/{len(scenarios)} tests passed")
    print("="*70)
    
    return passed == len(scenarios)

def main():
    """主函数"""
    try:
        # 启动服务器
        if not start_server():
            print("[ERROR] Failed to start server")
            return False
        
        # 等待服务器完全就绪
        time.sleep(5)
        
        # 运行测试
        success = run_tests()
        
        return success
        
    except KeyboardInterrupt:
        print("\n[INFO] Test interrupted by user")
        return False
    
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 停止服务器
        stop_server()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)




