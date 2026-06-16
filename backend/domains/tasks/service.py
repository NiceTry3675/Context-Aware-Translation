"""Service layer for task management."""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from .models import TaskExecution, TaskStatus, TaskKind
from .schemas import (
    TaskExecutionResponse,
    TaskExecutionListResponse,
    TaskStatsSimple
)
from .repository import TaskRepository
from ..user.models import User
from ...background.cloud_run import CloudRunJobClient
from ...config.settings import get_settings


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
        Returns database tracking info and background executor progress.
        """
        # Get task execution from database
        task_execution = self.repo.get_by_id(task_id)
        
        if not task_execution:
            raise ValueError("Task not found")
        
        # Check if user has permission to view this task
        if current_user and task_execution.user_id:
            if task_execution.user_id != current_user.id and not self._is_admin(current_user):
                raise PermissionError("Not authorized to view this task")
        
        return self._to_response(task_execution)
    
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
        
        # Convert to response objects with executor progress
        task_responses = []
        for task in tasks:
            task_responses.append(self._to_response(task))
        
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
        
        cancel_result: dict[str, Any] = {}
        extra = task_execution.extra_data or {}
        execution_name = extra.get("cloud_run_execution")
        operation_name = extra.get("cloud_run_operation")
        if execution_name or operation_name:
            settings = get_settings()
            client = CloudRunJobClient(
                project_id=settings.google_cloud_project or "",
                region=settings.google_cloud_location or "",
                job_name=settings.cloud_run_background_job or "",
            )
            if not execution_name and operation_name:
                execution_name = client.execution_from_operation(operation_name)
                if execution_name:
                    extra = dict(extra)
                    extra["cloud_run_execution"] = execution_name
                    task_execution.extra_data = extra
                    self.db.commit()
            if not execution_name:
                raise RuntimeError("Cloud Run execution name is not available yet")
            cancel_result = client.cancel_execution(execution_name)
        
        # Update database
        self.repo.cancel_task(task_id)
        self._mark_related_job_cancelled(task_execution)
        
        return {
            "message": "Task cancelled successfully",
            "task_id": task_id,
            "cloud_run_cancel": cancel_result or None,
        }
    
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
            task_responses.append(self._to_response(task))
        
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

    def _to_response(self, task: TaskExecution) -> TaskExecutionResponse:
        progress_data = {}
        if isinstance(task.extra_data, dict):
            progress_data = task.extra_data.get("progress") or {}
        progress_value = progress_data.get("current", progress_data.get("progress"))
        try:
            progress = int(progress_value) if progress_value is not None else None
        except (TypeError, ValueError):
            progress = None
        message = progress_data.get("status") or progress_data.get("message")
        executor_state = progress_data.get("state") or task.status.value.upper()

        return TaskExecutionResponse(
            id=task.id,
            name=task.name,
            kind=task.kind,
            status=task.status,
            job_id=task.job_id,
            user_id=task.user_id,
            args=task.args,
            kwargs=task.kwargs,
            result=task.result,
            attempts=task.attempts,
            max_retries=task.max_retries,
            last_error=task.last_error,
            created_at=task.created_at,
            updated_at=task.updated_at,
            start_time=task.start_time,
            end_time=task.end_time,
            duration=task.duration,
            queue_duration=task.queue_duration,
            progress=progress,
            message=message,
            celery_state=executor_state,
            celery_info=progress_data or None,
        )

    def _mark_related_job_cancelled(self, task: TaskExecution) -> None:
        if not task.job_id:
            return
        from ..translation.repository import SqlAlchemyTranslationJobRepository

        repo = SqlAlchemyTranslationJobRepository(self.db)
        repo.set_status(task.job_id, "FAILED", error="Cancelled by user")
        if task.kind == TaskKind.VALIDATION:
            repo.update_validation_status(task.job_id, "FAILED")
        elif task.kind == TaskKind.POST_EDIT:
            repo.update_post_edit_status(task.job_id, "FAILED")
        elif task.kind == TaskKind.ILLUSTRATION:
            repo.update_illustration_status(task.job_id, "FAILED")
        self.db.commit()
