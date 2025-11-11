"""
CRUD operations for database models
Create, Read, Update, Delete operations
"""

from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from .models import Simulation, SimulationMetrics


# ========== Simulation CRUD ==========

def create_simulation(
    db: Session,
    task_id: str,
    name: str,
    config: dict,
    description: Optional[str] = None,
    project_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> Simulation:
    """Create a new simulation record"""
    simulation = Simulation(
        task_id=task_id,
        name=name,
        description=description,
        status='queued',
        progress=0.0,
        config=config,
        project_id=project_id,
        user_id=user_id
    )
    db.add(simulation)
    db.commit()
    db.refresh(simulation)
    return simulation


def get_simulation_by_task_id(db: Session, task_id: str) -> Optional[Simulation]:
    """Get simulation by task_id"""
    return db.query(Simulation).filter(Simulation.task_id == task_id).first()


def get_simulation_by_id(db: Session, simulation_id: int) -> Optional[Simulation]:
    """Get simulation by ID"""
    return db.query(Simulation).filter(Simulation.id == simulation_id).first()


def get_simulations(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    project_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> List[Simulation]:
    """Get list of simulations with optional filters"""
    query = db.query(Simulation)

    if status:
        query = query.filter(Simulation.status == status)
    if project_id:
        query = query.filter(Simulation.project_id == project_id)
    if user_id:
        query = query.filter(Simulation.user_id == user_id)

    return query.order_by(Simulation.created_at.desc()).offset(skip).limit(limit).all()


def update_simulation_status(
    db: Session,
    task_id: str,
    status: str,
    progress: Optional[float] = None,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
    duration: Optional[float] = None,
    error_message: Optional[str] = None
) -> Optional[Simulation]:
    """Update simulation status and timestamps"""
    simulation = get_simulation_by_task_id(db, task_id)
    if not simulation:
        return None

    simulation.status = status
    if progress is not None:
        simulation.progress = progress
    if started_at:
        simulation.started_at = started_at
    if completed_at:
        simulation.completed_at = completed_at
    if duration is not None:
        simulation.duration = duration
    if error_message:
        simulation.error_message = error_message

    db.commit()
    db.refresh(simulation)
    return simulation


def update_simulation_results(
    db: Session,
    task_id: str,
    results: dict
) -> Optional[Simulation]:
    """Update simulation results"""
    simulation = get_simulation_by_task_id(db, task_id)
    if not simulation:
        return None

    simulation.results = results
    db.commit()
    db.refresh(simulation)
    return simulation


def delete_simulation(db: Session, task_id: str) -> bool:
    """Delete simulation by task_id"""
    simulation = get_simulation_by_task_id(db, task_id)
    if not simulation:
        return False

    # Delete associated metrics
    db.query(SimulationMetrics).filter(SimulationMetrics.task_id == task_id).delete()

    # Delete simulation
    db.delete(simulation)
    db.commit()
    return True


def count_simulations(
    db: Session,
    status: Optional[str] = None,
    project_id: Optional[str] = None
) -> int:
    """Count simulations with optional filters"""
    query = db.query(Simulation)

    if status:
        query = query.filter(Simulation.status == status)
    if project_id:
        query = query.filter(Simulation.project_id == project_id)

    return query.count()


# ========== SimulationMetrics CRUD ==========

def create_simulation_metrics(
    db: Session,
    task_id: str,
    metrics: dict
) -> SimulationMetrics:
    """Create simulation metrics record"""
    sim_metrics = SimulationMetrics(
        task_id=task_id,
        mass_conservation_error=metrics['mass_conservation_error'],
        max_depth=metrics['max_depth'],
        min_depth=metrics['min_depth'],
        max_velocity=metrics['max_velocity'],
        max_discharge=metrics['max_discharge'],
        max_froude=metrics['max_froude'],
        mean_depth_final=metrics['mean_depth_final'],
        mean_discharge_final=metrics['mean_discharge_final'],
        total_iterations=metrics['total_iterations'],
        converged=metrics['converged']
    )
    db.add(sim_metrics)
    db.commit()
    return sim_metrics


def get_simulation_metrics(db: Session, task_id: str) -> Optional[SimulationMetrics]:
    """Get simulation metrics by task_id"""
    return db.query(SimulationMetrics).filter(SimulationMetrics.task_id == task_id).first()
