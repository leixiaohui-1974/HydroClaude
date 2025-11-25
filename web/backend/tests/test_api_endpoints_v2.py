import sys
import os
from fastapi.testclient import TestClient

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from web.backend.api_gateway.main import app

client = TestClient(app)

def test_simulate_endpoint():
    """Test the simulation endpoint"""
    payload = {
        "simulation_type": "steady",
        "canal": {
            "length": 1000.0,
            "width": 10.0,
            "slope": 0.001,
            "manning_n": 0.015,
            "grid_nx": 50
        },
        "structure_type": "none",
        "structure": {
            "position": 0,
            "parameters": {}
        },
        "boundaries": {
            "upstream": {"type": "h", "value": 5.0},
            "downstream": {"type": "h", "value": 5.0}
        },
        "metadata": {"title": "Test Simulation"}
    }
    
    response = client.post("/api/structures/simulate-canal-with-structure", json=payload)
    if response.status_code != 200:
        with open("last_api_error.txt", "w", encoding="utf-8") as f:
            f.write(f"API Error: {response.status_code} - {response.text}")
        print(f"API Error: {response.status_code} - See last_api_error.txt")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "task_id" in data
    
    # Test result retrieval
    task_id = data["task_id"]
    response_result = client.get(f"/api/structures/simulation-results/{task_id}")
    if response_result.status_code != 200:
        with open("last_get_error.txt", "w", encoding="utf-8") as f:
            f.write(f"GET Error: {response_result.status_code} - {response_result.text}")
        print(f"GET Error: {response_result.status_code} - See last_get_error.txt")
    assert response_result.status_code == 200
    result_data = response_result.json()
    assert result_data["task_id"] == task_id
    assert result_data["status"] == "completed"

if __name__ == "__main__":
    test_simulate_endpoint()
    print("All API endpoint tests passed!")
