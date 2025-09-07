"""
Translation domain routes - thin routing layer.

This module provides a thin routing layer for translation operations,
delegating all business logic to the TranslationDomainService.
"""

from typing import List, Optional
from fastapi import Depends, HTTPException, UploadFile, File, Form, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.config.dependencies import get_db, get_required_user, is_admin
from backend.domains.user.models import User
from backend.domains.translation.models import TranslationJob as TranslationJobModel
from backend.domains.translation.schemas import TranslationJob
from backend.domains.translation.service import TranslationDomainService


def get_translation_service(db: Session = Depends(get_db)) -> TranslationDomainService:
    """Dependency injection for TranslationDomainService."""
    return TranslationDomainService(lambda: db)


async def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user: User = Depends(get_required_user),
    service: TranslationDomainService = Depends(get_translation_service)
) -> List[TranslationJob]:
    """
    List all translation jobs for the current user.
    
    Args:
        skip: Number of jobs to skip for pagination
        limit: Maximum number of jobs to return
        user: Current authenticated user
        service: Translation domain service
        
    Returns:
        List of translation jobs
    """
    return service.list_jobs(user.id, skip=skip, limit=limit)


def create_job(
    file: UploadFile = File(...),
    api_key: str = Form(...),
    model_name: str = Form("gemini-2.5-flash-lite"),
    translation_model_name: Optional[str] = Form(None),
    style_model_name: Optional[str] = Form(None),
    glossary_model_name: Optional[str] = Form(None),
    style_data: Optional[str] = Form(None),
    glossary_data: Optional[str] = Form(None),
    segment_size: int = Form(15000),
    user: User = Depends(get_required_user),
    service: TranslationDomainService = Depends(get_translation_service)
) -> TranslationJob:
    """
    Create a new translation job.
    
    Args:
        file: File to translate
        api_key: API key for translation service
        model_name: Default model name
        translation_model_name: Optional override for translation model
        style_model_name: Optional override for style model
        glossary_model_name: Optional override for glossary model
        style_data: Optional style data
        glossary_data: Optional glossary data
        segment_size: Segment size for translation
        user: Current authenticated user
        service: Translation domain service
        
    Returns:
        Created translation job
    """
    return service.create_job(
        user=user,
        file=file,
        api_key=api_key,
        model_name=model_name,
        translation_model_name=translation_model_name,
        style_model_name=style_model_name,
        glossary_model_name=glossary_model_name,
        style_data=style_data,
        glossary_data=glossary_data,
        segment_size=segment_size
    )


async def get_job(
    job_id: int,
    service: TranslationDomainService = Depends(get_translation_service)
) -> TranslationJob:
    """
    Get a translation job by ID.
    
    Args:
        job_id: Job ID
        service: Translation domain service
        
    Returns:
        Translation job
    """
    return service.get_job(job_id)


async def delete_job(
    job_id: int,
    user: User = Depends(get_required_user),
    service: TranslationDomainService = Depends(get_translation_service)
) -> Response:
    """
    Delete a translation job.
    
    Args:
        job_id: Job ID to delete
        user: Current authenticated user
        service: Translation domain service
        
    Returns:
        204 No Content response
    """
    user_is_admin = await is_admin(user)
    service.delete_job(user, job_id, is_admin=user_is_admin)
    return Response(status_code=204)


async def download_job_output(
    job_id: int,
    user: User = Depends(get_required_user),
    service: TranslationDomainService = Depends(get_translation_service)
) -> FileResponse:
    """
    Download the output of a translation job.
    
    Args:
        job_id: Job ID
        user: Current authenticated user
        service: Translation domain service
        
    Returns:
        FileResponse with the translated file
    """
    user_is_admin = await is_admin(user)
    return service.download_job_output(user, job_id, is_admin=user_is_admin)


async def download_job_log(
    job_id: int,
    log_type: str = Query(..., regex="^(prompts|context)$"),
    user: User = Depends(get_required_user),
    service: TranslationDomainService = Depends(get_translation_service)
) -> FileResponse:
    """
    Download log files for a translation job.
    
    Args:
        job_id: Job ID
        log_type: Type of log ('prompts' or 'context')
        user: Current authenticated user
        service: Translation domain service
        
    Returns:
        FileResponse with the log file
    """
    user_is_admin = await is_admin(user)
    return service.download_job_log(user, job_id, log_type, is_admin=user_is_admin)


async def get_job_content(
    job_id: int,
    service: TranslationDomainService = Depends(get_translation_service)
) -> dict:
    """
    Get the complete content of a translation job.
    
    Args:
        job_id: Job ID
        service: Translation domain service
        
    Returns:
        Dict containing the job content and segments
    """
    return service.get_job_content(job_id)


async def get_job_segments(
    job_id: int,
    offset: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    service: TranslationDomainService = Depends(get_translation_service)
) -> dict:
    """
    Get segments from a translation job with pagination.
    
    Args:
        job_id: Job ID
        offset: Number of segments to skip
        limit: Maximum number of segments to return
        service: Translation domain service
        
    Returns:
        Dict containing paginated segments
    """
    return service.get_job_segments(job_id, offset=offset, limit=limit)