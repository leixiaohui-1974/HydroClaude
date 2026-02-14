"""
仿真作业API路由

提供仿真作业的创建、运行、状态查询和结果获取。
"""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models import User, SimulationJob, SimulationResult
from ..models.simulation import Project
from ..schemas import JobCreate, JobPublic, JobList, ResultPublic
from ..utils.dependencies import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Simulation Jobs"])


def _run_simulation(job_id: int, db_url: str):
    """
    在后台运行仿真作业

    使用独立数据库会话，在后台线程中执行仿真计算。
    """
    import numpy as np
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

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
        sim_cfg = config.get("simulation", {})
        canal_cfg = config.get("canal", {})
        solver_cfg = config.get("solver", {})
        bc_cfg = config.get("boundary_conditions", {})

        sim_type = sim_cfg.get("type", "open_channel")
        method = solver_cfg.get("method", "godunov_fvm")

        # 基本参数
        length = canal_cfg.get("length", 1000.0)
        width = canal_cfg.get("width", 10.0)
        slope = canal_cfg.get("slope", 0.001)
        manning_n = canal_cfg.get("manning_n", 0.025)
        n_cells = canal_cfg.get("n_cells", 200)
        end_time = sim_cfg.get("end_time", 100.0)
        cfl = solver_cfg.get("cfl", 0.5)

        # 初始条件
        ic = config.get("initial_conditions", {})
        ic_type = ic.get("type", "uniform")

        dx = length / n_cells
        x = np.linspace(0.5 * dx, length - 0.5 * dx, n_cells)

        if ic_type == "dam_break":
            h_L = ic.get("h_left", 10.0)
            h_R = ic.get("h_right", 1.0)
            dam_pos = ic.get("dam_position", length / 2)
            h_init = np.where(x < dam_pos, h_L, h_R)
            Q_init = np.zeros(n_cells)
        else:
            h_val = ic.get("h", 1.0)
            Q_val = ic.get("Q", 0.0)
            h_init = np.ones(n_cells) * h_val
            Q_init = np.ones(n_cells) * Q_val

        # 边界条件
        bc_left = _parse_bc(bc_cfg.get("upstream", {"type": "h", "value": float(h_init[0])}))
        bc_right = _parse_bc(bc_cfg.get("downstream", {"type": "h", "value": float(h_init[-1])}))

        # 创建求解器并运行
        import sys
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        from solvers.godunov_fvm_solver import GodunvFVMSolver

        solver = GodunvFVMSolver(
            width=width,
            length=length,
            n_cells=n_cells,
            manning_n=manning_n,
            slope=slope,
            g=9.81,
            cfl=cfl,
            eps_dry=1e-6,
            order=solver_cfg.get("order", 1),
            riemann_solver=solver_cfg.get("riemann_solver", "hll"),
            well_balanced=solver_cfg.get("well_balanced", True),
            use_numba=False,
        )

        solver.initialize(h_init, Q_init, bc_left, bc_right)

        # 时间步进
        output_interval = max(end_time / 50, solver.compute_dt())
        next_output_time = output_interval
        snapshots = [{"t": 0.0, "h_max": float(np.max(h_init)), "h_min": float(np.min(h_init)),
                       "Q_max": float(np.max(Q_init))}]
        max_steps = solver_cfg.get("max_steps", 100000)
        step = 0

        while solver.t < end_time and step < max_steps:
            solver.step()
            step += 1

            if solver.t >= next_output_time:
                state = solver.get_state()
                snapshots.append({
                    "t": float(state["t"]),
                    "h_max": float(np.max(state["h"])),
                    "h_min": float(np.min(state["h"])),
                    "Q_max": float(np.max(np.abs(state["Q"]))),
                    "mass_error": float(state.get("mass_error", 0.0)),
                })
                next_output_time += output_interval

                # 更新进度
                progress = min(solver.t / end_time * 100.0, 99.0)
                job.progress = progress
                db.commit()

        # 获取最终状态
        final_state = solver.get_state()

        # 保存结果
        result = SimulationResult(
            job_id=job.id,
            summary={
                "final_time": float(final_state["t"]),
                "total_steps": step,
                "h_max": float(np.max(final_state["h"])),
                "h_min": float(np.min(final_state["h"])),
                "h_mean": float(np.mean(final_state["h"])),
                "Q_max": float(np.max(final_state["Q"])),
                "mass_error_percent": float(final_state.get("mass_error", 0.0)),
                "stable": bool(not np.any(np.isnan(final_state["h"]))),
            },
            time_series={
                "snapshots": snapshots,
                "x": x.tolist(),
                "h_final": final_state["h"].tolist(),
                "Q_final": final_state["Q"].tolist(),
            },
            solver_metadata={
                "solver": method,
                "n_cells": n_cells,
                "cfl": cfl,
                "end_time": end_time,
            },
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


def _parse_bc(bc_dict):
    """解析边界条件配置"""
    if bc_dict is None:
        return {"type": "h", "value": 1.0}
    bc_type = bc_dict.get("type", "h")
    value = bc_dict.get("value", 1.0)
    return {"type": bc_type, "value": value}


@router.post("", response_model=JobPublic, status_code=status.HTTP_201_CREATED)
async def create_job(
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
