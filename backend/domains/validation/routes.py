"""
Validation domain routes - thin routing layer.

This module provides a thin routing layer for validation operations,
delegating all business logic to the ValidationDomainService.
"""

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.dependencies import get_db, get_required_user
from backend.domains.user.models import User
from backend.domains.validation.schemas import ValidationRequest
from backend.domains.validation.service import ValidationDomainService


def get_validation_service(db: Session = Depends(get_db)) -> ValidationDomainService:
    """Dependency injection for ValidationDomainService."""
    return ValidationDomainService(lambda: db)


async def validate_job(
    job_id: int,
    request: ValidationRequest,
    user: User = Depends(get_required_user),
    service: ValidationDomainService = Depends(get_validation_service)
):
    """
    Trigger validation on a completed translation job.
    
    Args:
        job_id: Job ID
        request: Validation request parameters
        user: Current authenticated user
        service: Validation domain service
        
    Returns:
        Task information for the validation job
    """
    return await service.trigger_validation(user, job_id, request)


async def get_validation_status(
    job_id: int,
    structured: bool = False,
    user: User = Depends(get_required_user),
    service: ValidationDomainService = Depends(get_validation_service)
):
    """
    Get the validation report for a job.
    
    Args:
        job_id: Job ID
        structured: Whether to return structured response
        user: Current authenticated user
        service: Validation domain service
        
    Returns:
        Validation report (structured or plain)
    """
    return await service.get_validation_report(user, job_id, structured)