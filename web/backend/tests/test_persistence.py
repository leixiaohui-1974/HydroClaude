import sys
import os
import json
import shutil
from fastapi.testclient import TestClient

# Ensure project root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(os.path.dirname(backend_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from web.backend.services.simulation_service import simulation_service
from web.backend.services.result_store import result_store

def test_persistence():
    """Test that simulation results are persisted to disk."""
    
    # Clean up previous results for a clean test
    if os.path.exists(result_store.storage_dir):
        shutil.rmtree(result_store.storage_dir)
    
    config = {
        "simulation": {
            "type": "steady",
            "time": {"end": 10.0, "dt": 0.1}
        },
        "canal": {
            "width": 10.0,
            "length": 100.0,
            "grid": {"nx": 20}
        }
    }

    print("Running simulation...")
    result = simulation_service.run_simulation_from_config(config)
    task_id = result["task_id"]
    print(f"Simulation completed. Task ID: {task_id}")
    
    # Verify file exists
    expected_path = os.path.join(result_store.storage_dir, f"{task_id}.json")
    assert os.path.exists(expected_path), f"Result file not found at {expected_path}"
    print(f"File found at {expected_path}")
    
    # Verify content
    with open(expected_path, 'r', encoding='utf-8') as f:
        saved_result = json.load(f)
    
    assert saved_result["task_id"] == task_id
    assert saved_result["status"] == "completed"
    print("File content verified.")
    
    # Verify retrieval via service
    retrieved_result = simulation_service.get_simulation_result(task_id)
    assert retrieved_result is not None
    assert retrieved_result["task_id"] == task_id
    print("Service retrieval verified.")

if __name__ == "__main__":
    try:
        test_persistence()
        print("test_persistence PASSED")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"FAILED: {e}")
