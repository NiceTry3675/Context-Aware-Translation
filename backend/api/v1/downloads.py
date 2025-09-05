"""File download and content retrieval API endpoints."""

import os
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from ...dependencies import get_db, get_required_user
from ...domains.shared.utils import FileManager
from ...domains.shared.pdf_generator import generate_translation_pdf
from ... import models, auth, schemas
from ...domains.translation.repository import SqlAlchemyTranslationJobRepository

router = APIRouter(tags=["downloads"])


@router.get("/download/{job_id}")
async def download_job_output_legacy(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_required_user)
):
    """Legacy download endpoint for backward compatibility."""
    return await download_job_output(job_id, db, current_user)


@router.get("/jobs/{job_id}/output")
async def download_job_output(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_required_user)
):
    """Download the output of a translation job."""
    repo = SqlAlchemyTranslationJobRepository(db)
    db_job = repo.get(job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check ownership
    if not db_job.owner or db_job.owner.clerk_user_id != current_user.clerk_user_id:
        user_is_admin = await auth.is_admin(current_user)
        if not user_is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to download this file")
    
    if db_job.status not in ["COMPLETED", "FAILED"]:
        raise HTTPException(status_code=400, detail=f"Translation is not completed yet. Current status: {db_job.status}")
    
    if not db_job.filepath:
        raise HTTPException(status_code=404, detail="Filepath not found for this job.")
    
    file_manager = FileManager()
    file_path, user_translated_filename, media_type = file_manager.get_translated_file_path(db_job)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Translated file not found at path: {file_path}")
    
    return FileResponse(path=file_path, filename=user_translated_filename, media_type=media_type)


@router.get("/jobs/{job_id}/logs/{log_type}")
async def download_job_log(
    job_id: int,
    log_type: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_required_user)
):
    """Download log files for a translation job."""
    repo = SqlAlchemyTranslationJobRepository(db)
    db_job = repo.get(job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check ownership
    if not db_job.owner or db_job.owner.clerk_user_id != current_user.clerk_user_id:
        user_is_admin = await auth.is_admin(current_user)
        if not user_is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to download logs for this file")
    
    if log_type not in ["prompts", "context"]:
        raise HTTPException(status_code=400, detail="Invalid log type. Must be 'prompts' or 'context'.")
    
    base, _ = os.path.splitext(db_job.filename)
    log_dir = "logs/debug_prompts" if log_type == "prompts" else "logs/context_log"
    log_filename = f"{log_type}_job_{job_id}_{base}.txt"
    log_path = os.path.join(log_dir, log_filename)
    
    if not os.path.exists(log_path):
        raise HTTPException(status_code=404, detail=f"{log_type.capitalize()} log file not found.")
    
    return FileResponse(path=log_path, filename=log_filename, media_type="text/plain")


@router.get("/jobs/{job_id}/glossary", response_model=None)
async def get_job_glossary(
    job_id: int,
    structured: bool = False,  # Optional parameter to return structured response
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_required_user)
):
    """Get the final glossary for a completed translation job.
    
    Args:
        job_id: The job ID
        structured: If True, returns a GlossaryAnalysisResponse with structured data
    
    Returns:
        Either raw glossary dict or GlossaryAnalysisResponse depending on 'structured' param
    """
    repo = SqlAlchemyTranslationJobRepository(db)
    db_job = repo.get(job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check ownership or admin role
    user_is_admin = await auth.is_admin(current_user)
    if not db_job.owner or (db_job.owner.clerk_user_id != current_user.clerk_user_id and not user_is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to access this glossary")
    
    if db_job.status != "COMPLETED":
        raise HTTPException(status_code=400, detail=f"Glossary is available only for completed jobs. Current status: {db_job.status}")
    
    if not db_job.final_glossary:
        if structured:
            return schemas.GlossaryAnalysisResponse(glossary=[], translated_terms=schemas.TranslatedTerms(translations=[]))
        return {}
    
    # If structured response requested, parse and return GlossaryAnalysisResponse
    if structured:
        from core.schemas import TranslatedTerms, TranslatedTerm
        
        # Parse glossary based on format
        if isinstance(db_job.final_glossary, dict):
            if 'translations' in db_job.final_glossary:
                # Already in TranslatedTerms format
                translated_terms = TranslatedTerms(**db_job.final_glossary)
            else:
                # Convert from dict format
                translations = [
                    TranslatedTerm(source=k, korean=v)
                    for k, v in db_job.final_glossary.items()
                ]
                translated_terms = TranslatedTerms(translations=translations)
        else:
            # Return empty if format is unexpected
            translated_terms = TranslatedTerms(translations=[])
        
        return schemas.GlossaryAnalysisResponse(
            glossary=translated_terms.translations,
            translated_terms=translated_terms
        )
    
    # Default: return raw glossary
    return db_job.final_glossary


@router.get("/jobs/{job_id}/segments")
async def get_job_segments(
    job_id: int,
    offset: int = Query(0, ge=0, description="Starting segment index"),
    limit: int = Query(3, ge=1, le=200, description="Number of segments to return"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_required_user)
):
    """Get the segmented translation data for a completed translation job with pagination support."""
    repo = SqlAlchemyTranslationJobRepository(db)
    db_job = repo.get(job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check ownership
    if not db_job.owner or db_job.owner.clerk_user_id != current_user.clerk_user_id:
        user_is_admin = await auth.is_admin(current_user)
        if not user_is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to access this content")
    
    # Check if either translation is completed OR validation is completed (validation creates segments too)
    if db_job.status != "COMPLETED":
        # If translation not complete, check if validation is done (which also provides segments)
        if db_job.validation_status != "COMPLETED":
            raise HTTPException(status_code=400, detail=f"Translation segments are available only for completed jobs or validated jobs. Job status: {db_job.status}, Validation status: {db_job.validation_status}")
    
    # Get segments from different sources based on availability
    segments = db_job.translation_segments
    
    # If no translation segments but validation is complete, extract from validation report
    if not segments and db_job.validation_status == "COMPLETED" and db_job.validation_report_path:
        try:
            with open(db_job.validation_report_path, 'r', encoding='utf-8') as f:
                report = json.load(f)
            
            # Extract segments from validation report
            segments = []
            for result in report.get('detailed_results', []):
                segment_data = {
                    "source_text": result.get('source_text', ''),
                    "translated_text": result.get('translated_text', ''),
                    "segment_index": result.get('segment_index', 0)
                }
                segments.append(segment_data)
        except Exception as e:
            print(f"Error reading validation report for segments: {e}")
            segments = []
    
    # Return empty segments if still not available
    if not segments:
        return {
            "job_id": job_id,
            "filename": db_job.filename,
            "segments": [],
            "total_segments": 0,
            "has_more": False,
            "offset": offset,
            "limit": limit,
            "completed_at": db_job.completed_at.isoformat() if db_job.completed_at else None,
            "message": "No segments available for this job."
        }
    
    # Get total segments
    total_segments = len(segments)
    
    # Apply pagination
    end_index = min(offset + limit, total_segments)
    paginated_segments = segments[offset:end_index]
    
    # Return paginated segments as JSON
    return {
        "job_id": job_id,
        "filename": db_job.filename,
        "segments": paginated_segments,
        "total_segments": total_segments,
        "has_more": end_index < total_segments,
        "offset": offset,
        "limit": limit,
        "completed_at": db_job.completed_at.isoformat() if db_job.completed_at else None
    }


@router.get("/jobs/{job_id}/content")
async def get_job_content(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_required_user)
):
    """Get the translated content as text for a completed translation job."""
    repo = SqlAlchemyTranslationJobRepository(db)
    db_job = repo.get(job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check ownership
    if not db_job.owner or db_job.owner.clerk_user_id != current_user.clerk_user_id:
        user_is_admin = await auth.is_admin(current_user)
        if not user_is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to access this content")
    
    # Check if either translation is completed OR validation is completed
    if db_job.status != "COMPLETED":
        # If translation not complete, check if validation is done (which also provides content)
        if db_job.validation_status != "COMPLETED":
            raise HTTPException(status_code=400, detail=f"Translation content is available only for completed jobs or validated jobs. Job status: {db_job.status}, Validation status: {db_job.validation_status}")
    
    # Determine which file to return based on what's available
    file_path = None
    
    # Check if we have a translation file (post-edit overwrites the original, so we use the same path)
    if db_job.filepath:
        file_manager = FileManager()
        file_path, _, _ = file_manager.get_translated_file_path(db_job)
        if not os.path.exists(file_path):
            # If translated file doesn't exist but validation is complete, we can extract from validation report
            if db_job.validation_status != "COMPLETED" or not db_job.validation_report_path:
                raise HTTPException(status_code=404, detail=f"Translated file not found")
            file_path = None  # Will extract from validation report
    elif db_job.validation_status == "COMPLETED" and db_job.validation_report_path:
        # For validation-only case, we need to extract content from validation report
        file_path = None  # Will handle below
    else:
        raise HTTPException(status_code=404, detail="No content file found for this job.")
    
    # Handle validation report case specially - extract translated content from report
    if file_path is None and db_job.validation_status == "COMPLETED" and db_job.validation_report_path:
        try:
            with open(db_job.validation_report_path, 'r', encoding='utf-8') as f:
                report = json.load(f)
            
            # Extract translated segments from validation report
            translated_segments = []
            for result in report.get('detailed_results', []):
                translated_text = result.get('translated_text', '')
                if translated_text:
                    translated_segments.append(translated_text)
            
            content = '\n'.join(translated_segments) if translated_segments else ""
            if not content:
                raise HTTPException(status_code=404, detail="No translated content found in validation report")
        except Exception as e:
            print(f"Error reading validation report: {e}")
            raise HTTPException(status_code=500, detail="Error extracting content from validation report")
    else:
        # Regular file reading
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")
    
    # Try to read the original source file
    source_content = None
    if db_job.filepath and os.path.exists(db_job.filepath):
        try:
            # Parse the original file to get the text content
            from core.utils.file_parser import parse_document
            source_content = parse_document(db_job.filepath)
        except Exception as e:
            # Log error but don't fail the whole request
            print(f"Error reading source file: {e}")
    
    # Return content as JSON with metadata
    return {
        "job_id": job_id,
        "filename": db_job.filename,
        "content": content,
        "source_content": source_content,
        "completed_at": db_job.completed_at.isoformat() if db_job.completed_at else None
    }


@router.get("/jobs/{job_id}/pdf")
async def download_job_pdf(
    job_id: int,
    include_source: bool = Query(True, description="Include source text in PDF"),
    include_illustrations: bool = Query(True, description="Include illustrations in PDF"),
    page_size: str = Query("A4", description="Page size (A4 or Letter)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_required_user)
):
    """
    Download the translation as a PDF document with optional illustrations.
    
    This endpoint generates a professional PDF document containing:
    - Translated text segments
    - Source text (optional)
    - Illustrations for each segment where available
    - Proper formatting and pagination
    
    Args:
        job_id: ID of the translation job
        include_source: Whether to include source text alongside translations
        include_illustrations: Whether to embed generated illustrations
        page_size: Page size format (A4 or Letter)
    
    Returns:
        PDF file response
    """
    # Get the job from database
    repo = SqlAlchemyTranslationJobRepository(db)
    db_job = repo.get(job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check ownership
    if not db_job.owner or db_job.owner.clerk_user_id != current_user.clerk_user_id:
        user_is_admin = await auth.is_admin(current_user)
        if not user_is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to download this PDF")
    
    # Check if job is completed
    if db_job.status != "COMPLETED":
        raise HTTPException(
            status_code=400, 
            detail=f"PDF generation is available only for completed jobs. Current status: {db_job.status}"
        )
    
    # Validate page size
    if page_size not in ["A4", "Letter"]:
        raise HTTPException(status_code=400, detail="Invalid page size. Must be 'A4' or 'Letter'")
    
    try:
        # Generate PDF
        pdf_bytes = generate_translation_pdf(
            job_id=job_id,
            db=db,
            include_source=include_source,
            include_illustrations=include_illustrations,
            page_size=page_size
        )
        
        # Generate filename
        base_filename = db_job.filename.rsplit('.', 1)[0] if '.' in db_job.filename else db_job.filename
        pdf_filename = f"{base_filename}_translation.pdf"
        
        # Return PDF response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{pdf_filename}"'
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Error generating PDF for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")