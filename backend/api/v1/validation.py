"""Validation API endpoints - thin router layer."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.dependencies import get_db, get_required_user
from backend.domains.user.models import User
from backend.domains.validation.schemas import ValidationRequest
from backend.domains.validation.service import ValidationDomainService

router = APIRouter(prefix="/validation", tags=["validation"])


def get_validation_service(db: Session = Depends(get_db)) -> ValidationDomainService:
    """Dependency injection for ValidationDomainService."""
    return ValidationDomainService(lambda: db)


@router.put("/jobs/{job_id}/validate")
async def trigger_validation(
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


@router.get("/jobs/{job_id}/report")
async def get_validation_report(
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