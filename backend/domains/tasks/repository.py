"""Repository for task execution data access."""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta

from .models import TaskExecution, TaskStatus, TaskKind
from ..user.models import User


class TaskRepository:
    """Repository for accessing task execution data."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, task_id: str) -> Optional[TaskExecution]:
        """Get a task execution by ID."""
        return self.db.query(TaskExecution).filter_by(id=task_id).first()
    
    def create(self, task_execution: TaskExecution) -> TaskExecution:
        """Create a new task execution record."""
        self.db.add(task_execution)
        self.db.commit()
        self.db.refresh(task_execution)
        return task_execution
    
    def update(self, task_id: str, **kwargs) -> Optional[TaskExecution]:
        """Update task execution fields."""
        task = self.get_by_id(task_id)
        if task:
            for key, value in kwargs.items():
                setattr(task, key, value)
            self.db.commit()
            self.db.refresh(task)
        return task
    
    def list_tasks(
        self,
        kind: Optional[TaskKind] = None,
        status: Optional[TaskStatus] = None,
        job_id: Optional[int] = None,
        user_id: Optional[int] = None,
        limit: int = 20,
        offset: int = 0
    ) -> tuple[List[TaskExecution], int]:
        """List tasks with optional filters."""
        query = self.db.query(TaskExecution)
        
        # Apply filters
        if kind:
            query = query.filter(TaskExecution.kind == kind)
        if status:
            query = query.filter(TaskExecution.status == status)
        if job_id:
            query = query.filter(TaskExecution.job_id == job_id)
        if user_id:
            query = query.filter(TaskExecution.user_id == user_id)
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        tasks = query.order_by(TaskExecution.created_at.desc()).offset(offset).limit(limit).all()
        
        return tasks, total
    
    def get_job_tasks(self, job_id: int) -> List[TaskExecution]:
        """Get all tasks for a specific job."""
        return self.db.query(TaskExecution).filter(
            TaskExecution.job_id == job_id
        ).order_by(TaskExecution.created_at.desc()).all()
    
    def cancel_task(self, task_id: str) -> Optional[TaskExecution]:
        """Mark a task as cancelled/revoked."""
        return self.update(
            task_id,
            status=TaskStatus.REVOKED,
            end_time=datetime.utcnow(),
            last_error="Task cancelled by user"
        )
    
    def get_stats(self, hours: int = 24) -> dict:
        """Get task execution statistics for the specified time period."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Get task counts by status
        status_counts = {}
        for status in TaskStatus:
            count = self.db.query(TaskExecution).filter(
                and_(
                    TaskExecution.created_at >= cutoff_time,
                    TaskExecution.status == status
                )
            ).count()
            status_counts[status.value] = count
        
        # Get task counts by kind
        kind_counts = {}
        for kind in TaskKind:
            count = self.db.query(TaskExecution).filter(
                and_(
                    TaskExecution.created_at >= cutoff_time,
                    TaskExecution.kind == kind
                )
            ).count()
            kind_counts[kind.value] = count
        
        # Get average duration by kind
        avg_durations = {}
        for kind in TaskKind:
            tasks = self.db.query(TaskExecution).filter(
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
    
    def get_recent_failures(self, limit: int = 10) -> List[TaskExecution]:
        """Get recent failed tasks."""
        return self.db.query(TaskExecution).filter(
            TaskExecution.status == TaskStatus.FAILURE
        ).order_by(TaskExecution.created_at.desc()).limit(limit).all()
    
    def cleanup_old_tasks(self, days: int = 30) -> int:
        """Delete task executions older than specified days."""
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        count = self.db.query(TaskExecution).filter(
            TaskExecution.created_at < cutoff_time
        ).delete()
        self.db.commit()
        return count