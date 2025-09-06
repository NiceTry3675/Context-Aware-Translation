"""File download and content retrieval API endpoints - thin router layer."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...dependencies import get_db, get_required_user
from ...domains.user.models import User
from ...domains.export.routes import ExportRoutes

router = APIRouter(tags=["downloads"])


@router.get("/download/{job_id}")
async def download_job_output_legacy(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user)
):
    """Legacy download endpoint for backward compatibility."""
    return await ExportRoutes.download_job_output(db, current_user, job_id)


@router.get("/jobs/{job_id}/output")
async def download_job_output(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user)
):
    """Download the output of a translation job."""
    return await ExportRoutes.download_job_output(db, current_user, job_id)


@router.get("/jobs/{job_id}/logs/{log_type}")
async def download_job_log(
    job_id: int,
    log_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user)
):
    """Download log files for a translation job."""
    return await ExportRoutes.download_job_log(db, current_user, job_id, log_type)


@router.get("/jobs/{job_id}/glossary", response_model=None)
async def get_job_glossary(
    job_id: int,
    structured: bool = False,  # Optional parameter to return structured response
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user)
):
    """Get the final glossary for a completed translation job."""
    return await ExportRoutes.get_job_glossary(db, current_user, job_id, structured)


@router.get("/jobs/{job_id}/segments")
async def get_job_segments(
    job_id: int,
    offset: int = Query(0, ge=0, description="Starting segment index"),
    limit: int = Query(3, ge=1, le=200, description="Number of segments to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user)
):
    """Get the segmented translation data for a completed translation job with pagination support."""
    return await ExportRoutes.get_job_segments(db, current_user, job_id, offset, limit)


@router.get("/jobs/{job_id}/content")
async def get_job_content(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user)
):
    """Get the translated content as text for a completed translation job."""
    return await ExportRoutes.get_job_content(db, current_user, job_id)


@router.get("/jobs/{job_id}/pdf")
async def download_job_pdf(
    job_id: int,
    include_source: bool = Query(True, description="Include source text in PDF"),
    include_illustrations: bool = Query(True, description="Include illustrations in PDF"),
    page_size: str = Query("A4", description="Page size (A4 or Letter)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user)
):
    """Download the translation as a PDF document with optional illustrations."""
    return await ExportRoutes.download_job_pdf(
        db, current_user, job_id, include_source, include_illustrations, page_size
    )