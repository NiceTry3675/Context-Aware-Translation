"""File download and content retrieval API endpoints."""

import os
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ...dependencies import get_db, get_required_user
from ...services.translation_service import TranslationService
from ... import crud, models, auth, schemas

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
    db_job = crud.get_job(db, job_id=job_id)
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
    
    file_path, user_translated_filename, media_type = TranslationService.get_translated_file_path(db_job)
    
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
    db_job = crud.get_job(db, job_id=job_id)
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
    log_dir = "debug_prompts" if log_type == "prompts" else "context_log"
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
    db_job = crud.get_job(db, job_id=job_id)
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
    db_job = crud.get_job(db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check ownership
    if not db_job.owner or db_job.owner.clerk_user_id != current_user.clerk_user_id:
        user_is_admin = await auth.is_admin(current_user)
        if not user_is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to access this content")
    
    if db_job.status != "COMPLETED":
        raise HTTPException(status_code=400, detail=f"Translation segments are available only for completed jobs. Current status: {db_job.status}")
    
    # Return empty segments if not available (for jobs completed before segmentation was implemented)
    if not db_job.translation_segments:
        return {
            "job_id": job_id,
            "filename": db_job.filename,
            "segments": [],
            "total_segments": 0,
            "has_more": False,
            "offset": offset,
            "limit": limit,
            "completed_at": db_job.completed_at.isoformat() if db_job.completed_at else None,
            "message": "This job was completed before segment storage was implemented. Please run validation or post-editing to see segmented content."
        }
    
    # Get total segments
    total_segments = len(db_job.translation_segments)
    
    # Apply pagination
    end_index = min(offset + limit, total_segments)
    paginated_segments = db_job.translation_segments[offset:end_index]
    
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
    db_job = crud.get_job(db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check ownership
    if not db_job.owner or db_job.owner.clerk_user_id != current_user.clerk_user_id:
        user_is_admin = await auth.is_admin(current_user)
        if not user_is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to access this content")
    
    if db_job.status != "COMPLETED":
        raise HTTPException(status_code=400, detail=f"Translation content is available only for completed jobs. Current status: {db_job.status}")
    
    if not db_job.filepath:
        raise HTTPException(status_code=404, detail="Filepath not found for this job.")
    
    file_path, _, _ = TranslationService.get_translated_file_path(db_job)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Translated file not found at path: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading translation content: {str(e)}")