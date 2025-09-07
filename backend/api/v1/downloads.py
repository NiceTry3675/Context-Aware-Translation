"""File download and content retrieval API endpoints - thin router layer."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.dependencies import get_db, get_required_user, is_admin
from backend.domains.user.models import User
from backend.domains.export.service import ExportDomainService

router = APIRouter(tags=["downloads"])


def get_export_service(db: Session = Depends(get_db)) -> ExportDomainService:
    """Dependency injection for ExportDomainService."""
    return ExportDomainService(lambda: db)


@router.get("/download/{job_id}")
async def download_job_output_legacy(
    job_id: int,
    current_user: User = Depends(get_required_user),
    service: ExportDomainService = Depends(get_export_service)
):
    """Legacy download endpoint for backward compatibility."""
    user_is_admin = await is_admin(current_user)
    return await service.download_job_output(current_user, job_id, is_admin=user_is_admin)


@router.get("/jobs/{job_id}/output")
async def download_job_output(
    job_id: int,
    current_user: User = Depends(get_required_user),
    service: ExportDomainService = Depends(get_export_service)
):
    """Download the output of a translation job."""
    user_is_admin = await is_admin(current_user)
    return await service.download_job_output(current_user, job_id, is_admin=user_is_admin)


@router.get("/jobs/{job_id}/logs/{log_type}")
async def download_job_log(
    job_id: int,
    log_type: str,
    current_user: User = Depends(get_required_user),
    service: ExportDomainService = Depends(get_export_service)
):
    """Download log files for a translation job."""
    user_is_admin = await is_admin(current_user)
    return await service.download_job_log(current_user, job_id, log_type, is_admin=user_is_admin)


@router.get("/jobs/{job_id}/glossary", response_model=None)
async def get_job_glossary(
    job_id: int,
    structured: bool = False,
    current_user: User = Depends(get_required_user),
    service: ExportDomainService = Depends(get_export_service)
):
    """Get the final glossary for a completed translation job."""
    return await service.get_job_glossary(current_user, job_id, structured)


@router.get("/jobs/{job_id}/segments")
async def get_job_segments(
    job_id: int,
    offset: int = Query(0, ge=0, description="Starting segment index"),
    limit: int = Query(3, ge=1, le=200, description="Number of segments to return"),
    current_user: User = Depends(get_required_user),
    service: ExportDomainService = Depends(get_export_service)
):
    """Get the segmented translation data for a completed translation job with pagination support."""
    return await service.get_job_segments(current_user, job_id, offset, limit)


@router.get("/jobs/{job_id}/content")
async def get_job_content(
    job_id: int,
    current_user: User = Depends(get_required_user),
    service: ExportDomainService = Depends(get_export_service)
):
    """Get the translated content as text for a completed translation job."""
    return await service.get_job_content(current_user, job_id)


@router.get("/jobs/{job_id}/pdf")
async def download_job_pdf(
    job_id: int,
    include_source: bool = Query(True, description="Include source text in PDF"),
    include_illustrations: bool = Query(True, description="Include illustrations in PDF"),
    page_size: str = Query("A4", description="Page size (A4 or Letter)"),
    current_user: User = Depends(get_required_user),
    service: ExportDomainService = Depends(get_export_service)
):
    """Download the translation as a PDF document with optional illustrations."""
    return await service.download_job_pdf(
        current_user, job_id, include_source, include_illustrations, page_size
    )