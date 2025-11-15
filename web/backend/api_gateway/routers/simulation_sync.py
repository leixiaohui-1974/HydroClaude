"""
Synchronous Simulation API - for testing and simple cases
Bypasses BackgroundTasks issue
"""

import sys
import os

# 强制添加backend路径（必须在其他导入之前）
_backend_path = '/workspace/web/backend'
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

from fastapi import APIRouter, HTTPException
from typing import Dict
import uuid
from datetime import datetime
import logging

from core.hydraulic_engine import HydraulicEngine

try:
    from ..models.simulation import (
        SimulationRequest,
        SimulationResponse,
        SimulationResultResponse,
        SimulationMetrics
    )
except ImportError:
    from models.simulation import (
        SimulationRequest,
        SimulationResponse,
        SimulationResultResponse,
        SimulationMetrics
    )

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/simulations-sync",
    tags=["Simulations-Sync"]
)

@router.post("", response_model=SimulationResultResponse, status_code=201)
def create_simulation_sync(request: SimulationRequest):
    """
    Create and run simulation synchronously (blocking)
    Returns results immediately
    """
    task_id = str(uuid.uuid4())
    created_at = datetime.now()
    
    logger.info(f"Running sync simulation: {request.name}")
    
    try:
        # Create engine and run
        engine = HydraulicEngine()
        result = engine.run_canal_simulation(request.name, request.config.model_dump())
        
        if result.status != 'completed':
            raise HTTPException(
                status_code=500,
                detail=f"Simulation failed: {result.error}"
            )
        
        # Build response
        metrics = SimulationMetrics(
            mass_conservation_error=result.metrics['mass_conservation_error'],
            max_depth=result.metrics['max_depth'],
            min_depth=result.metrics['min_depth'],
            max_velocity=result.metrics['max_velocity'],
            max_discharge=result.metrics['max_discharge'],
            max_froude=result.metrics['max_froude'],
            mean_depth_final=result.metrics['mean_depth_final'],
            mean_discharge_final=result.metrics['mean_discharge_final'],
            total_iterations=result.metrics['total_iterations'],
            converged=result.metrics['converged']
        )
        
        response = SimulationResultResponse(
            task_id=task_id,
            status='completed',
            duration=result.duration,
            timestamp=datetime.now(),
            x=result.spatial_data['x'].tolist(),
            time=result.temporal_data['time'].tolist(),
            h=result.solution_data['h'].tolist(),
            Q=result.solution_data['Q'].tolist(),
            V=result.solution_data['V'].tolist(),
            metrics=metrics
        )
        
        logger.info(f"Sync simulation completed: {task_id}")
        return response
        
    except Exception as e:
        logger.error(f"Sync simulation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
