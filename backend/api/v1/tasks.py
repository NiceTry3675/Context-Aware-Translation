"""
Task status tracking API endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta

from ...dependencies import get_db, get_optional_user, get_required_user
from ...models import TaskExecution, TaskStatus, TaskKind, User
from ...schemas.task_execution import (
    TaskExecutionResponse, 
    TaskExecutionListResponse,
    TaskStatsResponse
)
from celery.result import AsyncResult
from ...celery_app import celery_app

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


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
    # Get task execution from database
    task_execution = db.query(TaskExecution).filter_by(id=task_id).first()
    
    if not task_execution:
        # Try to get status directly from Celery
        celery_result = AsyncResult(task_id, app=celery_app)
        
        if celery_result.state == 'PENDING':
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Create response from Celery state
        return TaskExecutionResponse(
            id=task_id,
            status=celery_result.state,
            result=celery_result.result if celery_result.ready() else None,
            created_at=datetime.utcnow()  # Approximation
        )
    
    # Check if user has permission to view this task
    if current_user and task_execution.user_id and task_execution.user_id != current_user.id:
        # User can only see their own tasks (unless admin)
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to view this task")
    
    # Get real-time status from Celery
    celery_result = AsyncResult(task_id, app=celery_app)
    
    # Merge database and Celery information
    response = TaskExecutionResponse(
        id=task_execution.id,
        name=task_execution.name,
        kind=task_execution.kind,
        status=task_execution.status,
        job_id=task_execution.job_id,
        user_id=task_execution.user_id,
        args=task_execution.args,
        kwargs=task_execution.kwargs,
        result=task_execution.result or celery_result.result,
        attempts=task_execution.attempts,
        last_error=task_execution.last_error,
        created_at=task_execution.created_at,
        start_time=task_execution.start_time,
        end_time=task_execution.end_time,
        duration=task_execution.duration,
        queue_duration=task_execution.queue_duration,
        celery_state=celery_result.state,
        celery_info=celery_result.info if celery_result.state not in ['SUCCESS', 'FAILURE'] else None
    )
    
    return response


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
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Build query
    query = db.query(TaskExecution)
    
    # Filter by user (unless admin)
    if not current_user.is_admin:
        query = query.filter(TaskExecution.user_id == current_user.id)
    
    # Apply filters
    if kind:
        query = query.filter(TaskExecution.kind == kind)
    if status:
        query = query.filter(TaskExecution.status == status)
    if job_id:
        query = query.filter(TaskExecution.job_id == job_id)
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    tasks = query.order_by(TaskExecution.created_at.desc()).offset(offset).limit(limit).all()
    
    # Convert to response objects
    task_responses = []
    for task in tasks:
        # Get Celery status
        celery_result = AsyncResult(task.id, app=celery_app)
        
        task_responses.append(TaskExecutionResponse(
            id=task.id,
            name=task.name,
            kind=task.kind,
            status=task.status,
            job_id=task.job_id,
            user_id=task.user_id,
            created_at=task.created_at,
            start_time=task.start_time,
            end_time=task.end_time,
            duration=task.duration,
            celery_state=celery_result.state
        ))
    
    return TaskExecutionListResponse(
        tasks=task_responses,
        total=total,
        offset=offset,
        limit=limit
    )


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
    # Get task execution from database
    task_execution = db.query(TaskExecution).filter_by(id=task_id).first()
    
    if not task_execution:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check permission
    if task_execution.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this task")
    
    # Cancel the Celery task
    celery_app.control.revoke(task_id, terminate=True)
    
    # Update database
    task_execution.status = TaskStatus.REVOKED
    task_execution.end_time = datetime.utcnow()
    task_execution.last_error = "Task cancelled by user"
    db.commit()
    
    return {"message": "Task cancelled successfully", "task_id": task_id}


@router.get("/job/{job_id}/tasks", response_model=List[TaskExecutionResponse])
async def get_job_tasks(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get all tasks associated with a specific job.
    """
    # Get tasks for the job
    tasks = db.query(TaskExecution).filter(
        TaskExecution.job_id == job_id
    ).order_by(TaskExecution.created_at.desc()).all()
    
    # Convert to response objects
    task_responses = []
    for task in tasks:
        # Get Celery status
        celery_result = AsyncResult(task.id, app=celery_app)
        
        task_responses.append(TaskExecutionResponse(
            id=task.id,
            name=task.name,
            kind=task.kind,
            status=task.status,
            job_id=task.job_id,
            created_at=task.created_at,
            start_time=task.start_time,
            end_time=task.end_time,
            duration=task.duration,
            celery_state=celery_result.state,
            last_error=task.last_error
        ))
    
    return task_responses


@router.get("/stats/summary")
async def get_task_stats(
    hours: int = Query(default=24, description="Number of hours to look back"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user)
):
    """
    Get task execution statistics.
    
    Admin only endpoint.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    # Get task counts by status
    status_counts = {}
    for status in TaskStatus:
        count = db.query(TaskExecution).filter(
            and_(
                TaskExecution.created_at >= cutoff_time,
                TaskExecution.status == status
            )
        ).count()
        status_counts[status.value] = count
    
    # Get task counts by kind
    kind_counts = {}
    for kind in TaskKind:
        count = db.query(TaskExecution).filter(
            and_(
                TaskExecution.created_at >= cutoff_time,
                TaskExecution.kind == kind
            )
        ).count()
        kind_counts[kind.value] = count
    
    # Get average duration by kind
    avg_durations = {}
    for kind in TaskKind:
        tasks = db.query(TaskExecution).filter(
            and_(
                TaskExecution.created_at >= cutoff_time,
                TaskExecution.kind == kind,
                TaskExecution.status == TaskStatus.SUCCESS,
                TaskExecution.start_time.isnot(None),
                TaskExecution.end_time.isnot(None)
            )
        ).all()
        
        if tasks:
            durations = [t.duration for t in tasks if t.duration > 0]
            if durations:
                avg_durations[kind.value] = sum(durations) / len(durations)
    
    return {
        "period_hours": hours,
        "status_counts": status_counts,
        "kind_counts": kind_counts,
        "average_durations": avg_durations,
        "total_tasks": sum(status_counts.values())
    }