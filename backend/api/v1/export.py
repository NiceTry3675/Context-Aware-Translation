"""Export API endpoints - thin router layer."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.dependencies import get_db, get_required_user
from backend.domains.user.models import User
from backend.domains.export.service import ExportDomainService

router = APIRouter(prefix="/export", tags=["export"])


def get_export_service(db: Session = Depends(get_db)) -> ExportDomainService:
    """Dependency injection for ExportDomainService."""
    return ExportDomainService(lambda: db)


@router.get("/jobs/{job_id}/download")
async def download_job_output(
    job_id: int,
    user: User = Depends(get_required_user),
    service: ExportDomainService = Depends(get_export_service)
) -> FileResponse:
    """
    Download the output of a translation job.
    
    Args:
        job_id: Job ID
        user: Current authenticated user
        service: Export domain service
        
    Returns:
        FileResponse with the translated file
    """
    return await service.download_job_output(user, job_id)


@router.get("/jobs/{job_id}/pdf")
async def export_to_pdf(
    job_id: int,
    user: User = Depends(get_required_user),
    service: ExportDomainService = Depends(get_export_service)
) -> FileResponse:
    """
    Export translation job to PDF format.
    
    Args:
        job_id: Job ID
        user: Current authenticated user
        service: Export domain service
        
    Returns:
        FileResponse with the PDF file
    """
    return await service.export_to_pdf(user, job_id)


@router.get("/jobs/{job_id}/logs")
async def download_job_log(
    job_id: int,
    log_type: str = Query(..., regex="^(prompts|context)$"),
    user: User = Depends(get_required_user),
    service: ExportDomainService = Depends(get_export_service)
) -> FileResponse:
    """
    Download log files for a translation job.
    
    Args:
        job_id: Job ID
        log_type: Type of log ('prompts' or 'context')
        user: Current authenticated user
        service: Export domain service
        
    Returns:
        FileResponse with the log file
    """
    return await service.download_job_log(user, job_id, log_type)