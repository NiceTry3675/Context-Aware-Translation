"""
Post-edit domain routes - thin routing layer.

This module provides a thin routing layer for post-editing operations,
delegating all business logic to the PostEditDomainService.
"""

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
import json
import os

from backend.config.dependencies import get_db, get_required_user
from backend.domains.user.models import User
from backend.domains.post_edit.schemas import PostEditRequest
from backend.domains.post_edit.service import PostEditDomainService
from backend.celery_tasks.post_edit import process_post_edit_task
from backend.domains.translation.repository import SqlAlchemyTranslationJobRepository


def get_post_edit_service(db: Session = Depends(get_db)) -> PostEditDomainService:
    """Dependency injection for PostEditDomainService."""
    return PostEditDomainService(lambda: db)


async def post_edit_job(
    job_id: int,
    request: PostEditRequest,
    user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    """
    Trigger post-editing on a validated translation job.
    
    Args:
        job_id: Job ID
        request: Post-edit request parameters
        user: Current authenticated user
        service: Post-edit domain service
        
    Returns:
        Task information for the post-edit job
    """
    # Verify the job exists and belongs to the user
    repo = SqlAlchemyTranslationJobRepository(db)
    job = repo.get(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    if job.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this job")
    
    # Update post-edit status to IN_PROGRESS immediately
    repo.update_post_edit_status(
        job_id,
        "IN_PROGRESS",
        progress=0
    )
    db.commit()
    
    # Launch the post-edit task
    task = process_post_edit_task.delay(
        job_id=job_id,
        api_key=request.api_key,
        model_name=request.model_name or "gemini-2.0-flash-exp",
        selected_cases=request.selected_cases,
        modified_cases=request.modified_cases,
        user_id=user.id
    )
    
    return {
        "task_id": task.id,
        "job_id": job_id,
        "status": "queued"
    }


async def get_post_edit_status(
    job_id: int,
    user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    """
    Get the post-edit report for a job.
    
    Args:
        job_id: Job ID
        user: Current authenticated user
        service: Post-edit domain service
        
    Returns:
        Post-edit report with changes and statistics
    """
    # Verify the job exists and belongs to the user
    repo = SqlAlchemyTranslationJobRepository(db)
    job = repo.get(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    if job.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this job")
    
    # Check if post-edit report exists
    if not job.post_edit_log_path:
        return {
            "job_id": job_id,
            "status": "not_post_edited",
            "message": "No post-edit report available for this job"
        }
    
    # Load the post-edit report
    if os.path.exists(job.post_edit_log_path):
        with open(job.post_edit_log_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
        return report
    else:
        raise HTTPException(
            status_code=404, 
            detail=f"Post-edit report file not found at {job.post_edit_log_path}"
        )
