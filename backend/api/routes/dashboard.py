"""
Dashboard API routes.

Provides aggregated statistics and SSE (Server-Sent Events) for real-time
simulation progress streaming.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, SimulationJob, SimulationResult, Project, Plugin
from ..utils.dependencies import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return aggregated statistics for the current user's dashboard."""
    user_id = current_user.id

    total_projects = db.query(func.count(Project.id)).filter(
        Project.user_id == user_id
    ).scalar() or 0

    running_jobs = db.query(func.count(SimulationJob.id)).filter(
        SimulationJob.user_id == user_id,
        SimulationJob.status == "running",
    ).scalar() or 0

    completed_jobs = db.query(func.count(SimulationJob.id)).filter(
        SimulationJob.user_id == user_id,
        SimulationJob.status == "completed",
    ).scalar() or 0

    pending_jobs = db.query(func.count(SimulationJob.id)).filter(
        SimulationJob.user_id == user_id,
        SimulationJob.status == "pending",
    ).scalar() or 0

    failed_jobs = db.query(func.count(SimulationJob.id)).filter(
        SimulationJob.user_id == user_id,
        SimulationJob.status == "failed",
    ).scalar() or 0

    # Recent jobs for timeline
    recent_jobs = (
        db.query(SimulationJob)
        .filter(SimulationJob.user_id == user_id)
        .order_by(SimulationJob.created_at.desc())
        .limit(5)
        .all()
    )

    recent_list = []
    for job in recent_jobs:
        recent_list.append({
            "id": job.id,
            "name": job.name,
            "status": job.status,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        })

    return {
        "total_projects": total_projects,
        "running_jobs": running_jobs,
        "completed_jobs": completed_jobs,
        "pending_jobs": pending_jobs,
        "failed_jobs": failed_jobs,
        "recent_jobs": recent_list,
    }


@router.get("/jobs/{job_id}/stream")
async def stream_job_progress(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Stream simulation job progress via Server-Sent Events (SSE).

    The client should use an EventSource to connect:
        const es = new EventSource('/api/jobs/{jobId}/stream');
        es.onmessage = (e) => { const data = JSON.parse(e.data); ... };
    """
    job = db.query(SimulationJob).filter(
        SimulationJob.id == job_id,
        SimulationJob.user_id == current_user.id,
    ).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    async def event_generator():
        from ..database import SessionLocal
        while True:
            local_db = SessionLocal()
            try:
                job = local_db.query(SimulationJob).filter(
                    SimulationJob.id == job_id
                ).first()
                if not job:
                    yield f"data: {json.dumps({'status': 'not_found'})}\n\n"
                    break

                payload = {
                    "status": job.status,
                    "progress": job.progress,
                    "error": job.error,
                }

                yield f"data: {json.dumps(payload)}\n\n"

                if job.status in ("completed", "failed"):
                    break
            finally:
                local_db.close()

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
