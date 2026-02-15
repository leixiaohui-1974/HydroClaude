"""
仿真项目和作业数据库模型
"""

from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class Project(Base):
    """仿真项目模型"""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    config = Column(JSON, nullable=True)

    # 状态
    status = Column(String(20), default="draft", index=True)  # draft, active, archived

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    owner = relationship("User", backref="projects")
    jobs = relationship("SimulationJob", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}')>"


class SimulationJob(Base):
    """仿真作业模型"""
    __tablename__ = "simulation_jobs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    name = Column(String(200), nullable=False)
    config = Column(JSON, nullable=False)

    # 运行状态
    status = Column(String(20), default="pending", index=True)  # pending, running, completed, failed
    progress = Column(Float, default=0.0)  # 0.0 - 100.0
    error = Column(Text, nullable=True)

    # 运行时间
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    project = relationship("Project", back_populates="jobs")
    owner = relationship("User", backref="simulation_jobs")
    results = relationship("SimulationResult", back_populates="job", cascade="all, delete-orphan",
                           uselist=False)

    def __repr__(self):
        return f"<SimulationJob(id={self.id}, name='{self.name}', status='{self.status}')>"


class SimulationResult(Base):
    """仿真结果模型"""
    __tablename__ = "simulation_results"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("simulation_jobs.id"), nullable=False, unique=True)

    # 结果数据
    summary = Column(JSON, nullable=True)        # 结果摘要（水深、流速统计等）
    time_series = Column(JSON, nullable=True)     # 时间序列关键点数据
    solver_metadata = Column("metadata", JSON, nullable=True)  # 元数据（求解器信息、网格信息等）

    # 结果文件路径（用于大型结果数据）
    result_file = Column(String(500), nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    job = relationship("SimulationJob", back_populates="results")

    def __repr__(self):
        return f"<SimulationResult(id={self.id}, job_id={self.job_id})>"
