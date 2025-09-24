"""Export domain routes - plain async functions for business logic."""

from typing import Dict, Any
from fastapi import Depends, Body, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from backend.config.dependencies import get_db, get_required_user
from backend.domains.user.models import User
from .service import ExportDomainService


async def download_file(
    job_id: int,
    user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
) -> FileResponse:
    """
    Download the output of a translation job.
    
    Args:
        job_id: Job ID
        user: Current authenticated user (from dependency)
        db: Database session (from dependency)
        
    Returns:
        FileResponse with the translated file
    """
    service = ExportDomainService(db)
    file_path, filename, media_type = await service.download_job_output(user, job_id)
    return FileResponse(path=file_path, filename=filename, media_type=media_type)


async def export_job(
    job_id: int,
    format: str = "pdf",
    include_source: bool = True,
    include_illustrations: bool = True,
    page_size: str = "A4",
    user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
) -> Response:
    """
    Export translation job in different formats.
    
    Args:
        job_id: Job ID
        format: Export format (pdf, etc.)
        include_source: Whether to include source text
        include_illustrations: Whether to include illustrations
        page_size: Page size format
        user: Current authenticated user (from dependency)
        db: Database session (from dependency)
        
    Returns:
        Response with exported file
    """
    service = ExportDomainService(db)
    
    if format == "pdf":
        from .schemas import PDFExportRequest
        
        # Create PDF request
        request = PDFExportRequest(
            job_id=job_id,
            include_source=include_source,
            include_illustrations=include_illustrations,
            page_size=page_size
        )
        
        # Generate PDF
        pdf_bytes = await service.generate_pdf(user, request)
        pdf_filename = service.get_pdf_filename(job_id)
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{pdf_filename}"'
            }
        )
    else:
        # Default to regular file download
        file_path, filename, media_type = await service.download_job_output(user, job_id)
        return FileResponse(path=file_path, filename=filename, media_type=media_type)


async def download_pdf(
    job_id: int,
    include_source: bool = Query(True),
    include_illustrations: bool = Query(True),
    page_size: str = Query("A4"),
    user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
) -> Response:
    """Download translation as PDF using query parameters."""
    service = ExportDomainService(db)

    from .schemas import PDFExportRequest

    request = PDFExportRequest(
        job_id=job_id,
        include_source=include_source,
        include_illustrations=include_illustrations,
        page_size=page_size,
    )

    pdf_bytes = await service.generate_pdf(user, request)
    pdf_filename = service.get_pdf_filename(job_id)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{pdf_filename}"'
        }
    )


async def download_glossary(
    job_id: int,
    structured: bool = Query(False),
    user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
) -> Response:
    """
    Download glossary for a translation job.
    If structured=true, returns structured glossary JSON payload.
    Otherwise returns raw dictionary JSON.
    """
    service = ExportDomainService(db)
    glossary = await service.get_job_glossary(user, job_id, structured=structured)
    filename = service.get_glossary_filename(job_id)
    import json
    return Response(
        content=json.dumps(glossary, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


async def upload_glossary(
    job_id: int,
    glossary: dict = Body(..., embed=False),
    mode: str = Query("merge"),
    structured: bool = Query(True),
    user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
) -> Response:
    """
    Upload and apply glossary to a job (merge or replace).
    Accepts flexible formats: dict, array of {source,korean}, array of {term,translation}, etc.
    """
    import json
    service = ExportDomainService(db)
    payload = json.dumps(glossary, ensure_ascii=False)
    updated = await service.update_job_glossary(
        user=user,
        job_id=job_id,
        glossary_json=payload,
        mode=mode,
        structured=structured,
    )
    return Response(
        content=json.dumps(updated, ensure_ascii=False, indent=2),
        media_type="application/json",
    )
