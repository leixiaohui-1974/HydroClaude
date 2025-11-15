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
    Background task to run simulation using subprocess worker
    Updates simulation_tasks with results
    
    修复方案：使用独立的worker进程运行仿真，避免FastAPI BackgroundTasks的模块导入问题
    """
    import subprocess
    import json
    import tempfile
    
    try:
        # Update status to running
        simulation_tasks[task_id]['status'] = 'running'
        simulation_tasks[task_id]['started_at'] = datetime.now()
        
        # 准备worker脚本路径
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        worker_script = os.path.join(backend_dir, 'run_simulation_worker.py')
        
        # 创建临时文件存储结果
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # 准备配置JSON
            config_json = json.dumps(config, ensure_ascii=False)
            
            # 调用worker脚本
            result = subprocess.run(
                [
                    'python3',
                    worker_script,
                    '--task-id', task_id,
                    '--config', config_json,
                    '--output', tmp_path
                ],
                cwd=backend_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            # 读取结果
            with open(tmp_path, 'r', encoding='utf-8') as f:
                worker_result = json.load(f)
            
            # 更新任务状态
            if worker_result['status'] == 'completed':
                simulation_tasks[task_id]['status'] = 'completed'
                simulation_tasks[task_id]['result'] = worker_result['result']
                simulation_tasks[task_id]['completed_at'] = datetime.now()
                # 计算持续时间
                started = datetime.fromisoformat(worker_result['started_at'])
                completed = datetime.fromisoformat(worker_result['completed_at'])
                simulation_tasks[task_id]['duration'] = (completed - started).total_seconds()
            else:
                simulation_tasks[task_id]['status'] = 'failed'
                simulation_tasks[task_id]['error'] = worker_result.get('error', 'Unknown error')
                simulation_tasks[task_id]['completed_at'] = datetime.now()
        
        finally:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    except subprocess.TimeoutExpired:
        simulation_tasks[task_id]['status'] = 'failed'
        simulation_tasks[task_id]['error'] = 'Simulation timeout (exceeded 5 minutes)'
        simulation_tasks[task_id]['completed_at'] = datetime.now()
    
    except Exception as e:
        simulation_tasks[task_id]['status'] = 'failed'
        simulation_tasks[task_id]['error'] = f'Worker error: {str(e)}'
        simulation_tasks[task_id]['completed_at'] = datetime.now()


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
