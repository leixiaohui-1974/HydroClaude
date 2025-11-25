import sys
import os
import pytest
from fastapi.testclient import TestClient

# Ensure project root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(os.path.dirname(backend_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from web.backend.services.simulation_service import simulation_service
from web.backend.api_gateway.main import app

client = TestClient(app)

def test_canal_with_gate_coupling():
    """Test that a gate actually affects the water level (backwater effect)"""
    config = {
        "simulation": {
            "type": "steady",
            "time": {"end": 200.0, "dt": 0.1, "output_interval": 1.0}
        },
        "canal": {
            "width": 10.0,
            "length": 1000.0,
            "slope": 0.001,
            "manning_n": 0.015,
            "grid": {"nx": 100}
        },
        "initial_conditions": {
            "type": "uniform",
            "h_initial": 2.0,
            "Q_initial": 10.0
        },
        "boundary_conditions": {
            "upstream": {"type": "Q", "value": 10.0},
            "downstream": {"type": "h", "value": 2.0}
        },
        "structures": [{
            "type": "gate",
            "position": 500.0,
            "parameters": {
                "type": "sluice",
                "width": 10.0,
                "opening": 0.1, # Very small opening to force level rise
                "discharge_coeff": 0.6
            }
        }]
    }

    result = simulation_service.run_simulation_from_config(config)
    assert result["status"] == "completed"
    
    # Check results
    h = result["h"][-1] # Last time step
    x = result["x"]
    
    # Find index of gate
    gate_idx = int(500.0 / (1000.0 / 100))
    
    # Upstream depth should be significantly higher than downstream depth
    h_upstream = h[gate_idx - 1]
    h_downstream = h[gate_idx + 1]
    
    print(f"Gate Test - Upstream h: {h_upstream}, Downstream h: {h_downstream}")
    
    # With 0.1m opening and 10m3/s, level must rise significantly above initial 2.0m
    assert h_upstream > 2.5, f"Gate should cause level rise. Got {h_upstream}"
    assert h_upstream > h_downstream + 1.0, "Significant drop across gate expected"

def test_canal_with_pump_coupling():
    """Test that a pump runs without error and is recorded in metrics"""
    config = {
        "simulation": {
            "type": "steady",
            "time": {"end": 100.0, "dt": 0.1}
        },
        "canal": {
            "width": 10.0,
            "length": 1000.0,
            "grid": {"nx": 100}
        },
        "structures": [{
            "type": "pump",
            "position": 200.0,
            "parameters": {
                "flow_rate": 5.0,
                "head": 10.0
            }
        }]
    }
    
    result = simulation_service.run_simulation_from_config(config)
    assert result["status"] == "completed"
    assert result["metrics"]["system_type"] == "canal_with_pump"
    assert result["metrics"]["pump_flow"] == 5.0

if __name__ == "__main__":
    try:
        test_canal_with_gate_coupling()
        print("test_canal_with_gate_coupling PASSED")
        test_canal_with_pump_coupling()
        print("test_canal_with_pump_coupling PASSED")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"FAILED: {e}")
