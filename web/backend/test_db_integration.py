#!/usr/bin/env python3
"""
Database Integration Test
Tests simulation API with database persistence
"""

import requests
import time
import json

API_URL = "http://localhost:8000"

def test_database_persistence():
    """Test database persistence functionality"""
    print("\n" + "="*60)
    print("Database Persistence Integration Test")
    print("="*60 + "\n")

    # Test 1: Create simulation
    print("Test 1: Create simulation...")
    request_data = {
        "name": "Database Test - Uniform Flow",
        "description": "Testing database persistence",
        "config": {
            "width": 10.0,
            "length": 1000.0,
            "n_cells": 100,
            "manning_n": 0.0,
            "slope": 0.0,
            "t_end": 5.0,
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

    response = requests.post(f"{API_URL}/api/v1/simulations", json=request_data)
    assert response.status_code == 201, f"Failed to create simulation: {response.status_code}"

    task_data = response.json()
    task_id = task_data['task_id']
    print(f"✓ Simulation created with task_id: {task_id}")

    # Test 2: Check if simulation is in database
    print("\nTest 2: Query simulation status from database...")
    time.sleep(1)

    response = requests.get(f"{API_URL}/api/v1/simulations/{task_id}/status")
    assert response.status_code == 200, "Failed to query status"

    status_data = response.json()
    print(f"✓ Status from database: {status_data['status']}")
    print(f"  Created at: {status_data['created_at']}")

    # Test 3: Wait for completion
    print("\nTest 3: Wait for simulation completion...")
    max_wait = 30
    waited = 0
    while waited < max_wait:
        response = requests.get(f"{API_URL}/api/v1/simulations/{task_id}/status")
        status_data = response.json()

        if status_data['status'] == 'completed':
            print(f"✓ Simulation completed in {status_data['duration']:.3f}s")
            break
        elif status_data['status'] == 'failed':
            print(f"✗ Simulation failed: {status_data.get('error')}")
            return False

        time.sleep(1)
        waited += 1
        print(".", end="", flush=True)

    if waited >= max_wait:
        print("\n✗ Simulation timeout")
        return False

    # Test 4: Retrieve results from database
    print("\nTest 4: Retrieve results from database...")
    response = requests.get(f"{API_URL}/api/v1/simulations/{task_id}/results")
    assert response.status_code == 200, "Failed to get results"

    result_data = response.json()
    print(f"✓ Results retrieved from database")
    print(f"  Task ID: {result_data['task_id']}")
    print(f"  Status: {result_data['status']}")
    print(f"  Time steps: {len(result_data['time'])}")
    print(f"  Spatial points: {len(result_data['x'])}")

    # Test 5: Verify metrics
    print("\nTest 5: Verify performance metrics...")
    metrics = result_data['metrics']
    print(f"  Mass conservation error: {metrics['mass_conservation_error']:.2e}")
    print(f"  Max velocity: {metrics['max_velocity']:.6f} m/s")
    print(f"  Converged: {metrics['converged']}")

    assert metrics['mass_conservation_error'] < 1e-6, "Mass conservation error too large"
    assert metrics['max_velocity'] < 0.001, "Velocity should be near zero"
    assert metrics['converged'], "Simulation should converge"
    print("✓ All metrics validated")

    # Test 6: List simulations
    print("\nTest 6: List all simulations from database...")
    response = requests.get(f"{API_URL}/api/v1/simulations")
    assert response.status_code == 200, "Failed to list simulations"

    simulations = response.json()
    print(f"✓ Found {len(simulations)} simulation(s) in database")

    # Test 7: Create another simulation
    print("\nTest 7: Create second simulation...")
    request_data['name'] = "Database Test - Simulation 2"
    response = requests.post(f"{API_URL}/api/v1/simulations", json=request_data)
    assert response.status_code == 201, "Failed to create second simulation"

    task_id_2 = response.json()['task_id']
    print(f"✓ Second simulation created: {task_id_2}")

    # Test 8: List again and verify count
    print("\nTest 8: Verify database contains both simulations...")
    time.sleep(2)  # Wait for second simulation to complete

    response = requests.get(f"{API_URL}/api/v1/simulations")
    simulations = response.json()
    assert len(simulations) >= 2, "Should have at least 2 simulations"
    print(f"✓ Database contains {len(simulations)} simulation(s)")

    # Test 9: Filter by status
    print("\nTest 9: Test status filtering...")
    response = requests.get(f"{API_URL}/api/v1/simulations?status=completed")
    completed_sims = response.json()
    print(f"✓ Found {len(completed_sims)} completed simulation(s)")

    # Test 10: Delete simulation
    print("\nTest 10: Delete first simulation from database...")
    response = requests.delete(f"{API_URL}/api/v1/simulations/{task_id}")
    assert response.status_code == 200, "Failed to delete simulation"
    print(f"✓ Simulation {task_id} deleted from database")

    # Verify deletion
    response = requests.get(f"{API_URL}/api/v1/simulations/{task_id}/status")
    assert response.status_code == 404, "Simulation should not exist"
    print("✓ Verified deletion")

    print("\n" + "="*60)
    print("✅ All database persistence tests PASSED!")
    print("="*60 + "\n")

    return True


if __name__ == "__main__":
    try:
        # Check backend is running
        response = requests.get(f"{API_URL}/health", timeout=2)
        if response.status_code != 200:
            print("❌ Backend server is not running!")
            print("Please start it with: cd web/backend && ./start_server.sh")
            exit(1)

        # Run tests
        success = test_database_persistence()
        exit(0 if success else 1)

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend server!")
        print("Please start it with: cd web/backend && ./start_server.sh")
        exit(1)
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
