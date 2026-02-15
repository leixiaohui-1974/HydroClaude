"""
End-to-end simulation pipeline tests.

Tests the COMPLETE workflow: create user → create job → run simulation →
verify results stored → retrieve results via API.

Uses a file-based temporary SQLite so that _run_simulation's independent
DB engine connects to the same database as the test client.

Author: HydroClaude Test Team
"""

import os
import tempfile

os.environ.setdefault("TESTING", "true")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.api.database import Base, get_db
from backend.api.models import User, Project, SimulationJob, SimulationResult  # noqa: F401
from backend.api.main import app
from backend.api.utils.limiter import limiter


# ---------------------------------------------------------------------------
# File-based temp SQLite (shared between test + _run_simulation)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def setup_database(monkeypatch):
    """Create tables, patch DATABASE_URL so background worker uses same DB."""
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
    """Register + login, return auth header."""
    client.post(
        "/api/auth/register",
        json={"username": "e2euser", "password": "Str0ngP@ss", "email": "e2e@example.com"},
    )
    resp = client.post(
        "/api/auth/login/json",
        json={"username": "e2euser", "password": "Str0ngP@ss"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. Full pipeline: create → run → completed → results
# ===========================================================================
class TestFullPipeline:
    def test_open_channel_e2e(self, client, auth_header):
        """Create an open-channel job, run it, verify completion and results."""
        # 1. Create job
        config = {
            "simulation": {"type": "steady", "end_time": 30, "mode": "single_canal"},
            "canal": {"length": 200, "width": 5, "slope": 0.001, "manning_n": 0.025, "n_cells": 30},
            "solver": {"method": "godunov"},
            "boundary_conditions": {
                "upstream": {"type": "h", "value": 2.0},
                "downstream": {"type": "h", "value": 1.5},
            },
        }
        create_resp = client.post(
            "/api/jobs", headers=auth_header,
            json={"config": config, "name": "E2E Open Channel"},
        )
        assert create_resp.status_code == 201
        job_id = create_resp.json()["id"]
        assert create_resp.json()["status"] == "pending"

        # 2. Run the job (TestClient executes BackgroundTasks synchronously)
        run_resp = client.post(f"/api/jobs/{job_id}/run", headers=auth_header)
        assert run_resp.status_code == 200

        # 3. Check status is completed
        status_resp = client.get(f"/api/jobs/{job_id}", headers=auth_header)
        assert status_resp.status_code == 200
        job_data = status_resp.json()
        assert job_data["status"] == "completed", f"Job failed: {job_data.get('error')}"
        assert job_data["progress"] == 100.0

        # 4. Retrieve results
        results_resp = client.get(f"/api/jobs/{job_id}/results", headers=auth_header)
        assert results_resp.status_code == 200
        results = results_resp.json()

        # 5. Verify result structure
        assert "summary" in results
        assert "time_series" in results
        assert "solver_metadata" in results
        assert results["summary"]["simulation_type"] == "open_channel"
        assert results["summary"]["stable"] is True
        assert results["summary"]["h_max"] > 0
        assert len(results["time_series"]["x"]) == 30
        assert len(results["time_series"]["h_final"]) == 30
        assert len(results["time_series"]["Q_final"]) == 30

    def test_water_quality_e2e(self, client, auth_header):
        """Full pipeline for water quality simulation."""
        config = {
            "simulation": {"type": "water_quality", "end_time": 600, "dt": 10, "mode": "single_canal"},
            "canal": {"length": 200, "n_cells": 20, "depth": 2, "velocity": 0.5, "manning_n": 0.025},
            "solver": {"method": "adr"},
            "boundary_conditions": {"upstream": {"type": "h", "value": 2}, "downstream": {"type": "h", "value": 1}},
            "water_quality": {"initial_concentration": 5.0, "decay_rate": 0.0001},
        }
        create_resp = client.post(
            "/api/jobs", headers=auth_header,
            json={"config": config, "name": "E2E Water Quality"},
        )
        job_id = create_resp.json()["id"]

        run_resp = client.post(f"/api/jobs/{job_id}/run", headers=auth_header)
        assert run_resp.status_code == 200

        status_resp = client.get(f"/api/jobs/{job_id}", headers=auth_header)
        job_data = status_resp.json()
        assert job_data["status"] == "completed", f"Job failed: {job_data.get('error')}"

        results_resp = client.get(f"/api/jobs/{job_id}/results", headers=auth_header)
        assert results_resp.status_code == 200
        results = results_resp.json()
        assert results["summary"]["simulation_type"] == "water_quality"
        assert results["summary"]["stable"] is True
        assert len(results["time_series"]["C_final"]) == 20

    def test_water_hammer_e2e(self, client, auth_header):
        """Full pipeline for water hammer simulation."""
        config = {
            "simulation": {"type": "water_hammer", "end_time": 5.0, "mode": "single_canal"},
            "canal": {"length": 100, "width": 1, "slope": 0, "manning_n": 0.01},
            "solver": {"method": "moc"},
            "boundary_conditions": {"upstream": {"type": "h", "value": 100}, "downstream": {"type": "h", "value": 0}},
            "pipe": {"length": 300, "diameter": 0.3, "initial_flow": 0.3, "upstream_head": 80, "n_cells": 50},
            "valve": {"closure_time": 1.0},
        }
        create_resp = client.post(
            "/api/jobs", headers=auth_header,
            json={"config": config, "name": "E2E Water Hammer"},
        )
        job_id = create_resp.json()["id"]

        run_resp = client.post(f"/api/jobs/{job_id}/run", headers=auth_header)
        assert run_resp.status_code == 200

        status_resp = client.get(f"/api/jobs/{job_id}", headers=auth_header)
        job_data = status_resp.json()
        assert job_data["status"] == "completed", f"Job failed: {job_data.get('error')}"

        results_resp = client.get(f"/api/jobs/{job_id}/results", headers=auth_header)
        results = results_resp.json()
        assert results["summary"]["simulation_type"] == "water_hammer"
        assert results["summary"]["pressure_surge"] > 0
        assert results["summary"]["wave_speed"] > 0

    def test_ice_simulation_e2e(self, client, auth_header):
        """Full pipeline for ice simulation."""
        config = {
            "simulation": {"type": "ice_simulation", "end_time": 86400 * 7, "dt": 3600, "mode": "single_canal"},
            "canal": {"length": 500, "width": 10, "slope": 0.001, "manning_n": 0.025, "n_cells": 50},
            "solver": {"method": "stefan"},
            "boundary_conditions": {"upstream": {"type": "h", "value": 2}, "downstream": {"type": "h", "value": 1.5}},
            "ice": {"water_temperature": 0.0, "air_temperature": -15.0, "initial_ice_thickness": 0.0, "T_freeze": 0.0},
        }
        create_resp = client.post(
            "/api/jobs", headers=auth_header,
            json={"config": config, "name": "E2E Ice Simulation"},
        )
        job_id = create_resp.json()["id"]

        run_resp = client.post(f"/api/jobs/{job_id}/run", headers=auth_header)
        assert run_resp.status_code == 200

        status_resp = client.get(f"/api/jobs/{job_id}", headers=auth_header)
        job_data = status_resp.json()
        assert job_data["status"] == "completed", f"Job failed: {job_data.get('error')}"

        results_resp = client.get(f"/api/jobs/{job_id}/results", headers=auth_header)
        results = results_resp.json()
        assert results["summary"]["simulation_type"] == "ice_simulation"
        assert results["summary"]["ice_max_thickness"] > 0


# ===========================================================================
# 2. Error handling in the pipeline
# ===========================================================================
class TestPipelineErrors:
    def test_results_before_run(self, client, auth_header):
        """Cannot get results for a pending job."""
        create_resp = client.post(
            "/api/jobs", headers=auth_header,
            json={"config": {"simulation": {"type": "steady"}}, "name": "Not Run"},
        )
        job_id = create_resp.json()["id"]

        results_resp = client.get(f"/api/jobs/{job_id}/results", headers=auth_header)
        assert results_resp.status_code == 400
        assert "not completed" in results_resp.json()["detail"]

    def test_run_already_running(self, client, auth_header):
        """Cannot start a job that's already running."""
        create_resp = client.post(
            "/api/jobs", headers=auth_header,
            json={"config": {"simulation": {"type": "steady"}}, "name": "Double Run"},
        )
        job_id = create_resp.json()["id"]

        # Manually set status to running via DB
        db = TestingSessionLocal()
        job = db.query(SimulationJob).filter(SimulationJob.id == job_id).first()
        job.status = "running"
        db.commit()
        db.close()

        run_resp = client.post(f"/api/jobs/{job_id}/run", headers=auth_header)
        assert run_resp.status_code == 409

    def test_rerun_completed_job(self, client, auth_header):
        """Can rerun a completed job — should clear old results."""
        config = {
            "simulation": {"type": "steady", "end_time": 20},
            "canal": {"length": 100, "width": 5, "slope": 0.001, "manning_n": 0.025, "n_cells": 20},
            "solver": {"method": "godunov"},
            "boundary_conditions": {
                "upstream": {"type": "h", "value": 2.0},
                "downstream": {"type": "h", "value": 1.5},
            },
        }
        create_resp = client.post(
            "/api/jobs", headers=auth_header,
            json={"config": config, "name": "Rerun Test"},
        )
        job_id = create_resp.json()["id"]

        # First run
        client.post(f"/api/jobs/{job_id}/run", headers=auth_header)
        status1 = client.get(f"/api/jobs/{job_id}", headers=auth_header).json()
        assert status1["status"] == "completed"

        # Second run (rerun)
        client.post(f"/api/jobs/{job_id}/run", headers=auth_header)
        status2 = client.get(f"/api/jobs/{job_id}", headers=auth_header).json()
        assert status2["status"] == "completed"

        # Results should still exist
        results_resp = client.get(f"/api/jobs/{job_id}/results", headers=auth_header)
        assert results_resp.status_code == 200

    def test_delete_job_with_results(self, client, auth_header):
        """Deleting a completed job should work."""
        config = {
            "simulation": {"type": "steady", "end_time": 20},
            "canal": {"length": 100, "width": 5, "slope": 0.001, "manning_n": 0.025, "n_cells": 20},
            "solver": {"method": "godunov"},
            "boundary_conditions": {
                "upstream": {"type": "h", "value": 2},
                "downstream": {"type": "h", "value": 1.5},
            },
        }
        create_resp = client.post(
            "/api/jobs", headers=auth_header,
            json={"config": config, "name": "Delete Me"},
        )
        job_id = create_resp.json()["id"]

        client.post(f"/api/jobs/{job_id}/run", headers=auth_header)
        status_resp = client.get(f"/api/jobs/{job_id}", headers=auth_header)
        assert status_resp.json()["status"] == "completed"

        del_resp = client.delete(f"/api/jobs/{job_id}", headers=auth_header)
        assert del_resp.status_code == 204

        # Job should be gone
        get_resp = client.get(f"/api/jobs/{job_id}", headers=auth_header)
        assert get_resp.status_code == 404


# ===========================================================================
# 3. Multi-type job listing
# ===========================================================================
class TestMultiTypeJobList:
    def test_run_multiple_types_and_list(self, client, auth_header):
        """Run different simulation types and verify list/filter."""
        configs = [
            {
                "name": "OC Job",
                "config": {
                    "simulation": {"type": "steady", "end_time": 20},
                    "canal": {"length": 100, "width": 5, "slope": 0.001, "manning_n": 0.025, "n_cells": 20},
                    "solver": {"method": "godunov"},
                    "boundary_conditions": {"upstream": {"type": "h", "value": 2}, "downstream": {"type": "h", "value": 1.5}},
                },
            },
            {
                "name": "WQ Job",
                "config": {
                    "simulation": {"type": "water_quality", "end_time": 300, "dt": 10},
                    "canal": {"length": 100, "n_cells": 10, "depth": 2, "velocity": 0.5, "manning_n": 0.025},
                    "water_quality": {"initial_concentration": 5.0},
                },
            },
        ]

        job_ids = []
        for cfg in configs:
            resp = client.post("/api/jobs", headers=auth_header, json=cfg)
            assert resp.status_code == 201
            job_ids.append(resp.json()["id"])

        # Run all
        for jid in job_ids:
            run_resp = client.post(f"/api/jobs/{jid}/run", headers=auth_header)
            assert run_resp.status_code == 200

        # Verify all completed
        for jid in job_ids:
            status_resp = client.get(f"/api/jobs/{jid}", headers=auth_header)
            assert status_resp.json()["status"] == "completed"

        # List all jobs
        list_resp = client.get("/api/jobs", headers=auth_header)
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert data["total"] >= 2

        # Filter by status
        completed_resp = client.get("/api/jobs?status=completed", headers=auth_header)
        assert completed_resp.status_code == 200
        assert completed_resp.json()["total"] >= 2

        pending_resp = client.get("/api/jobs?status=pending", headers=auth_header)
        assert pending_resp.status_code == 200
        assert pending_resp.json()["total"] == 0


# ===========================================================================
# Cleanup
# ===========================================================================
@pytest.fixture(scope="session", autouse=True)
def cleanup_temp_db():
    yield
    try:
        os.unlink(TEST_DB_PATH)
    except OSError:
        pass
