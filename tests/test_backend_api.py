"""
Backend API 综合测试

测试项目管理、仿真作业、数据库模型等。
使用 FastAPI TestClient 进行同步测试，不需要服务器运行。
"""

import pytest
import sys
from pathlib import Path

# 确保项目根路径在 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.api.database import Base, get_db
from backend.api.main import app
from backend.api.models import User, Project, SimulationJob, SimulationResult
from backend.api.utils.security import get_password_hash

# ====== 测试数据库设置 ======

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_hydroclaude.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """每个测试前重建数据库"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """获取数据库会话"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db_session):
    """创建测试用户"""
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=get_password_hash("testpass123"),
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    """获取认证头"""
    client = TestClient(app)
    response = client.post(
        "/api/auth/login",
        data={"username": "testuser", "password": "testpass123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client():
    """测试客户端"""
    return TestClient(app)


# ====== 认证测试 ======

class TestAuth:
    """认证API测试"""

    def test_register(self, client):
        """测试用户注册"""
        response = client.post("/api/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "newpass123",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["id"] is not None

    def test_register_duplicate_username(self, client, test_user):
        """测试重复用户名注册"""
        response = client.post("/api/auth/register", json={
            "username": "testuser",
            "email": "other@example.com",
            "password": "pass123",
        })
        assert response.status_code == 400

    def test_login(self, client, test_user):
        """测试用户登录"""
        response = client.post("/api/auth/login", data={
            "username": "testuser",
            "password": "testpass123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user):
        """测试错误密码登录"""
        response = client.post("/api/auth/login", data={
            "username": "testuser",
            "password": "wrongpass",
        })
        assert response.status_code == 401


# ====== 项目管理测试 ======

class TestProjects:
    """项目管理API测试"""

    def test_create_project(self, client, auth_headers):
        """测试创建项目"""
        response = client.post("/api/projects", json={
            "name": "Test Project",
            "description": "A test project",
            "config": {"canal": {"length": 1000, "width": 10}},
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Project"
        assert data["status"] == "draft"
        assert data["config"]["canal"]["length"] == 1000

    def test_list_projects(self, client, auth_headers):
        """测试获取项目列表"""
        # 创建2个项目
        for i in range(2):
            client.post("/api/projects", json={
                "name": f"Project {i}",
            }, headers=auth_headers)

        response = client.get("/api/projects", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_get_project(self, client, auth_headers):
        """测试获取单个项目"""
        create_resp = client.post("/api/projects", json={
            "name": "My Project",
        }, headers=auth_headers)
        project_id = create_resp.json()["id"]

        response = client.get(f"/api/projects/{project_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == "My Project"

    def test_update_project(self, client, auth_headers):
        """测试更新项目"""
        create_resp = client.post("/api/projects", json={
            "name": "Old Name",
        }, headers=auth_headers)
        project_id = create_resp.json()["id"]

        response = client.put(f"/api/projects/{project_id}", json={
            "name": "New Name",
            "config": {"solver": {"method": "godunov_fvm"}},
        }, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == "New Name"
        assert response.json()["config"]["solver"]["method"] == "godunov_fvm"

    def test_delete_project(self, client, auth_headers):
        """测试删除项目"""
        create_resp = client.post("/api/projects", json={
            "name": "To Delete",
        }, headers=auth_headers)
        project_id = create_resp.json()["id"]

        response = client.delete(f"/api/projects/{project_id}", headers=auth_headers)
        assert response.status_code == 204

        # 确认已删除
        get_resp = client.get(f"/api/projects/{project_id}", headers=auth_headers)
        assert get_resp.status_code == 404

    def test_project_not_found(self, client, auth_headers):
        """测试访问不存在的项目"""
        response = client.get("/api/projects/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_unauthorized_access(self, client):
        """测试未认证访问"""
        response = client.get("/api/projects")
        assert response.status_code == 401


# ====== 仿真作业测试 ======

class TestSimulationJobs:
    """仿真作业API测试"""

    SAMPLE_CONFIG = {
        "simulation": {"type": "open_channel", "end_time": 10.0},
        "canal": {"length": 200, "width": 10, "slope": 0.001, "manning_n": 0.025, "n_cells": 50},
        "solver": {"method": "godunov_fvm", "cfl": 0.5},
        "initial_conditions": {"type": "dam_break", "h_left": 5.0, "h_right": 1.0},
        "boundary_conditions": {
            "upstream": {"type": "h", "value": 5.0},
            "downstream": {"type": "h", "value": 1.0},
        },
    }

    def test_create_job(self, client, auth_headers):
        """测试创建仿真作业"""
        response = client.post("/api/jobs", json={
            "name": "Dam Break Test",
            "config": self.SAMPLE_CONFIG,
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Dam Break Test"
        assert data["status"] == "pending"
        assert data["progress"] == 0.0

    def test_create_job_auto_name(self, client, auth_headers):
        """测试创建作业（自动生成名称）"""
        response = client.post("/api/jobs", json={
            "config": self.SAMPLE_CONFIG,
        }, headers=auth_headers)
        assert response.status_code == 201
        assert response.json()["name"].startswith("Simulation-")

    def test_list_jobs(self, client, auth_headers):
        """测试获取作业列表"""
        for i in range(3):
            client.post("/api/jobs", json={
                "name": f"Job {i}",
                "config": self.SAMPLE_CONFIG,
            }, headers=auth_headers)

        response = client.get("/api/jobs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3

    def test_get_job(self, client, auth_headers):
        """测试获取作业详情"""
        create_resp = client.post("/api/jobs", json={
            "name": "My Job",
            "config": self.SAMPLE_CONFIG,
        }, headers=auth_headers)
        job_id = create_resp.json()["id"]

        response = client.get(f"/api/jobs/{job_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == "My Job"

    def test_delete_job(self, client, auth_headers):
        """测试删除作业"""
        create_resp = client.post("/api/jobs", json={
            "name": "To Delete",
            "config": self.SAMPLE_CONFIG,
        }, headers=auth_headers)
        job_id = create_resp.json()["id"]

        response = client.delete(f"/api/jobs/{job_id}", headers=auth_headers)
        assert response.status_code == 204

    def test_get_results_not_completed(self, client, auth_headers):
        """测试获取未完成作业的结果"""
        create_resp = client.post("/api/jobs", json={
            "config": self.SAMPLE_CONFIG,
        }, headers=auth_headers)
        job_id = create_resp.json()["id"]

        response = client.get(f"/api/jobs/{job_id}/results", headers=auth_headers)
        assert response.status_code == 400

    def test_job_not_found(self, client, auth_headers):
        """测试访问不存在的作业"""
        response = client.get("/api/jobs/99999", headers=auth_headers)
        assert response.status_code == 404


# ====== 数据库模型测试 ======

class TestModels:
    """数据库模型测试"""

    def test_project_model(self, db_session, test_user):
        """测试项目模型"""
        project = Project(
            user_id=test_user.id,
            name="Test",
            config={"key": "value"},
            status="draft",
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        assert project.id is not None
        assert project.name == "Test"
        assert project.config["key"] == "value"
        assert project.created_at is not None

    def test_simulation_job_model(self, db_session, test_user):
        """测试仿真作业模型"""
        job = SimulationJob(
            user_id=test_user.id,
            name="Job Test",
            config={"solver": "hll"},
            status="pending",
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        assert job.id is not None
        assert job.status == "pending"
        assert job.progress == 0.0

    def test_simulation_result_model(self, db_session, test_user):
        """测试仿真结果模型"""
        job = SimulationJob(
            user_id=test_user.id,
            name="Result Test",
            config={},
        )
        db_session.add(job)
        db_session.commit()

        result = SimulationResult(
            job_id=job.id,
            summary={"h_max": 10.0, "stable": True},
            solver_metadata={"solver": "godunov"},
        )
        db_session.add(result)
        db_session.commit()
        db_session.refresh(result)

        assert result.id is not None
        assert result.summary["h_max"] == 10.0
        assert result.job.name == "Result Test"

    def test_project_cascade_delete(self, db_session, test_user):
        """测试项目级联删除"""
        project = Project(
            user_id=test_user.id,
            name="Cascade Test",
            config={},
        )
        db_session.add(project)
        db_session.commit()

        job = SimulationJob(
            user_id=test_user.id,
            project_id=project.id,
            name="Child Job",
            config={},
        )
        db_session.add(job)
        db_session.commit()

        # 删除项目应级联删除作业
        db_session.delete(project)
        db_session.commit()

        remaining = db_session.query(SimulationJob).filter(
            SimulationJob.project_id == project.id
        ).count()
        assert remaining == 0


# ====== 健康检查测试 ======

class TestHealthCheck:
    """健康检查和基础端点测试"""

    def test_health(self, client):
        """测试健康检查"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_root(self, client):
        """测试根路径"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "version" in data


# ====== 清理 ======

@pytest.fixture(scope="session", autouse=True)
def cleanup():
    """测试完成后清理临时数据库"""
    yield
    import os
    try:
        os.remove("test_hydroclaude.db")
    except OSError:
        pass
