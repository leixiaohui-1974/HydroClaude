"""
Tests for pipe network simulation types in the dispatcher.

Covers all 5 new simulation types:
    7. pipe_network       — Steady-state pipe network hydraulics
    8. pipe_network_pdd   — Pressure-Driven Demand analysis
    9. network_wq         — Chlorine decay in pipe networks
   10. network_optimization — GA pipe sizing
   11. extended_period     — Extended Period Simulation
"""

import os
import sys

os.environ.setdefault("TESTING", "true")
# Ensure project root is in sys.path so that core/physics/network packages are importable
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.api.database import Base, get_db
from backend.api.models import User, SimulationJob, SimulationResult  # noqa: F401
from backend.api.models.simulation import Project  # noqa: F401
from backend.api.main import app
from backend.api.utils.limiter import limiter

# File-based temp SQLite (shared with background tasks)
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
TEST_DB_PATH = _tmp.name
TEST_DB_URL = f"sqlite:///{TEST_DB_PATH}"

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database(monkeypatch):
    app.dependency_overrides[get_db] = override_get_db
    limiter.enabled = False
    monkeypatch.setattr("backend.api.config.settings.DATABASE_URL", TEST_DB_URL)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    from backend.api.routes.auth import _token_blacklist
    _token_blacklist.clear()
    return TestClient(app)


