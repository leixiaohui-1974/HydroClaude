"""
Database models for HydroClaude Web
SQLAlchemy ORM models for simulation data persistence
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class Simulation(Base):
    """
    Simulation model
    Stores simulation tasks and their configurations
    """
    __tablename__ = "simulations"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Task identification
    task_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Status tracking
    status = Column(String(20), nullable=False, default='queued')  # queued, running, completed, failed
    progress = Column(Float, nullable=True, default=0.0)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Configuration (stored as JSON)
    config = Column(JSON, nullable=False)

    # Results (stored as JSON for completed simulations)
    results = Column(JSON, nullable=True)

    # Performance metrics
    duration = Column(Float, nullable=True)  # Execution time in seconds

    # Error information
    error_message = Column(Text, nullable=True)

    # Metadata
    project_id = Column(String(50), nullable=True, index=True)
    user_id = Column(String(50), nullable=True, index=True)

    def __repr__(self):
        return f"<Simulation(task_id='{self.task_id}', name='{self.name}', status='{self.status}')>"

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'progress': self.progress,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'config': self.config,
            'results': self.results,
            'duration': self.duration,
            'error_message': self.error_message,
            'project_id': self.project_id,
            'user_id': self.user_id
        }


class SimulationMetrics(Base):
    """
    Simulation metrics model
    Stores detailed performance metrics for completed simulations
    """
    __tablename__ = "simulation_metrics"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Foreign key to simulation
    task_id = Column(String(50), index=True, nullable=False)

    # Performance metrics
    mass_conservation_error = Column(Float, nullable=False)
    max_depth = Column(Float, nullable=False)
    min_depth = Column(Float, nullable=False)
    max_velocity = Column(Float, nullable=False)
    max_discharge = Column(Float, nullable=False)
    max_froude = Column(Float, nullable=False)
    mean_depth_final = Column(Float, nullable=False)
    mean_discharge_final = Column(Float, nullable=False)
    total_iterations = Column(Integer, nullable=False)
    converged = Column(Boolean, nullable=False)

    # Timestamp
    created_at = Column(DateTime, nullable=False, default=func.now())

    def __repr__(self):
        return f"<SimulationMetrics(task_id='{self.task_id}', converged={self.converged})>"

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'mass_conservation_error': self.mass_conservation_error,
            'max_depth': self.max_depth,
            'min_depth': self.min_depth,
            'max_velocity': self.max_velocity,
            'max_discharge': self.max_discharge,
            'max_froude': self.max_froude,
            'mean_depth_final': self.mean_depth_final,
            'mean_discharge_final': self.mean_discharge_final,
            'total_iterations': self.total_iterations,
            'converged': self.converged,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
