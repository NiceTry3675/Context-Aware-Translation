"""Task management API routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...config.dependencies import get_db, get_optional_user, get_required_user
from ..user.models import User
from .models import TaskKind, TaskStatus
from .schemas import (
    TaskExecutionResponse,
    TaskExecutionListResponse,
    TaskStatsSimple
)
from .service import TaskService


router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}", response_model=TaskExecutionResponse)
async def get_task_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get the status of a specific task.
    
    Returns both database tracking info and real-time Celery status.
    """
    service = TaskService(db)
    
    try:
        return service.get_task_status(task_id, current_user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/", response_model=TaskExecutionListResponse)
async def list_tasks(
    kind: Optional[TaskKind] = None,
    status: Optional[TaskStatus] = None,
    job_id: Optional[int] = None,
    limit: int = Query(default=20, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    List tasks with optional filters.
    
    - Users can see their own tasks
    - Admins can see all tasks
    - Anonymous users can't see any tasks
    """
    service = TaskService(db)
    
    try:
        return service.list_tasks(
            current_user=current_user,
            kind=kind,
            status=status,
            job_id=job_id,
            limit=limit,
            offset=offset
        )
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user)
):
    """
    Cancel a running task.
    
    Only the task owner or an admin can cancel a task.
    """
    service = TaskService(db)
    
    try:
        return service.cancel_task(task_id, current_user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/job/{job_id}/tasks", response_model=List[TaskExecutionResponse])
async def get_job_tasks(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get all tasks associated with a specific job.
    """
    service = TaskService(db)
    return service.get_job_tasks(job_id, current_user)


@router.get("/stats/summary", response_model=TaskStatsSimple)
async def get_task_stats(
    hours: int = Query(default=24, description="Number of hours to look back"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user)
):
    """
    Get task execution statistics.
    
    Admin only endpoint.
    """
    service = TaskService(db)
    
    try:
        return service.get_task_stats(hours, current_user)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))