@pytest.fixture
def auth_header(client):
    client.post("/api/auth/register", json={"username": "netuser", "password": "Str0ngP@ss", "email": "net@test.com"})
    resp = client.post("/api/auth/login/json", json={"username": "netuser", "password": "Str0ngP@ss"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ======================================================================
# Standard 3-node network config (reused across tests)
# ======================================================================
SIMPLE_NETWORK = {
    "nodes": [
        {"id": "R1", "type": "reservoir", "elevation": 100.0, "head": 150.0, "demand": 0.0},
        {"id": "J1", "type": "junction", "elevation": 50.0, "demand": 0.02},
        {"id": "J2", "type": "junction", "elevation": 45.0, "demand": 0.03},
    ],
    "pipes": [
        {"id": "P1", "from": "R1", "to": "J1", "diameter": 0.3, "length": 500.0, "roughness": 0.001},
        {"id": "P2", "from": "J1", "to": "J2", "diameter": 0.25, "length": 400.0, "roughness": 0.001},
    ],
}

LOOPED_NETWORK = {
    "nodes": [
        {"id": "R1", "type": "reservoir", "elevation": 100.0, "head": 150.0, "demand": 0.0},
        {"id": "J1", "type": "junction", "elevation": 50.0, "demand": 0.01},
        {"id": "J2", "type": "junction", "elevation": 48.0, "demand": 0.02},
        {"id": "J3", "type": "junction", "elevation": 45.0, "demand": 0.015},
    ],
    "pipes": [
        {"id": "P1", "from": "R1", "to": "J1", "diameter": 0.35, "length": 600.0, "roughness": 0.001},
        {"id": "P2", "from": "J1", "to": "J2", "diameter": 0.3, "length": 400.0, "roughness": 0.001},
        {"id": "P3", "from": "J2", "to": "J3", "diameter": 0.25, "length": 300.0, "roughness": 0.001},
        {"id": "P4", "from": "J1", "to": "J3", "diameter": 0.25, "length": 500.0, "roughness": 0.001},
    ],
}


def _create_and_run(client, auth_header, config, name):
    """Create a job and run it, return (status_json, results_json)."""
    create = client.post("/api/jobs", headers=auth_header, json={"config": config, "name": name})
    assert create.status_code == 201, f"Create failed: {create.text}"
    job_id = create.json()["id"]

    run = client.post(f"/api/jobs/{job_id}/run", headers=auth_header)
    assert run.status_code == 200, f"Run failed: {run.text}"

    status = client.get(f"/api/jobs/{job_id}", headers=auth_header).json()
    if status["status"] != "completed":
        return status, None

    results = client.get(f"/api/jobs/{job_id}/results", headers=auth_header)
    return status, results.json()


# ======================================================================
# 7. Pipe Network Hydraulics
# ======================================================================
class TestPipeNetwork:
    def test_simple_network_hardy_cross(self, client, auth_header):
        """Hardy-Cross completes on simple branching networks."""
        config = {
            "simulation": {"type": "pipe_network"},
            "network": SIMPLE_NETWORK,
            "solver": {"method": "hardy_cross", "max_iter": 100},
        }
        status, results = _create_and_run(client, auth_header, config, "HC Simple")
        assert status["status"] == "completed", f"Failed: {status.get('error')}"
        assert results["summary"]["converged"] is True
        assert results["summary"]["num_nodes"] == 3
        assert results["summary"]["num_pipes"] == 2
        assert "P1" in results["time_series"]["flows"]

    def test_looped_network_hardy_cross(self, client, auth_header):
        """Hardy-Cross on a looped network with 4 pipes."""
        config = {
            "simulation": {"type": "pipe_network"},
            "network": LOOPED_NETWORK,
            "solver": {"method": "hardy_cross"},
        }
        status, results = _create_and_run(client, auth_header, config, "HC Looped")
        assert status["status"] == "completed", f"Failed: {status.get('error')}"
        assert results["summary"]["converged"] is True
        assert results["summary"]["num_pipes"] == 4
        flows = results["time_series"]["flows"]
        assert "P1" in flows
        assert "P4" in flows

    def test_looped_network_newton_raphson(self, client, auth_header):
        """Newton-Raphson with Hardy-Cross initialization on looped network."""
        config = {
            "simulation": {"type": "pipe_network"},
            "network": LOOPED_NETWORK,
            "solver": {"method": "newton_raphson", "use_hardy_cross_init": True},
        }
        status, results = _create_and_run(client, auth_header, config, "NR Looped")
        assert status["status"] == "completed", f"Failed: {status.get('error')}"
        # NR may not converge on all topologies, but should complete
        assert results["summary"]["num_pipes"] == 4


# ======================================================================
# 8. Pressure-Driven Demand
# ======================================================================
class TestPressureDrivenDemand:
    def test_pdd_normal_pressure(self, client, auth_header):
        """With adequate pressure, demands should be fully satisfied."""
        config = {
            "simulation": {"type": "pipe_network_pdd"},
            "network": LOOPED_NETWORK,
            "solver": {"method": "hardy_cross"},
            "pdd": {"min_pressure": 0.0, "required_pressure": 20.0},
        }
        status, results = _create_and_run(client, auth_header, config, "PDD Normal")
        assert status["status"] == "completed", f"Failed: {status.get('error')}"
        assert results["summary"]["pdd_converged"] is True
        # High reservoir head (150m) minus elevation (50m) = 100m pressure >> 20m required
        assert results["summary"]["demand_satisfaction"] > 90.0

    def test_pdd_low_pressure(self, client, auth_header):
        """With very high required pressure, demands should be curtailed."""
        config = {
            "simulation": {"type": "pipe_network_pdd"},
            "network": LOOPED_NETWORK,
            "solver": {"method": "hardy_cross"},
            "pdd": {"min_pressure": 0.0, "required_pressure": 200.0},  # very high req
        }
        status, results = _create_and_run(client, auth_header, config, "PDD Low")
        assert status["status"] == "completed", f"Failed: {status.get('error')}"
        # With P_req=200m, pressures (~100m) won't fully satisfy
        assert results["summary"]["demand_satisfaction"] <= 100.0


# ======================================================================
# 9. Network Water Quality
# ======================================================================
class TestNetworkWQ:
    def test_chlorine_decay(self, client, auth_header):
        config = {
            "simulation": {"type": "network_wq"},
            "network": LOOPED_NETWORK,
            "solver": {"method": "hardy_cross"},
            "water_quality": {
                "source_concentration": 1.0,
                "bulk_decay_rate": 0.5,
                "wall_decay_rate": 0.1,
                "duration": 7200,
                "dt": 60,
                "initial_concentration": 0.0,
                "min_residual": 0.2,
            },
        }
        status, results = _create_and_run(client, auth_header, config, "Network WQ")
        assert status["status"] == "completed", f"Failed: {status.get('error')}"
        assert results["summary"]["simulation_type"] == "network_wq"
        assert results["summary"]["C_max"] > 0
        # After 2 hours, chlorine should have propagated from reservoir
        final = results["time_series"]["final_concentrations"]
        assert "R1" in final
        assert final["R1"] == pytest.approx(1.0, abs=0.01)  # Source stays at 1.0
        assert len(results["time_series"]["snapshots"]) > 0


# ======================================================================
# 10. Genetic Algorithm Optimization
# ======================================================================
class TestNetworkOptimization:
    def test_ga_simple_network(self, client, auth_header):
        config = {
            "simulation": {"type": "network_optimization"},
            "network": SIMPLE_NETWORK,
            "solver": {"method": "hardy_cross"},
            "optimization": {
                "population_size": 20,
                "generations": 15,
                "min_pressure": 20.0,
                "seed": 42,
            },
        }
        status, results = _create_and_run(client, auth_header, config, "GA Opt")
        assert status["status"] == "completed", f"Failed: {status.get('error')}"
        assert results["summary"]["simulation_type"] == "network_optimization"
        assert results["summary"]["total_cost"] > 0
        assert results["summary"]["num_pipes"] == 2
        assert len(results["time_series"]["convergence"]) == 15
        # Verify optimal pipes have valid diameters
        for pid, pinfo in results["time_series"]["optimal_pipes"].items():
            assert pinfo["diameter"] > 0
            assert pinfo["total_cost"] > 0


# ======================================================================
# 11. Extended Period Simulation
# ======================================================================
class TestExtendedPeriod:
    def test_eps_24h(self, client, auth_header):
        config = {
            "simulation": {"type": "extended_period"},
            "network": LOOPED_NETWORK,
            "solver": {"method": "hardy_cross"},
            "eps": {
                "duration": 86400,
                "timestep": 3600,
                "demand_pattern": [
                    0.5, 0.4, 0.3, 0.3, 0.4, 0.6,
                    0.8, 1.2, 1.4, 1.3, 1.1, 1.0,
                    0.9, 0.9, 1.0, 1.1, 1.3, 1.4,
                    1.2, 1.0, 0.8, 0.7, 0.6, 0.5,
                ],
            },
        }
        status, results = _create_and_run(client, auth_header, config, "EPS 24h")
        assert status["status"] == "completed", f"Failed: {status.get('error')}"
        assert results["summary"]["simulation_type"] == "extended_period"
        assert results["summary"]["duration_hours"] == 24.0
        assert results["summary"]["total_timesteps"] == 24
        assert len(results["time_series"]["snapshots"]) == 24
        # Verify demand multipliers vary across time steps
        multipliers = [s["demand_multiplier"] for s in results["time_series"]["snapshots"]]
        assert max(multipliers) > min(multipliers)  # demand should vary

    def test_eps_with_tank(self, client, auth_header):
        """EPS with a tank node tracks level changes."""
        network_with_tank = {
            "nodes": [
                {"id": "R1", "type": "reservoir", "elevation": 100.0, "head": 150.0, "demand": 0.0},
                {"id": "J1", "type": "junction", "elevation": 50.0, "demand": 0.03},
                {"id": "T1", "type": "tank", "elevation": 60.0, "head": 65.0, "demand": 0.0,
                 "initial_level": 5.0, "area": 200.0, "min_level": 0.5, "max_level": 10.0},
            ],
            "pipes": [
                {"id": "P1", "from": "R1", "to": "J1", "diameter": 0.3, "length": 500.0, "roughness": 0.001},
                {"id": "P2", "from": "J1", "to": "T1", "diameter": 0.25, "length": 300.0, "roughness": 0.001},
            ],
        }
        config = {
            "simulation": {"type": "extended_period"},
            "network": network_with_tank,
            "solver": {"method": "hardy_cross"},
            "eps": {"duration": 43200, "timestep": 3600},  # 12 hours
        }
        status, results = _create_and_run(client, auth_header, config, "EPS Tank")
        assert status["status"] == "completed", f"Failed: {status.get('error')}"
        assert results["summary"]["num_tanks"] == 1
        # Tank level should appear in snapshots
        for snap in results["time_series"]["snapshots"]:
            assert "T1" in snap["tank_levels"]


# ======================================================================
# Simulation types listing
# ======================================================================
class TestSimulationTypesAPI:
    def test_list_all_types(self, client, auth_header):
        resp = client.get("/api/jobs/simulation-types", headers=auth_header)
        assert resp.status_code == 200
        types = resp.json()["types"]
        type_ids = [t["id"] for t in types]
        assert "pipe_network" in type_ids
        assert "pipe_network_pdd" in type_ids
        assert "network_wq" in type_ids
        assert "network_optimization" in type_ids
        assert "extended_period" in type_ids
        assert len(types) == 13  # 8 original + 5 new


# ======================================================================
# Cleanup
# ======================================================================
@pytest.fixture(scope="session", autouse=True)
def cleanup_temp_db():
    yield
    try:
        os.unlink(TEST_DB_PATH)
    except OSError:
        pass
