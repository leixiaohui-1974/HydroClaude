"""
仿真作业API路由

提供仿真作业的创建、运行、状态查询和结果获取。
"""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks, Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from typing import Optional
from ..database import get_db
from ..models import User, SimulationJob, SimulationResult
from ..models.simulation import Project
from ..schemas import JobCreate, JobPublic, JobList, ResultPublic
from ..utils.dependencies import get_current_active_user

from ..utils.limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Simulation Jobs"])


def _run_simulation(job_id: int, db_url: str):
    """
    Run a simulation job in the background.

    Uses an independent DB session and dispatches to the appropriate solver
    via the multi-physics simulation dispatcher.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from .simulation_dispatcher import dispatch

    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        job = db.query(SimulationJob).filter(SimulationJob.id == job_id).first()
        if not job:
            return

        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        job.progress = 0.0
        db.commit()

        config = job.config
        sim_type = config.get("simulation", {}).get("type", "open_channel")

        def progress_cb(pct: float):
            job.progress = pct
            db.commit()

        result_data = dispatch(sim_type, config, progress_cb=progress_cb)

        result = SimulationResult(
            job_id=job.id,
            summary=result_data["summary"],
            time_series=result_data["time_series"],
            solver_metadata=result_data["solver_metadata"],
        )
        db.add(result)

        job.status = "completed"
        job.progress = 100.0
        job.completed_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as e:
        logger.error(f"Simulation job {job_id} failed: {e}", exc_info=True)
        job = db.query(SimulationJob).filter(SimulationJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.error = f"{type(e).__name__}: {str(e)}"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()
        engine.dispose()


@router.get("/simulation-types")
async def list_simulation_types():
    """Return all supported simulation types and their descriptions."""
    from .simulation_dispatcher import get_supported_simulation_types
    return {"types": get_supported_simulation_types()}


@router.post("", response_model=JobPublic, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_job(
    request: Request,
    data: JobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """创建仿真作业"""
    # 验证 project_id（如果提供）
    if data.project_id is not None:
        project = db.query(Project).filter(
            Project.id == data.project_id,
            Project.user_id == current_user.id,
        ).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or does not belong to current user"
            )

    name = data.name or f"Simulation-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    job = SimulationJob(
        user_id=current_user.id,
        project_id=data.project_id,
        name=name,
        config=data.config,
        status="pending",
        progress=0.0,
    )
    try:
        db.add(job)
        db.commit()
        db.refresh(job)
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to create simulation job for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create simulation job"
        )
    logger.info(f"Simulation job created: '{name}' (id={job.id}) by user {current_user.username}")
    return job


@router.get("", response_model=JobList)
async def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取当前用户的仿真作业列表"""
    valid_statuses = {"pending", "running", "completed", "failed"}
    query = db.query(SimulationJob).filter(SimulationJob.user_id == current_user.id)
    if status_filter:
        if status_filter not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status filter. Must be one of: {', '.join(valid_statuses)}"
            )
        query = query.filter(SimulationJob.status == status_filter)
    total = query.count()
    items = query.order_by(SimulationJob.created_at.desc()).offset(skip).limit(limit).all()
    return JobList(total=total, items=items)


@router.get("/{job_id}", response_model=JobPublic)
async def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取作业详情"""
    job = db.query(SimulationJob).filter(
        SimulationJob.id == job_id,
        SimulationJob.user_id == current_user.id,
    ).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.post("/{job_id}/run", response_model=JobPublic)
async def run_job(
    job_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """运行仿真作业（后台异步执行）"""
    job = db.query(SimulationJob).filter(
        SimulationJob.id == job_id,
        SimulationJob.user_id == current_user.id,
    ).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.status == "running":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job is already running")

    # 清除旧结果并重置状态
    try:
        old_result = db.query(SimulationResult).filter(SimulationResult.job_id == job_id).first()
        if old_result:
            db.delete(old_result)

        job.status = "pending"
        job.progress = 0.0
        job.error = None
        db.commit()
        db.refresh(job)
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to reset and run job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start simulation job"
        )

    # 在后台线程运行仿真
    from ..config import settings
    background_tasks.add_task(_run_simulation, job.id, settings.DATABASE_URL)

    logger.info(f"Simulation job started: id={job.id}")
    return job


@router.get("/{job_id}/results", response_model=ResultPublic)
async def get_job_results(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取作业结果"""
    job = db.query(SimulationJob).filter(
        SimulationJob.id == job_id,
        SimulationJob.user_id == current_user.id,
    ).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is not completed (status: {job.status})"
        )

    result = db.query(SimulationResult).filter(SimulationResult.job_id == job_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Results not found")

    return result


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """删除作业"""
    job = db.query(SimulationJob).filter(
        SimulationJob.id == job_id,
        SimulationJob.user_id == current_user.id,
    ).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.status == "running":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a running job"
        )

    try:
        db.delete(job)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to delete job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete simulation job"
        )
