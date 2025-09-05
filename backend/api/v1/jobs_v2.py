"""
Example API routes using the new repository pattern and Unit of Work.

This module demonstrates how to integrate the new domain-driven architecture
with FastAPI endpoints.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import hashlib

from backend.database import SessionLocal
from backend.auth import get_current_user_optional
from backend.domains.translation.service import TranslationDomainService
from backend.schemas import (
    TranslationJobResponse,
    TranslationJobCreate,
    PaginatedJobsResponse
)

router = APIRouter(prefix="/api/v2/jobs", tags=["jobs-v2"])


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_translation_service():
    """Dependency to get translation service."""
    return TranslationDomainService(SessionLocal)


@router.post("/", response_model=TranslationJobResponse)
async def create_translation_job(
    file: UploadFile = File(...),
    api_key: str = None,
    segment_size: int = 15000,
    enable_validation: bool = False,
    enable_post_edit: bool = False,
    enable_illustrations: bool = False,
    idempotency_key: Optional[str] = None,
    current_user: dict = Depends(get_current_user_optional),
    service: TranslationDomainService = Depends(get_translation_service)
):
    """
    Create a new translation job using the repository pattern.
    
    This endpoint demonstrates:
    - Idempotent job creation
    - Domain event publishing
    - Unit of Work transaction management
    """
    # Verify user is authenticated
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Generate idempotency key from file if not provided
    if not idempotency_key:
        file_content = await file.read()
        await file.seek(0)  # Reset file pointer
        file_hash = hashlib.md5(file_content).hexdigest()
        idempotency_key = f"{current_user['id']}:{file.filename}:{file_hash}"
    
    try:
        # Create job using the service
        job_with_id = service.create_translation_job(
            filename=file.filename,
            owner_id=current_user['id'],
            idempotency_key=idempotency_key,
            segment_size=segment_size,
            validation_enabled=enable_validation,
            post_edit_enabled=enable_post_edit,
            illustrations_enabled=enable_illustrations
        )
        
        # Fetch the complete job using the ID
        from backend.domains.translation import SqlAlchemyTranslationJobRepository
        db = SessionLocal()
        try:
            repo = SqlAlchemyTranslationJobRepository(db)
            job = repo.get(job_with_id.id)
        finally:
            db.close()
        
        # TODO: Add background task to process the translation
        # background_tasks.add_task(process_translation_task, job.id, file)
        
        return TranslationJobResponse.from_orm(job)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=PaginatedJobsResponse)
async def list_user_jobs(
    limit: int = 20,
    cursor: Optional[int] = None,
    current_user: dict = Depends(get_current_user_optional),
    service: TranslationDomainService = Depends(get_translation_service)
):
    """
    List translation jobs for the current user with cursor-based pagination.
    
    This endpoint demonstrates:
    - Repository-based data access
    - Cursor-based pagination
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        jobs = service.get_user_jobs(
            user_id=current_user['id'],
            limit=limit,
            cursor=cursor
        )
        
        # Get next cursor from last job if we got full page
        next_cursor = None
        if len(jobs) == limit and jobs:
            next_cursor = jobs[-1].id
        
        return PaginatedJobsResponse(
            jobs=[TranslationJobResponse.from_orm(job) for job in jobs],
            next_cursor=next_cursor,
            has_more=len(jobs) == limit
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{job_id}/progress")
async def update_job_progress(
    job_id: int,
    progress: int,
    current_user: dict = Depends(get_current_user_optional),
    service: TranslationDomainService = Depends(get_translation_service)
):
    """
    Update the progress of a translation job.
    
    This endpoint is typically called by background workers.
    """
    # In production, this would be protected by service-to-service auth
    try:
        success = service.update_progress(job_id, progress)
        if not success:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {"status": "success", "progress": progress}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/complete")
async def complete_translation_job(
    job_id: int,
    duration_seconds: int,
    translation_data: Optional[dict] = None,
    service: TranslationDomainService = Depends(get_translation_service)
):
    """
    Mark a translation job as completed.
    
    This endpoint is typically called by background workers.
    """
    # In production, this would be protected by service-to-service auth
    try:
        success = service.complete_translation(
            job_id=job_id,
            duration_seconds=duration_seconds,
            translation_segments=translation_data
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {"status": "success", "message": "Job completed"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/fail")
async def fail_translation_job(
    job_id: int,
    error_message: str,
    service: TranslationDomainService = Depends(get_translation_service)
):
    """
    Mark a translation job as failed.
    
    This endpoint is typically called by background workers when an error occurs.
    """
    # In production, this would be protected by service-to-service auth
    try:
        success = service.fail_translation(
            job_id=job_id,
            error_message=error_message
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {"status": "success", "message": "Job marked as failed"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/validate")
async def start_validation(
    job_id: int,
    sample_rate: int = 100,
    quick_validation: bool = False,
    current_user: dict = Depends(get_current_user_optional),
    service: TranslationDomainService = Depends(get_translation_service)
):
    """
    Start validation for a completed translation job.
    
    This endpoint demonstrates how validation integrates with the repository pattern.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        success = service.start_validation(
            job_id=job_id,
            sample_rate=sample_rate,
            quick_validation=quick_validation
        )
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Job not found or not completed"
            )
        
        # TODO: Add background task to process validation
        # background_tasks.add_task(process_validation_task, job_id)
        
        return {"status": "success", "message": "Validation started"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))