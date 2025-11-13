#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HydroClaude Web System Deep Test - Real API Testing
真正的Web系统深度测试 - API实际调用
"""

import requests
import json
import time
from datetime import datetime

# API Base URL
BASE_URL = "http://localhost:8000"

# Test results storage
test_results = {
    "timestamp": datetime.now().isoformat(),
    "tests": [],
    "summary": {}
}

def log_test(name, passed, details="", response=None):
    """Log test results"""
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
    
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name}")
    if details:
        print(f"       {details}")
    print()

def test_health_check():
    """Test 1: Health Check API"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        passed = response.status_code == 200
        data = response.json() if response.status_code == 200 else {}
        log_test(
            "Health Check API",
            passed,
            f"Status: {data.get('status', 'unknown')}",
            response
        )
        return passed
    except Exception as e:
        log_test("Health Check API", False, f"Error: {str(e)}")
        return False

def test_engine_info():
    """Test 2: Engine Info API"""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/engine/info", timeout=5)
        passed = response.status_code == 200
        
        if passed:
            data = response.json()
            details = f"Engine Version: {data.get('engine_version', 'unknown')}"
            details += f"\n       Solvers: Canal={len(data.get('solvers', {}).get('canal', []))}"
            details += f", Pipe={len(data.get('solvers', {}).get('pipe', []))}"
            details += f", Network={len(data.get('solvers', {}).get('network', []))}"
            
            # Check features
            features = data.get('features', {})
            details += f"\n       Features: Numba={features.get('numba_acceleration', False)}"
            details += f", 3D Viz={features.get('3d_visualization', False)}"
        else:
            details = f"HTTP {response.status_code}"
        
        log_test("Engine Info API", passed, details, response)
        return passed
    except Exception as e:
        log_test("Engine Info API", False, f"Error: {str(e)}")
        return False

def test_create_simulation():
    """Test 3: Create Simulation Task"""
    try:
        # Create test simulation config
        simulation_request = {
            "name": "API Deep Test Simulation",
            "description": "Automated API testing",
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
            details = f"Task ID: {task_id}, Status: {status}"
            
            # Save task_id for subsequent tests
            test_results['task_id'] = task_id
        else:
            details = f"HTTP {response.status_code}: {response.text[:200]}"
        
        log_test("Create Simulation Task API", passed, details, response)
        return passed, test_results.get('task_id')
    except Exception as e:
        log_test("Create Simulation Task API", False, f"Error: {str(e)}")
        return False, None

def test_get_simulation_status(task_id):
    """Test 4: Get Simulation Status"""
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
            details = f"Status: {status}, Progress: {progress}"
            
            if 'duration' in data and data['duration']:
                details += f", Duration: {data['duration']:.2f}s"
        else:
            details = f"HTTP {response.status_code}"
        
        log_test("Get Simulation Status API", passed, details, response)
        return passed, data.get('status') if passed else None
    except Exception as e:
        log_test("Get Simulation Status API", False, f"Error: {str(e)}")
        return False, None

def test_get_simulation_results(task_id):
    """Test 5: Get Simulation Results"""
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/simulations/{task_id}/results",
            timeout=10
        )
        
        passed = response.status_code == 200
        
        if passed:
            data = response.json()
            metrics = data.get('metrics', {})
            
            details = f"Data Points: {len(data.get('x', []))} cells, {len(data.get('time', []))} timesteps"
            details += f"\n       Mass Conservation Error: {metrics.get('mass_conservation_error', 0):.6f}%"
            details += f"\n       Max Depth: {metrics.get('max_depth', 0):.3f}m"
            details += f", Max Velocity: {metrics.get('max_velocity', 0):.3f}m/s"
            details += f"\n       Froude Number: {metrics.get('max_froude', 0):.3f}"
            details += f", Converged: {metrics.get('converged', False)}"
        else:
            details = f"HTTP {response.status_code}"
        
        log_test("Get Simulation Results API", passed, details, response)
        return passed
    except Exception as e:
        log_test("Get Simulation Results API", False, f"Error: {str(e)}")
        return False

def test_list_simulations():
    """Test 6: List Simulations"""
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
            details = f"Returned {count} simulation tasks"
        else:
            details = f"HTTP {response.status_code}"
        
        log_test("List Simulations API", passed, details, response)
        return passed
    except Exception as e:
        log_test("List Simulations API", False, f"Error: {str(e)}")
        return False

def main():
    """Main test workflow"""
    print("=" * 80)
    print("HydroClaude Web System Deep Test - Real API Testing")
    print("=" * 80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Test Server: {BASE_URL}")
    print("=" * 80)
    print()
    
    # Phase 1: Basic Service Tests
    print("[Phase 1: Basic Service Tests]")
    print("-" * 80)
    test_health_check()
    test_engine_info()
    print()
    
    # Phase 2: Simulation Task Tests
    print("[Phase 2: Simulation Task Tests]")
    print("-" * 80)
    passed, task_id = test_create_simulation()
    
    if passed and task_id:
        # Wait for simulation to complete
        print("Waiting for simulation to complete...")
        max_wait = 60  # Max 60 seconds wait
        waited = 0
        status = None
        
        while waited < max_wait:
            time.sleep(2)
            waited += 2
            passed_status, status = test_get_simulation_status(task_id)
            
            if status in ['completed', 'failed']:
                break
            
            print(f"       Waiting... ({waited}s / {max_wait}s)")
        
        if status == 'completed':
            test_get_simulation_results(task_id)
        else:
            print(f"       WARNING: Simulation not completed within {max_wait}s (Current status: {status})")
    print()
    
    # Phase 3: Query Function Tests
    print("[Phase 3: Query Function Tests]")
    print("-" * 80)
    test_list_simulations()
    print()
    
    # Generate test report
    print("=" * 80)
    print("[Test Summary]")
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
    
    print(f"Total Tests: {total_count}")
    print(f"Passed: {passed_count}")
    print(f"Failed: {total_count - passed_count}")
    print(f"Success Rate: {success_rate:.1f}%")
    print()
    
    # Save test results
    output_file = "web_test_screenshots/API_test_results.json"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(test_results, f, indent=2, ensure_ascii=False)
        print(f"Detailed results saved to: {output_file}")
    except Exception as e:
        print(f"Failed to save results: {e}")
    
    print("=" * 80)
    print("Testing Complete!")
    print("=" * 80)
    
    return success_rate >= 80

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)







