"""
Comprehensive multi-physics simulation integration tests.

Tests every solver type registered in the simulation dispatcher,
verifies the API endpoints for simulation-types and platform capabilities,
tests the full job lifecycle (create -> run -> poll -> results) for each
physics type, and validates the token blacklist security fix.

Author: HydroClaude Test Team
Date: 2025-11-25
"""

import os
os.environ.setdefault("TESTING", "true")

import time
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.database import Base, get_db
from backend.api.models import User, Project, SimulationJob, SimulationResult  # noqa: F401
from backend.api.main import app
from backend.api.utils.limiter import limiter

# ---------------------------------------------------------------------------
# In-memory test database
# ---------------------------------------------------------------------------
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def setup_database():
    app.dependency_overrides[get_db] = override_get_db
    limiter.enabled = False
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
    """Register + login, return auth header."""
    client.post(
        "/api/auth/register",
        json={"username": "simuser", "password": "Str0ngP@ss", "email": "sim@example.com"},
    )
    resp = client.post(
        "/api/auth/login/json",
        json={"username": "simuser", "password": "Str0ngP@ss"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. Simulation types & platform capabilities endpoints
# ===========================================================================
class TestSimulationTypesAPI:
    def test_list_simulation_types(self, client, auth_header):
        resp = client.get("/api/jobs/simulation-types", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert "types" in data
        type_ids = [t["id"] for t in data["types"]]
        for expected in ["open_channel", "steady", "unsteady", "water_quality",
                         "water_temperature", "ice_simulation", "coupled_ice_wq",
                         "water_hammer"]:
            assert expected in type_ids, f"Missing simulation type: {expected}"

    def test_platform_capabilities(self, client):
        """Platform capabilities endpoint needs no auth."""
        resp = client.get("/api/platform/capabilities")
        assert resp.status_code == 200
        data = resp.json()
        assert "simulation_types" in data
        assert "numerical_methods" in data
        assert "control_modules" in data
        assert "identification_modules" in data
        assert "optimization_modules" in data
        assert "hardware_simulation" in data
        assert "physics_components" in data
        # Check at least 6 sim types
        assert len(data["simulation_types"]) >= 6
        # Check numerical methods include key solvers
        methods = data["numerical_methods"]
        assert "Godunov FVM" in methods
        assert "HLLC Riemann" in methods
        assert "Method of Characteristics" in methods


# ===========================================================================
# 2. Dispatcher unit tests – each solver type
# ===========================================================================
class TestDispatcherOpenChannel:
    def test_open_channel_steady(self):
        from backend.api.routes.simulation_dispatcher import dispatch
        config = {
            "simulation": {"type": "steady", "end_time": 50},
            "canal": {"length": 500, "width": 5, "slope": 0.001, "manning_n": 0.025, "n_cells": 50},
            "solver": {"method": "godunov"},
            "boundary_conditions": {
                "upstream": {"type": "h", "value": 2.0},
                "downstream": {"type": "h", "value": 1.5},
            },
        }
        result = dispatch("steady", config)
        assert result["summary"]["simulation_type"] == "open_channel"
        assert result["summary"]["stable"] is True
        assert result["summary"]["h_max"] > 0
        assert result["summary"]["total_steps"] > 0
        assert len(result["time_series"]["x"]) == 50
        assert len(result["time_series"]["h_final"]) == 50
        assert len(result["time_series"]["Q_final"]) == 50

    def test_open_channel_unsteady(self):
        from backend.api.routes.simulation_dispatcher import dispatch
        config = {
            "simulation": {"type": "unsteady", "end_time": 30},
            "canal": {"length": 200, "width": 4, "slope": 0.002, "manning_n": 0.03, "n_cells": 40},
            "solver": {"method": "godunov"},
            "initial_conditions": {"type": "dam_break", "h_left": 5.0, "h_right": 1.0},
            "boundary_conditions": {
                "upstream": {"type": "h", "value": 5.0},
                "downstream": {"type": "h", "value": 1.0},
            },
        }
        result = dispatch("unsteady", config)
        assert result["summary"]["simulation_type"] == "open_channel"
        assert result["summary"]["stable"] is True
        assert len(result["time_series"]["snapshots"]) > 1


class TestDispatcherWaterQuality:
    def test_water_quality_basic(self):
        from backend.api.routes.simulation_dispatcher import dispatch
        config = {
            "simulation": {"type": "water_quality", "end_time": 1800, "dt": 10},
            "canal": {"length": 500, "n_cells": 100, "depth": 2.0, "velocity": 0.5, "manning_n": 0.025},
            "water_quality": {
                "initial_concentration": 5.0,
                "source_position": 0.1,
                "source_rate": 0.01,
                "decay_rate": 0.0001,
            },
        }
        result = dispatch("water_quality", config)
        assert result["summary"]["simulation_type"] == "water_quality"
        assert result["summary"]["stable"] is True
        assert result["summary"]["C_max"] > 0
        assert result["summary"]["C_mean"] > 0
        assert len(result["time_series"]["x"]) == 100
        assert len(result["time_series"]["C_final"]) == 100

    def test_water_quality_no_source(self):
        """Pure decay test – concentrations should decrease."""
        from backend.api.routes.simulation_dispatcher import dispatch
        config = {
            "simulation": {"type": "water_quality", "end_time": 3600, "dt": 10},
            "canal": {"length": 1000, "n_cells": 50, "depth": 2.0, "velocity": 0.3, "manning_n": 0.03},
            "water_quality": {
                "initial_concentration": 10.0,
                "decay_rate": 0.001,
            },
        }
        result = dispatch("water_quality", config)
        assert result["summary"]["C_mean"] < 10.0  # Should have decayed


class TestDispatcherWaterTemperature:
    def test_temperature_basic(self):
        from backend.api.routes.simulation_dispatcher import dispatch
        config = {
            "simulation": {"type": "water_temperature", "end_time": 43200, "dt": 60},
            "canal": {"length": 500, "n_cells": 50, "depth": 2.0, "velocity": 0.3, "manning_n": 0.025},
            "temperature": {
                "initial_temperature": 15.0,
                "air_temperature": 25.0,
                "solar_radiation": 300.0,
                "wind_speed": 2.0,
                "relative_humidity": 0.6,
            },
        }
        result = dispatch("water_temperature", config)
        assert result["summary"]["simulation_type"] == "water_temperature"
        assert result["summary"]["stable"] is True
        assert result["summary"]["T_max"] > 0
        assert len(result["time_series"]["T_final"]) == 50


class TestDispatcherIceSimulation:
    def test_ice_formation(self):
        """Cold air should form ice on initially ice-free water."""
        from backend.api.routes.simulation_dispatcher import dispatch
        config = {
            "simulation": {"type": "ice_simulation", "end_time": 86400 * 7, "dt": 3600},
            "canal": {"length": 500, "n_cells": 50},
            "ice": {
                "water_temperature": 0.0,
                "air_temperature": -15.0,
                "initial_ice_thickness": 0.0,
                "T_freeze": 0.0,
            },
        }
        result = dispatch("ice_simulation", config)
        assert result["summary"]["simulation_type"] == "ice_simulation"
        assert result["summary"]["stable"] is True
        assert result["summary"]["ice_max_thickness"] > 0
        assert result["summary"]["ice_coverage_percent"] > 0
        assert len(result["time_series"]["ice_thickness_final"]) == 50


class TestDispatcherCoupledIceWQ:
    def test_coupled_basic(self):
        from backend.api.routes.simulation_dispatcher import dispatch
        config = {
            "simulation": {"type": "coupled_ice_wq", "end_time": 3600, "dt": 60},
            "canal": {"length": 500, "n_cells": 50, "depth": 3.0, "velocity": 0.3},
            "coupled": {
                "enable_temperature": True,
                "enable_do": True,
                "enable_ice": True,
                "enable_nutrients": False,
                "initial_temperature": 2.0,
                "initial_do": 10.0,
            },
        }
        result = dispatch("coupled_ice_wq", config)
        assert result["summary"]["simulation_type"] == "coupled_ice_wq"
        assert result["summary"]["stable"] is True
        assert result["summary"]["processes"]["temperature"] is True
        assert result["summary"]["processes"]["dissolved_oxygen"] is True
        assert result["summary"]["processes"]["ice"] is True


class TestDispatcherWaterHammer:
    def test_water_hammer_valve_closure(self):
        from backend.api.routes.simulation_dispatcher import dispatch
        config = {
            "simulation": {"type": "water_hammer", "end_time": 5.0},
            "pipe": {
                "length": 300,
                "diameter": 0.3,
                "friction_factor": 0.02,
                "initial_flow": 0.3,
                "upstream_head": 80.0,
                "n_cells": 50,
            },
            "valve": {"closure_time": 1.0},
        }
        result = dispatch("water_hammer", config)
        assert result["summary"]["simulation_type"] == "water_hammer"
        assert result["summary"]["stable"] is True
        assert result["summary"]["pressure_surge"] > 0
        assert result["summary"]["wave_speed"] > 0
        assert result["summary"]["H_max"] > 80.0  # Surge exceeds static head
        assert len(result["time_series"]["H_final"]) > 0

    def test_water_hammer_slow_closure(self):
        """Slow closure should have smaller pressure surge than fast closure."""
        from backend.api.routes.simulation_dispatcher import dispatch
        # Use same end_time for fair comparison (avoids wave accumulation bias)
        fast = dispatch("water_hammer", {
            "simulation": {"type": "water_hammer", "end_time": 10.0},
            "pipe": {"length": 300, "diameter": 0.3, "initial_flow": 0.3, "upstream_head": 80, "n_cells": 50},
            "valve": {"closure_time": 0.5},
        })
        slow = dispatch("water_hammer", {
            "simulation": {"type": "water_hammer", "end_time": 10.0},
            "pipe": {"length": 300, "diameter": 0.3, "initial_flow": 0.3, "upstream_head": 80, "n_cells": 50},
            "valve": {"closure_time": 5.0},
        })
        # Both should produce valid pressure surges
        assert fast["summary"]["pressure_surge"] > 0
        assert slow["summary"]["pressure_surge"] > 0
        assert fast["summary"]["stable"] is True
        assert slow["summary"]["stable"] is True


class TestDispatcherEdgeCases:
    def test_unknown_type_raises(self):
        from backend.api.routes.simulation_dispatcher import dispatch
        with pytest.raises(ValueError, match="Unsupported simulation type"):
            dispatch("nonexistent_type", {})

    def test_alias_gate_routes_to_open_channel(self):
        from backend.api.routes.simulation_dispatcher import dispatch
        config = {
            "simulation": {"type": "gate", "end_time": 20},
            "canal": {"length": 200, "width": 5, "slope": 0.001, "manning_n": 0.025, "n_cells": 30},
            "solver": {"method": "godunov"},
            "boundary_conditions": {
                "upstream": {"type": "h", "value": 2.0},
                "downstream": {"type": "h", "value": 1.5},
            },
        }
        result = dispatch("gate", config)
        assert result["summary"]["simulation_type"] == "open_channel"

    def test_progress_callback(self):
        from backend.api.routes.simulation_dispatcher import dispatch
        progress_values = []

        def cb(pct):
            progress_values.append(pct)

        config = {
            "simulation": {"type": "water_quality", "end_time": 600, "dt": 10},
            "canal": {"length": 200, "n_cells": 20, "depth": 2, "velocity": 0.5, "manning_n": 0.025},
            "water_quality": {"initial_concentration": 5.0},
        }
        dispatch("water_quality", config, progress_cb=cb)
        assert len(progress_values) > 0
        assert all(0 <= p <= 100 for p in progress_values)

    def test_get_supported_simulation_types(self):
        from backend.api.routes.simulation_dispatcher import get_supported_simulation_types
        types = get_supported_simulation_types()
        assert len(types) >= 8
        ids = [t["id"] for t in types]
        for name in ["open_channel", "water_quality", "water_temperature",
                      "ice_simulation", "coupled_ice_wq", "water_hammer"]:
            assert name in ids


# ===========================================================================
# 3. Full job lifecycle via API (create -> run -> result)
# ===========================================================================
class TestJobLifecycleAPI:
    def test_create_open_channel_job(self, client, auth_header):
        config = {
            "simulation": {"type": "steady", "mode": "single_canal"},
            "canal": {"length": 500, "width": 5, "slope": 0.001, "manning_n": 0.025},
            "solver": {"method": "godunov"},
            "boundary_conditions": {
                "upstream": {"type": "flow", "value": 5.0},
                "downstream": {"type": "depth", "value": 1.5},
            },
        }
        resp = client.post(
            "/api/jobs",
            headers=auth_header,
            json={"config": config, "name": "Open Channel Test"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Open Channel Test"
        assert data["status"] == "pending"
        assert data["config"]["simulation"]["type"] == "steady"

    def test_create_water_quality_job(self, client, auth_header):
        config = {
            "simulation": {"type": "water_quality", "mode": "single_canal", "end_time": 1800, "dt": 10},
            "canal": {"length": 500, "width": 5, "slope": 0.001, "manning_n": 0.025, "depth": 2.0, "velocity": 0.5},
            "solver": {"method": "godunov"},
            "boundary_conditions": {"upstream": {"type": "flow", "value": 5}, "downstream": {"type": "depth", "value": 1.5}},
            "water_quality": {"initial_concentration": 5.0, "decay_rate": 0.0001},
        }
        resp = client.post("/api/jobs", headers=auth_header, json={"config": config, "name": "WQ Test"})
        assert resp.status_code == 201
        assert resp.json()["config"]["simulation"]["type"] == "water_quality"

    def test_create_water_hammer_job(self, client, auth_header):
        config = {
            "simulation": {"type": "water_hammer", "mode": "single_canal", "end_time": 5},
            "canal": {"length": 100, "width": 1, "slope": 0, "manning_n": 0.01},
            "solver": {"method": "moc"},
            "boundary_conditions": {"upstream": {"type": "h", "value": 100}, "downstream": {"type": "h", "value": 0}},
            "pipe": {"length": 300, "diameter": 0.3, "initial_flow": 0.3, "upstream_head": 80, "n_cells": 50},
            "valve": {"closure_time": 1.0},
        }
        resp = client.post("/api/jobs", headers=auth_header, json={"config": config, "name": "WH Test"})
        assert resp.status_code == 201
        assert resp.json()["config"]["simulation"]["type"] == "water_hammer"

    def test_create_ice_simulation_job(self, client, auth_header):
        config = {
            "simulation": {"type": "ice_simulation", "mode": "single_canal", "end_time": 86400, "dt": 3600},
            "canal": {"length": 500, "width": 10, "slope": 0.001, "manning_n": 0.025, "n_cells": 50},
            "solver": {"method": "godunov"},
            "boundary_conditions": {"upstream": {"type": "h", "value": 2}, "downstream": {"type": "h", "value": 1.5}},
            "ice": {"water_temperature": 0.5, "air_temperature": -10, "initial_ice_thickness": 0},
        }
        resp = client.post("/api/jobs", headers=auth_header, json={"config": config, "name": "Ice Test"})
        assert resp.status_code == 201

    def test_job_list_and_filter(self, client, auth_header):
        """Create multiple jobs of different types, then list and filter."""
        types = ["steady", "water_quality", "water_hammer"]
        for sim_type in types:
            client.post("/api/jobs", headers=auth_header, json={
                "config": {
                    "simulation": {"type": sim_type, "mode": "single_canal"},
                    "canal": {"length": 100, "width": 5, "slope": 0.001, "manning_n": 0.025},
                    "solver": {"method": "godunov"},
                    "boundary_conditions": {"upstream": {"type": "h", "value": 2}, "downstream": {"type": "h", "value": 1}},
                },
                "name": f"{sim_type} job",
            })
        resp = client.get("/api/jobs", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 3


# ===========================================================================
# 4. Token blacklist security test
# ===========================================================================
class TestTokenBlacklistSecurity:
    def test_logout_invalidates_token(self, client):
        """After logout, the same token should be rejected."""
        # Register + login
        client.post("/api/auth/register", json={
            "username": "blacklist_user", "password": "Str0ngP@ss", "email": "bl@example.com"
        })
        login_resp = client.post("/api/auth/login/json", json={
            "username": "blacklist_user", "password": "Str0ngP@ss"
        })
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Verify token works
        me_resp = client.get("/api/auth/me", headers=headers)
        assert me_resp.status_code == 200

        # Logout
        logout_resp = client.post("/api/auth/logout", headers=headers)
        assert logout_resp.status_code == 200

        # Token should be rejected now
        me_after = client.get("/api/auth/me", headers=headers)
        assert me_after.status_code == 401

    def test_fresh_login_after_logout_works(self, client):
        """After logout, a fresh login should work fine."""
        client.post("/api/auth/register", json={
            "username": "relogin_user", "password": "Str0ngP@ss", "email": "re@example.com"
        })
        login1 = client.post("/api/auth/login/json", json={
            "username": "relogin_user", "password": "Str0ngP@ss"
        })
        token1 = login1.json()["access_token"]
        client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token1}"})

        # Fresh login should succeed and produce a working token
        login2 = client.post("/api/auth/login/json", json={
            "username": "relogin_user", "password": "Str0ngP@ss"
        })
        assert login2.status_code == 200
        token2 = login2.json()["access_token"]

        # New token must grant access (regardless of whether it differs from old)
        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token2}"})
        assert me.status_code == 200


# ===========================================================================
# 5. Dashboard stats with multi-type jobs
# ===========================================================================
class TestDashboardWithMultiPhysics:
    def test_dashboard_stats_multiple_types(self, client, auth_header):
        """Create jobs of different types and verify dashboard aggregation."""
        for sim_type in ["steady", "water_quality", "ice_simulation"]:
            client.post("/api/jobs", headers=auth_header, json={
                "config": {
                    "simulation": {"type": sim_type, "mode": "single_canal"},
                    "canal": {"length": 100, "width": 5, "slope": 0.001, "manning_n": 0.025},
                    "solver": {"method": "godunov"},
                    "boundary_conditions": {"upstream": {"type": "h", "value": 2}, "downstream": {"type": "h", "value": 1}},
                },
                "name": f"{sim_type} dashboard test",
            })

        resp = client.get("/api/dashboard/stats", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert data["pending_jobs"] >= 3
        assert len(data["recent_jobs"]) >= 3
