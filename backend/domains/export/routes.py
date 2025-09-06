"""
Export domain routes with business logic.

This module contains the export business logic extracted from the translation routes,
implementing the single responsibility principle for export operations.
"""

import os
import json
import logging
from typing import Dict, Any

from fastapi import HTTPException, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.domains.user.models import User
from .service import ExportDomainService
from .schemas import (
    PDFExportRequest,
    SegmentResponse,
    ContentResponse
)


class ExportRoutes:
    """Business logic for export-related operations."""
    
    @staticmethod
    async def download_job_output(
        db: Session,
        user: User,
        job_id: int
    ):
        """
        Download the output of a translation job.
        
        Args:
            db: Database session
            user: Current user
            job_id: Job ID
            
        Returns:
            FileResponse with the translated file
            
        Raises:
            HTTPException: If job not found, not authorized, or file not available
        """
        service = ExportDomainService(db)
        
        try:
            file_path, filename, media_type = await service.download_job_output(user, job_id)
            return FileResponse(path=file_path, filename=filename, media_type=media_type)
        except ValueError as e:
            if "Job not found" in str(e):
                raise HTTPException(status_code=404, detail=str(e))
            elif "Not authorized" in str(e):
                raise HTTPException(status_code=403, detail=str(e))
            else:
                raise HTTPException(status_code=400, detail=str(e))
    
    @staticmethod
    async def download_job_log(
        db: Session,
        user: User,
        job_id: int,
        log_type: str
    ):
        """
        Download log files for a translation job.
        
        Args:
            db: Database session
            user: Current user
            job_id: Job ID
            log_type: Type of log ('prompts' or 'context')
            
        Returns:
            FileResponse with the log file
            
        Raises:
            HTTPException: If job not found, not authorized, or log not available
        """
        service = ExportDomainService(db)
        
        try:
            file_path, filename = await service.download_job_log(user, job_id, log_type)
            return FileResponse(path=file_path, filename=filename, media_type="text/plain")
        except ValueError as e:
            if "Job not found" in str(e):
                raise HTTPException(status_code=404, detail=str(e))
            elif "Not authorized" in str(e):
                raise HTTPException(status_code=403, detail=str(e))
            elif "Invalid log type" in str(e):
                raise HTTPException(status_code=400, detail=str(e))
            elif "not found" in str(e):
                raise HTTPException(status_code=404, detail=str(e))
            else:
                raise HTTPException(status_code=400, detail=str(e))
    
    @staticmethod
    async def get_job_glossary(
        db: Session,
        user: User,
        job_id: int,
        structured: bool = False
    ):
        """
        Get the final glossary for a completed translation job.
        
        Args:
            db: Database session
            user: Current user
            job_id: Job ID
            structured: If True, returns a structured response
            
        Returns:
            Either raw glossary dict or structured response
            
        Raises:
            HTTPException: If job not found, not authorized, or glossary not available
        """
        service = ExportDomainService(db)
        
        try:
            return await service.get_job_glossary(user, job_id, structured)
        except ValueError as e:
            if "Job not found" in str(e):
                raise HTTPException(status_code=404, detail=str(e))
            elif "Not authorized" in str(e):
                raise HTTPException(status_code=403, detail=str(e))
            else:
                raise HTTPException(status_code=400, detail=str(e))
    
    @staticmethod
    async def get_job_segments(
        db: Session,
        user: User,
        job_id: int,
        offset: int = 0,
        limit: int = 3
    ) -> Dict[str, Any]:
        """
        Get the segmented translation data for a completed translation job.
        
        Args:
            db: Database session
            user: Current user
            job_id: Job ID
            offset: Starting segment index
            limit: Number of segments to return
            
        Returns:
            Dict with segments and pagination info (backwards compatible format)
            
        Raises:
            HTTPException: If job not found, not authorized, or segments not available
        """
        service = ExportDomainService(db)
        
        try:
            # Get structured response from service
            response = await service.get_job_segments(user, job_id, offset, limit)
            
            # Convert to backwards compatible format
            from backend.domains.translation.repository import SqlAlchemyTranslationJobRepository
            repo = SqlAlchemyTranslationJobRepository(db)
            db_job = repo.get(job_id)
            
            return {
                "job_id": job_id,
                "filename": db_job.filename,
                "segments": response.segments,
                "total_segments": response.total_count,
                "has_more": response.has_more,
                "offset": response.offset,
                "limit": response.limit,
                "completed_at": db_job.completed_at.isoformat() if db_job.completed_at else None,
                "message": "No segments available for this job." if response.total_count == 0 else None
            }
        except ValueError as e:
            if "Job not found" in str(e):
                raise HTTPException(status_code=404, detail=str(e))
            elif "Not authorized" in str(e):
                raise HTTPException(status_code=403, detail=str(e))
            else:
                raise HTTPException(status_code=400, detail=str(e))
    
    @staticmethod
    async def get_job_content(
        db: Session,
        user: User,
        job_id: int
    ) -> Dict[str, Any]:
        """
        Get the translated content as text for a completed translation job.
        
        Args:
            db: Database session
            user: Current user
            job_id: Job ID
            
        Returns:
            Dict with content and metadata
            
        Raises:
            HTTPException: If job not found, not authorized, or content not available
        """
        service = ExportDomainService(db)
        
        try:
            response = await service.get_job_content(user, job_id, include_source=True)
            return response.model_dump()
        except ValueError as e:
            if "Job not found" in str(e):
                raise HTTPException(status_code=404, detail=str(e))
            elif "Not authorized" in str(e):
                raise HTTPException(status_code=403, detail=str(e))
            elif "not found" in str(e):
                raise HTTPException(status_code=404, detail=str(e))
            else:
                raise HTTPException(status_code=500, detail=str(e))
    
    @staticmethod
    async def download_job_pdf(
        db: Session,
        user: User,
        job_id: int,
        include_source: bool = True,
        include_illustrations: bool = True,
        page_size: str = "A4"
    ):
        """
        Download the translation as a PDF document.
        
        Args:
            db: Database session
            user: Current user
            job_id: Job ID
            include_source: Whether to include source text
            include_illustrations: Whether to include illustrations
            page_size: Page size format
            
        Returns:
            Response with PDF file
            
        Raises:
            HTTPException: If job not found, not authorized, or PDF generation fails
        """
        service = ExportDomainService(db)
        
        # Validate page size
        if page_size not in ["A4", "Letter"]:
            raise HTTPException(status_code=400, detail="Invalid page size. Must be 'A4' or 'Letter'")
        
        try:
            # Create request object
            request = PDFExportRequest(
                job_id=job_id,
                include_source=include_source,
                include_illustrations=include_illustrations,
                page_size=page_size
            )
            
            # Generate PDF
            pdf_bytes = await service.generate_pdf(user, request)
            
            # Generate filename
            pdf_filename = service.get_pdf_filename(job_id)
            
            # Return PDF response
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{pdf_filename}"'
                }
            )
            
        except ValueError as e:
            if "Job not found" in str(e):
                raise HTTPException(status_code=404, detail=str(e))
            elif "Not authorized" in str(e):
                raise HTTPException(status_code=403, detail=str(e))
            elif "PDF generation is available only" in str(e):
                raise HTTPException(status_code=400, detail=str(e))
            else:
                raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logging.error(f"Unexpected error generating PDF for job {job_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")