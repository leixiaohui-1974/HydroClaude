"""
仿真相关的Pydantic模型
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Any, Dict, List, Literal
from datetime import datetime


# ====== Project Schemas ======

class ProjectCreate(BaseModel):
    """创建项目请求"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    config: Optional[Dict[str, Any]] = None


class ProjectUpdate(BaseModel):
    """更新项目请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    config: Optional[Dict[str, Any]] = None
    status: Optional[Literal["draft", "active", "archived"]] = None


class ProjectPublic(BaseModel):
    """项目公开信息"""
    id: int
    name: str
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProjectList(BaseModel):
    """项目列表"""
    total: int
    items: List[ProjectPublic]


# ====== Simulation Job Schemas ======

class JobCreate(BaseModel):
    """创建仿真作业请求"""
    name: Optional[str] = None
    config: Dict[str, Any]
    project_id: Optional[int] = None


class JobPublic(BaseModel):
    """仿真作业公开信息"""
    id: int
    name: str
    config: Dict[str, Any]
    status: str
    progress: float
    error: Optional[str] = None
    project_id: Optional[int] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class JobList(BaseModel):
    """作业列表"""
    total: int
    items: List[JobPublic]


# ====== Simulation Result Schemas ======

class ResultPublic(BaseModel):
    """仿真结果公开信息"""
    id: int
    job_id: int
    summary: Optional[Dict[str, Any]] = None
    time_series: Optional[Dict[str, Any]] = None
    solver_metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
