import sys
import os
import pytest

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from web.backend.services.simulation_service import simulation_service

def test_simulation_service_basic():
    """Test basic canal simulation via service"""
    config = {
        "simulation": {
            "type": "steady",
            "time": {"end": 100, "dt": 1.0}
        },
        "canal": {
            "length": 1000.0,
            "width": 10.0,
            "slope": 0.001,
            "manning_n": 0.015,
            "grid": {"nx": 50}
        },
        "structures": [],
        "initial_conditions": {
            "depth": "uniform_flow",
            "h_initial": 5.0
        },
        "boundary_conditions": {
            "upstream": {"type": "h", "value": 5.0},
            "downstream": {"type": "h", "value": 5.0}
        }
    }
    
    result = simulation_service.run_simulation_from_config(config)
    
    if result["status"] != "completed":
        with open("test_failure_result.txt", "w") as f:
            f.write(str(result))
    assert result["status"] == "completed"
    assert "task_id" in result
    assert "h" in result
    assert len(result["h"]) > 0
    
    # Verify result storage
    task_id = result["task_id"]
    stored_result = simulation_service.get_simulation_result(task_id)
    assert stored_result == result

def test_simulation_service_with_gate():
    """Test canal with gate simulation via service"""
    config = {
        "simulation": {
            "type": "steady"
        },
        "canal": {
            "length": 1000.0,
            "width": 10.0,
            "slope": 0.001,
            "manning_n": 0.015,
            "grid": {"nx": 50}
        },
        "structures": [
            {
                "type": "gate",
                "position": 500.0,
                "parameters": {
                    "width": 5.0,
                    "opening": 1.0,
                    "discharge_coeff": 0.6
                }
            }
        ],
        "boundary_conditions": {
            "upstream": {"type": "h", "value": 5.0},
            "downstream": {"type": "h", "value": 2.0}
        }
    }
    
    result = simulation_service.run_simulation_from_config(config)
    
    assert result["status"] == "completed"
    assert "metrics" in result
    # Check if gate specific metrics are present (depends on engine implementation)
    # For now just check success
    
if __name__ == "__main__":
    test_simulation_service_basic()
    test_simulation_service_with_gate()
    print("All service tests passed!")
