"""
Post-edit domain routes - thin routing layer.

This module provides a thin routing layer for post-editing operations.
"""

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
import json
import os
import uuid

from backend.config.dependencies import get_db, get_required_user
from backend.domains.user.models import User
from backend.domains.post_edit.schemas import PostEditRequest
from backend.domains.post_edit.service import PostEditDomainService
from backend.celery_tasks.post_edit import process_post_edit_task
from backend.domains.translation.repository import SqlAlchemyTranslationJobRepository
from backend.domains.tasks.models import TaskKind
from backend.domains.tasks.repository import TaskRepository
from backend.celery_app import celery_app
from celery.result import AsyncResult
from backend.celery_tasks.base import create_task_execution
from backend.domains.shared.provider_context import provider_context_to_payload


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
    Returns:
        Task information for the post-edit job
    """
    # Verify the job exists and belongs to the user
    service = PostEditDomainService(lambda: db)
    repo = SqlAlchemyTranslationJobRepository(db)
    job = repo.get(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    if job.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this job")
    
    # If already marked IN_PROGRESS, verify if a task is actively running to avoid duplicates
    if job.post_edit_status == "IN_PROGRESS":
        task_repo = TaskRepository(db)
        tasks = task_repo.get_job_tasks(job_id)
        recent_post_edit_task = next((t for t in tasks if t.kind == TaskKind.POST_EDIT), None)
        if recent_post_edit_task:
            celery_state = AsyncResult(recent_post_edit_task.id, app=celery_app).state
            if celery_state in ("PENDING", "STARTED", "RETRY"):
                raise HTTPException(status_code=409, detail="Post-edit is already in progress for this job")
        # else fall through and re-queue

    provider_context = service.build_provider_context(
        request.api_provider or "gemini",
        request.provider_config,
    )
    # Use provider-specific default models
    fallback_model = "gemini-flash-lite-latest"
    if provider_context and provider_context.name == "vertex":
        fallback_model = "gemini-flash-latest"
    elif provider_context and provider_context.name == "openrouter":
        fallback_model = "google/gemini-2.5-flash-lite-preview-09-2025"

    model_name = (
        request.model_name
        or provider_context.default_model
        or service.config.get("default_model", fallback_model)
    )

    if not service.validate_api_key(
        request.api_key,
        model_name,
        provider_context=provider_context,
    ):
        service.raise_invalid_api_key()

    provider_payload = provider_context_to_payload(provider_context)

    # Update post-edit status to IN_PROGRESS immediately (idempotent)
    repo.update_post_edit_status(
        job_id,
        "IN_PROGRESS",
        progress=0
    )
    db.commit()

    # Launch the post-edit task with pre-created tracking record and explicit task_id
    task_id = str(uuid.uuid4())
    create_task_execution(
        task_id=task_id,
        task_name=process_post_edit_task.name,
        task_kind=TaskKind.POST_EDIT,
        job_id=job_id,
        user_id=user.id,
        args=[],
        kwargs={
            "job_id": job_id,
            "api_key": request.api_key,
            "model_name": model_name,
            "selected_cases": request.selected_cases,
            "modified_cases": request.modified_cases,
            "default_select_all": request.default_select_all,
            "user_id": user.id,
            "provider_context": provider_payload,
        },
    )

    process_post_edit_task.apply_async(
        kwargs={
            "job_id": job_id,
            "api_key": request.api_key,
            "model_name": model_name,
            "selected_cases": request.selected_cases,
            "modified_cases": request.modified_cases,
            "default_select_all": request.default_select_all,
            "user_id": user.id,
            "provider_context": provider_payload,
        },
        task_id=task_id,
    )

    return {
        "task_id": task_id,
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
