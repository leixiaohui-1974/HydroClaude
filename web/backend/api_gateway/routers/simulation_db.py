"""
Simulation API endpoints (Database version)
Handles canal flow simulation requests with database persistence
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from typing import Optional
import uuid
from datetime import datetime
import logging
import sys
import os

from models.simulation import (
    SimulationRequest,
    SimulationResponse,
    SimulationStatusResponse,
    SimulationResultResponse,
    SimulationMetrics
)

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/v1/simulations",
    tags=["Simulations"]
)

# Add backend path for core module and database
backend_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from shared.database import get_db, crud


def run_simulation_task(task_id: str, config: dict):
    """
    Background task to run simulation
    Updates database with results
    """
    from shared.database import SessionLocal

    db = SessionLocal()
    try:
        # Update status to running
        crud.update_simulation_status(
            db=db,
            task_id=task_id,
            status='running',
            started_at=datetime.now(),
            progress=10.0
        )

        logger.info(f"Starting simulation task {task_id}")

        # Import engine
        from core.hydraulic_engine import HydraulicEngine

        # Create engine and run simulation
        engine = HydraulicEngine()
        result = engine.run_canal_simulation(task_id, config)

        # Update database with results
        if result.status == 'completed':
            # Store full results
            results_dict = {
                'x': result.x,
                'time': result.time,
                'h': result.h,
                'Q': result.Q,
                'V': result.V,
                'timestamp': result.timestamp
            }

            crud.update_simulation_results(db=db, task_id=task_id, results=results_dict)
            crud.update_simulation_status(
                db=db,
                task_id=task_id,
                status='completed',
                progress=100.0,
                completed_at=datetime.now(),
                duration=result.duration
            )

            # Store metrics
            crud.create_simulation_metrics(db=db, task_id=task_id, metrics=result.metrics)

            logger.info(f"Simulation task {task_id} completed successfully")
        else:
            crud.update_simulation_status(
                db=db,
                task_id=task_id,
                status='failed',
                completed_at=datetime.now(),
                error_message=result.error
            )
            logger.error(f"Simulation task {task_id} failed: {result.error}")

    except Exception as e:
        logger.error(f"Simulation task {task_id} encountered error: {e}", exc_info=True)
        crud.update_simulation_status(
            db=db,
            task_id=task_id,
            status='failed',
            completed_at=datetime.now(),
            error_message=str(e)
        )
    finally:
        db.close()


@router.post("", response_model=SimulationResponse, status_code=201)
async def create_simulation(
    request: SimulationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create a new canal simulation task

    This endpoint accepts simulation configuration and queues it for execution.
    The simulation runs in the background and results can be retrieved using
    the task_id returned in the response.
    """
    # Generate unique task ID
    task_id = str(uuid.uuid4())

    # Convert Pydantic model to dict for engine
    config_dict = request.config.dict()

    # Create database record
    simulation = crud.create_simulation(
        db=db,
        task_id=task_id,
        name=request.name,
        description=request.description,
        config=config_dict,
        project_id=request.project_id
    )

    # Add background task
    background_tasks.add_task(run_simulation_task, task_id, config_dict)

    logger.info(f"Created simulation task {task_id}: {request.name}")

    return SimulationResponse(
        task_id=task_id,
        status='queued',
        name=request.name,
        created_at=simulation.created_at,
        message="Simulation queued successfully. Use task_id to check status."
    )


@router.get("/{task_id}/status", response_model=SimulationStatusResponse)
async def get_simulation_status(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Get simulation status
    """
    simulation = crud.get_simulation_by_task_id(db, task_id)

    if not simulation:
        raise HTTPException(status_code=404, detail=f"Simulation task {task_id} not found")

    # Calculate progress
    progress = simulation.progress

    return SimulationStatusResponse(
        task_id=simulation.task_id,
        status=simulation.status,
        progress=progress,
        created_at=simulation.created_at,
        started_at=simulation.started_at,
        completed_at=simulation.completed_at,
        duration=simulation.duration,
        error=simulation.error_message
    )


@router.get("/{task_id}/results", response_model=SimulationResultResponse)
async def get_simulation_results(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Get simulation results

    This endpoint returns the complete simulation results including
    temporal and spatial data for water depth, discharge, and velocity.
    """
    simulation = crud.get_simulation_by_task_id(db, task_id)

    if not simulation:
        raise HTTPException(status_code=404, detail=f"Simulation task {task_id} not found")

    if simulation.status != 'completed' and simulation.status != 'failed':
        raise HTTPException(
            status_code=400,
            detail=f"Simulation is not complete yet. Current status: {simulation.status}"
        )

    if simulation.status == 'failed':
        raise HTTPException(
            status_code=500,
            detail=f"Simulation failed: {simulation.error_message}"
        )

    # Get metrics
    metrics_record = crud.get_simulation_metrics(db, task_id)
    if not metrics_record:
        raise HTTPException(
            status_code=500,
            detail="Simulation metrics not found"
        )

    # Get results from database
    results = simulation.results
    if not results:
        raise HTTPException(
            status_code=500,
            detail="Simulation results not available"
        )

    # Convert to response model
    return SimulationResultResponse(
        task_id=simulation.task_id,
        status=simulation.status,
        duration=simulation.duration,
        timestamp=datetime.fromisoformat(results['timestamp']),
        x=results['x'],
        time=results['time'],
        h=results['h'],
        Q=results['Q'],
        V=results['V'],
        metrics=SimulationMetrics(**metrics_record.to_dict()),
        error=simulation.error_message
    )


@router.get("", response_model=list[SimulationStatusResponse])
async def list_simulations(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all simulations
    """
    simulations = crud.get_simulations(
        db=db,
        skip=skip,
        limit=limit,
        status=status
    )

    # Convert to response models
    results = []
    for simulation in simulations:
        results.append(SimulationStatusResponse(
            task_id=simulation.task_id,
            status=simulation.status,
            progress=simulation.progress,
            created_at=simulation.created_at,
            started_at=simulation.started_at,
            completed_at=simulation.completed_at,
            duration=simulation.duration,
            error=simulation.error_message
        ))

    return results


@router.delete("/{task_id}")
async def delete_simulation(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a simulation task
    """
    simulation = crud.get_simulation_by_task_id(db, task_id)

    if not simulation:
        raise HTTPException(status_code=404, detail=f"Simulation task {task_id} not found")

    # Don't allow deletion of running tasks
    if simulation.status == 'running':
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a running simulation"
        )

    # Delete from database
    success = crud.delete_simulation(db, task_id)

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete simulation"
        )

    logger.info(f"Deleted simulation task {task_id}")

    return {
        "message": f"Simulation task {task_id} deleted successfully",
        "task_id": task_id
    }
