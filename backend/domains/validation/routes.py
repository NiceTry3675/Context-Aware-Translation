"""
Validation domain routes - thin routing layer.

This module provides a thin routing layer for validation operations,
delegating all business logic to the ValidationDomainService.
"""

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
import json
import os

from backend.config.dependencies import get_db, get_required_user
from backend.domains.user.models import User
from backend.domains.validation.schemas import ValidationRequest
from backend.domains.validation.service import ValidationDomainService
from backend.celery_tasks.validation import process_validation_task
from backend.domains.translation.repository import SqlAlchemyTranslationJobRepository


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
    
    # Update validation status to IN_PROGRESS immediately
    repo.update_validation_status(
        job_id,
        "IN_PROGRESS",
        progress=0
    )
    db.commit()
    
    # Launch the validation task
    validation_mode = "quick" if request.quick_validation else "comprehensive"
    task = process_validation_task.delay(
        job_id=job_id,
        api_key=request.api_key,
        model_name=request.model_name or "gemini-2.0-flash-exp",
        validation_mode=validation_mode,
        sample_rate=request.validation_sample_rate,
        user_id=user.id,
        autotrigger_post_edit=False
    )
    
    return {
        "task_id": task.id,
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
