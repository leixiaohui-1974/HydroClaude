"""
Simulation API endpoints
Handles canal flow simulation requests
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict
import uuid
from datetime import datetime
import logging
import sys
import os

# 添加当前目录到path，以便导入models
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 尝试相对导入，如果失败则使用绝对导入
try:
    from ..models.simulation import (
        SimulationRequest,
        SimulationResponse,
        SimulationStatusResponse,
        SimulationResultResponse,
        SimulationMetrics
    )
except ImportError:
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

# In-memory storage for simulation tasks
# In production, this would be replaced with Redis or a database
simulation_tasks: Dict[str, Dict] = {}

# Add backend path for core module
backend_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


def run_simulation_task(task_id: str, config: dict):
    """
    Background task to run simulation
    Updates simulation_tasks with results
    """
    import io
    import sys as _sys
    import os as _os
    
    # 关键修复：后台任务需要重新设置路径
    # 使用多种方法确保找到backend目录
    possible_paths = [
        '/workspace/web/backend',  # 绝对路径（Linux）
        _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '../../..')),  # 相对路径
        _os.environ.get('PYTHONPATH', '').split(':')[0] if _os.environ.get('PYTHONPATH') else None
    ]
    for path in possible_paths:
        if path and _os.path.exists(path) and path not in _sys.path:
            _sys.path.insert(0, path)
    
    # 在Windows上，完全屏蔽stdout/stderr以避免编码问题
    # 必须在任何其他操作之前屏蔽，包括import
    old_stdout = _sys.stdout
    old_stderr = _sys.stderr
    
    # 立即屏蔽所有输出
    if _sys.platform == 'win32':
        _sys.stdout = io.StringIO()
        _sys.stderr = io.StringIO()
    
    try:
        # Update status to running
        simulation_tasks[task_id]['status'] = 'running'
        simulation_tasks[task_id]['started_at'] = datetime.now()

        # logger.info(f"Starting simulation task {task_id}")  # 禁用以避免编码问题

        # Import engine
        from core.hydraulic_engine import HydraulicEngine

        # Create engine and run simulation
        engine = HydraulicEngine()
        result = engine.run_canal_simulation(task_id, config)

        # Update task with results
        if result.status == 'completed':
            simulation_tasks[task_id]['status'] = 'completed'
            simulation_tasks[task_id]['result'] = result
            simulation_tasks[task_id]['completed_at'] = datetime.now()
            simulation_tasks[task_id]['duration'] = result.duration
            # logger.info(f"Simulation task {task_id} completed successfully")  # 禁用
        else:
            simulation_tasks[task_id]['status'] = 'failed'
            # 安全地处理错误信息，移除任何可能的非ASCII字符
            try:
                error_msg = str(result.error).encode('ascii', 'ignore').decode('ascii') if result.error else "Unknown error"
            except:
                error_msg = "Unknown error (encoding issue)"
            simulation_tasks[task_id]['error'] = error_msg
            simulation_tasks[task_id]['completed_at'] = datetime.now()
            # logger.error(f"Simulation task {task_id} failed: {result.error}")  # 禁用

    except Exception as e:
        # logger.error(f"Simulation task {task_id} encountered error: {e}", exc_info=True)  # 禁用
        simulation_tasks[task_id]['status'] = 'failed'
        # 安全地转换错误信息，移除任何可能的非ASCII字符
        try:
            error_msg = str(e).encode('ascii', 'ignore').decode('ascii')
        except:
            error_msg = "Unknown error (encoding issue)"
        simulation_tasks[task_id]['error'] = error_msg
        simulation_tasks[task_id]['completed_at'] = datetime.now()
    
    finally:
        # 恢复stdout/stderr
        _sys.stdout = old_stdout
        _sys.stderr = old_stderr


@router.post("", response_model=SimulationResponse, status_code=201)
async def create_simulation(
    request: SimulationRequest,
    background_tasks: BackgroundTasks
):
    """
    Create a new canal simulation task

    This endpoint accepts simulation configuration and queues it for execution.
    The simulation runs in the background and results can be retrieved using
    the task_id returned in the response.

    **Example Request:**
    ```json
    {
        "name": "Uniform Flow Test",
        "description": "Testing uniform flow scenario",
        "config": {
            "width": 10.0,
            "length": 1000.0,
            "n_cells": 100,
            "t_end": 10.0,
            "initial_conditions": {
                "type": "uniform",
                "h": 5.0,
                "Q": 0.0
            }
        }
    }
    ```

    **Returns:** Task information including task_id for status tracking
    """
    # Generate unique task ID
    task_id = str(uuid.uuid4())

    # Convert Pydantic model to dict for engine
    config_dict = request.config.dict()

    # Create task record
    task_record = {
        'task_id': task_id,
        'name': request.name,
        'description': request.description,
        'config': config_dict,
        'status': 'queued',
        'created_at': datetime.now(),
        'started_at': None,
        'completed_at': None,
        'duration': None,
        'result': None,
        'error': None
    }

    simulation_tasks[task_id] = task_record

    # Add background task
    background_tasks.add_task(run_simulation_task, task_id, config_dict)

    logger.info(f"Created simulation task {task_id}: {request.name}")

    return SimulationResponse(
        task_id=task_id,
        status='queued',
        name=request.name,
        created_at=task_record['created_at'],
        message="Simulation queued successfully. Use task_id to check status."
    )


@router.get("/{task_id}/status", response_model=SimulationStatusResponse)
async def get_simulation_status(task_id: str):
    """
    Get simulation status

    **Parameters:**
    - **task_id**: Unique task identifier

    **Returns:** Current status and progress information
    """
    if task_id not in simulation_tasks:
        raise HTTPException(status_code=404, detail=f"Simulation task {task_id} not found")

    task = simulation_tasks[task_id]

    # Calculate progress
    progress = None
    if task['status'] == 'queued':
        progress = 0.0
    elif task['status'] == 'running':
        progress = 50.0  # In future, we can track actual progress
    elif task['status'] == 'completed':
        progress = 100.0
    elif task['status'] == 'failed':
        progress = None

    return SimulationStatusResponse(
        task_id=task_id,
        status=task['status'],
        progress=progress,
        created_at=task['created_at'],
        started_at=task.get('started_at'),
        completed_at=task.get('completed_at'),
        duration=task.get('duration'),
        error=task.get('error')
    )


@router.get("/{task_id}/results", response_model=SimulationResultResponse)
async def get_simulation_results(task_id: str):
    """
    Get simulation results

    This endpoint returns the complete simulation results including
    temporal and spatial data for water depth, discharge, and velocity.

    **Parameters:**
    - **task_id**: Unique task identifier

    **Returns:** Complete simulation results with metrics
    """
    if task_id not in simulation_tasks:
        raise HTTPException(status_code=404, detail=f"Simulation task {task_id} not found")

    task = simulation_tasks[task_id]

    if task['status'] != 'completed' and task['status'] != 'failed':
        raise HTTPException(
            status_code=400,
            detail=f"Simulation is not complete yet. Current status: {task['status']}"
        )

    result = task.get('result')

    if result is None:
        raise HTTPException(
            status_code=500,
            detail="Simulation failed with no results available"
        )

    # Convert to response model
    return SimulationResultResponse(
        task_id=result.task_id,
        status=result.status,
        duration=result.duration,
        timestamp=datetime.fromisoformat(result.timestamp),
        x=result.x,
        time=result.time,
        h=result.h,
        Q=result.Q,
        V=result.V,
        metrics=SimulationMetrics(**result.metrics),
        error=result.error
    )


@router.get("", response_model=list[SimulationStatusResponse])
async def list_simulations(
    skip: int = 0,
    limit: int = 100,
    status: str = None
):
    """
    List all simulations

    **Parameters:**
    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return
    - **status**: Filter by status (queued, running, completed, failed)

    **Returns:** List of simulation status records
    """
    # Get all tasks
    tasks = list(simulation_tasks.values())

    # Filter by status if provided
    if status:
        tasks = [t for t in tasks if t['status'] == status]

    # Sort by creation time (newest first)
    tasks.sort(key=lambda x: x['created_at'], reverse=True)

    # Apply pagination
    tasks = tasks[skip:skip + limit]

    # Convert to response models
    results = []
    for task in tasks:
        # Calculate progress
        progress = None
        if task['status'] == 'queued':
            progress = 0.0
        elif task['status'] == 'running':
            progress = 50.0
        elif task['status'] == 'completed':
            progress = 100.0

        results.append(SimulationStatusResponse(
            task_id=task['task_id'],
            status=task['status'],
            progress=progress,
            created_at=task['created_at'],
            started_at=task.get('started_at'),
            completed_at=task.get('completed_at'),
            duration=task.get('duration'),
            error=task.get('error')
        ))

    return results


@router.delete("/{task_id}")
async def delete_simulation(task_id: str):
    """
    Delete a simulation task

    **Parameters:**
    - **task_id**: Unique task identifier

    **Returns:** Success message
    """
    if task_id not in simulation_tasks:
        raise HTTPException(status_code=404, detail=f"Simulation task {task_id} not found")

    task = simulation_tasks[task_id]

    # Don't allow deletion of running tasks
    if task['status'] == 'running':
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a running simulation"
        )

    # Delete task
    del simulation_tasks[task_id]

    logger.info(f"Deleted simulation task {task_id}")

    return {
        "message": f"Simulation task {task_id} deleted successfully",
        "task_id": task_id
    }
