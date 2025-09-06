"""Service layer for task management."""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from celery.result import AsyncResult
from datetime import datetime

from .models import TaskExecution, TaskStatus, TaskKind
from .schemas import (
    TaskExecutionResponse,
    TaskExecutionListResponse,
    TaskStatsSimple
)
from .repository import TaskRepository
from ..user.models import User
from ...celery_app import celery_app


class TaskService:
    """Service for managing background tasks."""
    
    def __init__(self, db: Session):
        self.db = db
        self.repo = TaskRepository(db)
    
    def get_task_status(
        self, 
        task_id: str, 
        current_user: Optional[User] = None
    ) -> TaskExecutionResponse:
        """
        Get the status of a specific task.
        Returns both database tracking info and real-time Celery status.
        """
        # Get task execution from database
        task_execution = self.repo.get_by_id(task_id)
        
        if not task_execution:
            # Try to get status directly from Celery
            celery_result = AsyncResult(task_id, app=celery_app)
            
            if celery_result.state == 'PENDING':
                raise ValueError("Task not found")
            
            # Create response from Celery state
            return TaskExecutionResponse(
                id=task_id,
                kind=TaskKind.OTHER,
                name="Unknown",
                status=TaskStatus.PENDING,
                celery_state=celery_result.state,
                result=celery_result.result if celery_result.ready() else None,
                created_at=datetime.utcnow()
            )
        
        # Check if user has permission to view this task
        if current_user and task_execution.user_id:
            if task_execution.user_id != current_user.id and not self._is_admin(current_user):
                raise PermissionError("Not authorized to view this task")
        
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
            max_retries=task_execution.max_retries,
            last_error=task_execution.last_error,
            created_at=task_execution.created_at,
            updated_at=task_execution.updated_at,
            start_time=task_execution.start_time,
            end_time=task_execution.end_time,
            duration=task_execution.duration,
            queue_duration=task_execution.queue_duration,
            celery_state=celery_result.state,
            celery_info=celery_result.info if celery_result.state not in ['SUCCESS', 'FAILURE'] else None
        )
        
        return response
    
    def list_tasks(
        self,
        current_user: Optional[User] = None,
        kind: Optional[TaskKind] = None,
        status: Optional[TaskStatus] = None,
        job_id: Optional[int] = None,
        limit: int = 20,
        offset: int = 0
    ) -> TaskExecutionListResponse:
        """
        List tasks with optional filters.
        Users can see their own tasks, admins can see all tasks.
        """
        if not current_user:
            raise PermissionError("Authentication required")
        
        # Filter by user unless admin
        user_id = None if self._is_admin(current_user) else current_user.id
        
        tasks, total = self.repo.list_tasks(
            kind=kind,
            status=status,
            job_id=job_id,
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        # Convert to response objects with Celery status
        task_responses = []
        for task in tasks:
            celery_result = AsyncResult(task.id, app=celery_app)
            
            task_responses.append(TaskExecutionResponse(
                id=task.id,
                name=task.name,
                kind=task.kind,
                status=task.status,
                job_id=task.job_id,
                user_id=task.user_id,
                created_at=task.created_at,
                updated_at=task.updated_at,
                start_time=task.start_time,
                end_time=task.end_time,
                duration=task.duration,
                celery_state=celery_result.state,
                last_error=task.last_error
            ))
        
        return TaskExecutionListResponse(
            tasks=task_responses,
            total=total,
            offset=offset,
            limit=limit
        )
    
    def cancel_task(self, task_id: str, current_user: User) -> Dict[str, Any]:
        """
        Cancel a running task.
        Only the task owner or an admin can cancel a task.
        """
        task_execution = self.repo.get_by_id(task_id)
        
        if not task_execution:
            raise ValueError("Task not found")
        
        # Check permission
        if task_execution.user_id != current_user.id and not self._is_admin(current_user):
            raise PermissionError("Not authorized to cancel this task")
        
        # Cancel the Celery task
        celery_app.control.revoke(task_id, terminate=True)
        
        # Update database
        self.repo.cancel_task(task_id)
        
        return {"message": "Task cancelled successfully", "task_id": task_id}
    
    def get_job_tasks(
        self, 
        job_id: int, 
        current_user: Optional[User] = None
    ) -> List[TaskExecutionResponse]:
        """Get all tasks associated with a specific job."""
        tasks = self.repo.get_job_tasks(job_id)
        
        # Convert to response objects
        task_responses = []
        for task in tasks:
            celery_result = AsyncResult(task.id, app=celery_app)
            
            task_responses.append(TaskExecutionResponse(
                id=task.id,
                name=task.name,
                kind=task.kind,
                status=task.status,
                job_id=task.job_id,
                created_at=task.created_at,
                updated_at=task.updated_at,
                start_time=task.start_time,
                end_time=task.end_time,
                duration=task.duration,
                celery_state=celery_result.state,
                last_error=task.last_error
            ))
        
        return task_responses
    
    def get_task_stats(self, hours: int = 24, current_user: Optional[User] = None) -> TaskStatsSimple:
        """
        Get task execution statistics.
        Admin only endpoint.
        """
        if not current_user or not self._is_admin(current_user):
            raise PermissionError("Admin access required")
        
        stats = self.repo.get_stats(hours)
        return TaskStatsSimple(**stats)
    
    def _is_admin(self, user: User) -> bool:
        """Check if user is admin."""
        # Check for is_admin attribute or role
        if hasattr(user, 'is_admin'):
            return user.is_admin
        if hasattr(user, 'role'):
            return user.role in ['admin', 'super_admin']
        return False