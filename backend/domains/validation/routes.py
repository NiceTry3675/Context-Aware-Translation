"""
Validation domain routes - thin routing layer.

This module provides a thin routing layer for validation operations,
delegating all business logic to the ValidationDomainService.
"""

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
import json
import os
import uuid

from backend.config.dependencies import get_db, get_required_user
from backend.domains.user.models import User
from backend.domains.validation.schemas import ValidationRequest
from backend.domains.validation.service import ValidationDomainService
from backend.celery_tasks.validation import process_validation_task
from backend.domains.translation.repository import SqlAlchemyTranslationJobRepository
from backend.domains.tasks.models import TaskKind
from backend.domains.tasks.repository import TaskRepository
from backend.celery_app import celery_app
from celery.result import AsyncResult
from backend.celery_tasks.base import create_task_execution


def get_validation_service(db: Session = Depends(get_db)) -> ValidationDomainService:
    """Dependency injection for ValidationDomainService."""
    return ValidationDomainService(lambda: db)


async def validate_job(
    job_id: int,
    request: ValidationRequest,
    user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    """
    Trigger validation on a completed translation job.
    
    Args:
        job_id: Job ID
        request: Validation request parameters
        user: Current authenticated user
        db: Database session
        
    Returns:
        Task information for the validation job
    """
    # Verify the job exists and belongs to the user
    repo = SqlAlchemyTranslationJobRepository(db)
    job = repo.get(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    if job.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this job")
    
    # If a validation is already marked as in progress, check for an active task.
    if job.validation_status == "IN_PROGRESS":
        task_repo = TaskRepository(db)
        tasks = task_repo.get_job_tasks(job_id)
        # Find the most recent validation task for this job
        recent_validation_task = next((t for t in tasks if t.kind == TaskKind.VALIDATION), None)

        if recent_validation_task:
            celery_state = AsyncResult(recent_validation_task.id, app=celery_app).state
            if celery_state in ("PENDING", "STARTED", "RETRY"):
                # Already running; avoid duplicate
                raise HTTPException(status_code=409, detail="Validation is already in progress for this job")
        # No active task found; fall through and re-queue a new one

    # Update validation status to IN_PROGRESS immediately (idempotent)
    repo.update_validation_status(
        job_id,
        "IN_PROGRESS",
        progress=0
    )
    db.commit()

    # Launch the validation task with a pre-created tracking record and explicit task_id
    validation_mode = "quick" if request.quick_validation else "comprehensive"
    task_id = str(uuid.uuid4())
    create_task_execution(
        task_id=task_id,
        task_name=process_validation_task.name,
        task_kind=TaskKind.VALIDATION,
        job_id=job_id,
        user_id=user.id,
        args=[],
        kwargs={
            "job_id": job_id,
            "api_key": request.api_key,
            "model_name": request.model_name or "gemini-2.0-flash-exp",
            "validation_mode": validation_mode,
            "sample_rate": request.validation_sample_rate,
            "user_id": user.id,
            "autotrigger_post_edit": False,
        },
    )

    process_validation_task.apply_async(
        kwargs={
            "job_id": job_id,
            "api_key": request.api_key,
            "model_name": request.model_name or "gemini-2.0-flash-exp",
            "validation_mode": validation_mode,
            "sample_rate": request.validation_sample_rate,
            "user_id": user.id,
            "autotrigger_post_edit": False,
        },
        task_id=task_id,
    )

    return {
        "task_id": task_id,
        "job_id": job_id,
        "status": "queued"
    }


async def get_validation_status(
    job_id: int,
    structured: bool = False,
    user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    """
    Get the validation report for a job.
    
    Args:
        job_id: Job ID
        structured: Whether to return structured response
        user: Current authenticated user
        db: Database session
        
    Returns:
        Validation report (structured or plain)
    """
    # Verify the job exists and belongs to the user
    repo = SqlAlchemyTranslationJobRepository(db)
    job = repo.get(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    if job.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this job")
    
    # Check if validation report exists
    if not job.validation_report_path:
        return {
            "job_id": job_id,
            "status": "not_validated",
            "message": "No validation report available for this job"
        }
    
    # Load the validation report
    if os.path.exists(job.validation_report_path):
        with open(job.validation_report_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        # Log report structure for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[VALIDATION ROUTE] Loaded report for job {job_id}: keys={list(report.keys())}, "
                   f"summary_keys={list(report.get('summary', {}).keys()) if 'summary' in report else 'N/A'}, "
                   f"detailed_results_count={len(report.get('detailed_results', []))}")
        
        if structured:
            # Return structured report
            from backend.domains.validation.schemas import StructuredValidationReport
            from core.schemas import ValidationResponse
            
            # Convert to structured format if available
            validation_response = None
            if 'validation_response' in report:
                validation_response = ValidationResponse(**report['validation_response'])
            
            return StructuredValidationReport(
                summary=report.get('summary', {}),
                detailed_results=report.get('detailed_results', []),
                validation_response=validation_response
            )
        else:
            # Return raw report
            return report
    else:
        raise HTTPException(
            status_code=404, 
            detail=f"Validation report file not found at {job.validation_report_path}"
        )
