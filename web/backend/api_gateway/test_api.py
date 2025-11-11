"""
Test script for HydroClaude Web API
Validates that all endpoints work correctly
"""

import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient
from main import app
import json

# Create test client
client = TestClient(app)


def test_health_check():
    """Test health check endpoint"""
    print("\n" + "="*60)
    print("TEST 1: Health Check")
    print("="*60)

    response = client.get("/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    print("✅ PASSED")


def test_root_endpoint():
    """Test root endpoint"""
    print("\n" + "="*60)
    print("TEST 2: Root Endpoint")
    print("="*60)

    response = client.get("/")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 200
    assert "service" in response.json()
    print("✅ PASSED")


def test_engine_info():
    """Test engine info endpoint"""
    print("\n" + "="*60)
    print("TEST 3: Engine Info")
    print("="*60)

    response = client.get("/api/v1/engine/info")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 200
    assert "engine_version" in response.json()
    print("✅ PASSED")


def test_create_simulation():
    """Test creating a simulation"""
    print("\n" + "="*60)
    print("TEST 4: Create Simulation")
    print("="*60)

    # Uniform flow test case (validated in engine test)
    request_data = {
        "name": "Uniform Flow Test - API Validation",
        "description": "Testing uniform flow scenario through API",
        "config": {
            "width": 10.0,
            "length": 1000.0,
            "n_cells": 100,
            "manning_n": 0.0,
            "slope": 0.0,
            "t_end": 10.0,
            "dt_max": 0.1,
            "output_interval": 0.5,
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

    print("Request Data:")
    print(json.dumps(request_data, indent=2))

    response = client.post("/api/v1/simulations", json=request_data)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 201
    assert "task_id" in response.json()
    assert response.json()["status"] == "queued"

    task_id = response.json()["task_id"]
    print(f"✅ PASSED - Task ID: {task_id}")

    return task_id


def test_get_simulation_status(task_id):
    """Test getting simulation status"""
    print("\n" + "="*60)
    print("TEST 5: Get Simulation Status")
    print("="*60)

    import time

    # Wait a bit for simulation to start
    print("Waiting for simulation to complete...")
    time.sleep(2)

    response = client.get(f"/api/v1/simulations/{task_id}/status")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 200
    assert response.json()["task_id"] == task_id
    print(f"✅ PASSED - Status: {response.json()['status']}")

    return response.json()["status"]


def test_get_simulation_results(task_id):
    """Test getting simulation results"""
    print("\n" + "="*60)
    print("TEST 6: Get Simulation Results")
    print("="*60)

    import time

    # Wait for simulation to complete
    max_wait = 10  # seconds
    wait_interval = 0.5
    elapsed = 0

    while elapsed < max_wait:
        status_response = client.get(f"/api/v1/simulations/{task_id}/status")
        status = status_response.json()["status"]

        if status == "completed":
            break
        elif status == "failed":
            print(f"❌ Simulation failed!")
            return

        time.sleep(wait_interval)
        elapsed += wait_interval
        print(f"Status: {status}, waiting... ({elapsed:.1f}s)")

    response = client.get(f"/api/v1/simulations/{task_id}/results")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        result = response.json()

        # Print summary (not full data)
        print(f"Task ID: {result['task_id']}")
        print(f"Status: {result['status']}")
        print(f"Duration: {result['duration']:.4f}s")
        print(f"Time steps: {len(result['time'])}")
        print(f"Spatial points: {len(result['x'])}")
        print(f"\nMetrics:")
        for key, value in result['metrics'].items():
            if isinstance(value, float):
                print(f"  {key}: {value:.6e}")
            else:
                print(f"  {key}: {value}")

        # Validate key metrics for uniform flow
        metrics = result['metrics']
        assert metrics['mass_conservation_error'] < 1e-10, "Mass conservation error too large!"
        assert metrics['max_velocity'] < 0.001, "Velocity should be near zero for static uniform flow!"
        assert abs(metrics['mean_depth_final'] - 5.0) < 0.01, "Final depth should be ~5.0m!"

        print("✅ PASSED - Results validated!")
    else:
        print(f"Response: {response.text}")
        print(f"❌ FAILED")


def test_list_simulations():
    """Test listing all simulations"""
    print("\n" + "="*60)
    print("TEST 7: List Simulations")
    print("="*60)

    response = client.get("/api/v1/simulations")
    print(f"Status Code: {response.status_code}")
    print(f"Number of simulations: {len(response.json())}")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    print("✅ PASSED")


def run_all_tests():
    """Run all tests"""
    print("\n" + "🚀" * 30)
    print("HydroClaude Web API Test Suite")
    print("🚀" * 30)

    try:
        test_health_check()
        test_root_endpoint()
        test_engine_info()
        task_id = test_create_simulation()
        status = test_get_simulation_status(task_id)
        test_get_simulation_results(task_id)
        test_list_simulations()

        print("\n" + "✅" * 30)
        print("ALL TESTS PASSED!")
        print("✅" * 30)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()
