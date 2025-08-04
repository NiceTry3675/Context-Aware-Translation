"""Translation API endpoints."""

import os
import re
import json
import shutil
from typing import List

from fastapi import APIRouter, File, UploadFile, BackgroundTasks, Depends, HTTPException, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ...dependencies import get_db, get_required_user
from ...services.translation_service import TranslationService
from ...services.validation_service import ValidationService
from ...services.post_edit_service import PostEditService
from ...background_tasks.translation_tasks import run_translation_in_background
from ...background_tasks.validation_tasks import run_validation_in_background
from ...background_tasks.post_edit_tasks import run_post_edit_in_background
from ... import crud, models, schemas, auth


router = APIRouter(prefix="/api/v1", tags=["translation"])


class StyleAnalysisResponse(BaseModel):
    protagonist_name: str
    narration_style_endings: str
    tone_keywords: str
    stylistic_rule: str


class GlossaryTerm(BaseModel):
    term: str
    translation: str


class GlossaryAnalysisResponse(BaseModel):
    glossary: List[GlossaryTerm]


@router.post("/analyze-style", response_model=StyleAnalysisResponse)
async def analyze_style(
    file: UploadFile = File(...),
    api_key: str = Form(...),
    model_name: str = Form("gemini-2.5-flash-lite"),
):
    """Analyze the narrative style of a document."""
    if not TranslationService.validate_api_key(api_key, model_name):
        raise HTTPException(status_code=400, detail="Invalid API Key or unsupported model.")
    
    try:
        temp_file_path, _ = TranslationService.save_uploaded_file(file.file, file.filename)
        
        try:
            parsed_style = TranslationService.analyze_style(
                temp_file_path, api_key, model_name, file.filename
            )
            return StyleAnalysisResponse(**parsed_style)
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze style: {e}")


@router.post("/analyze-glossary", response_model=GlossaryAnalysisResponse)
async def analyze_glossary(
    file: UploadFile = File(...),
    api_key: str = Form(...),
    model_name: str = Form("gemini-2.5-flash-lite"),
):
    """Extract glossary terms from a document."""
    if not TranslationService.validate_api_key(api_key, model_name):
        raise HTTPException(status_code=400, detail="Invalid API Key or unsupported model.")
    
    try:
        temp_file_path, _ = TranslationService.save_uploaded_file(file.file, file.filename)
        
        try:
            parsed_glossary = TranslationService.analyze_glossary(
                temp_file_path, api_key, model_name, file.filename
            )
            return GlossaryAnalysisResponse(glossary=parsed_glossary)
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract glossary: {e}")


@router.post("/jobs", response_model=schemas.TranslationJob)
async def create_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    api_key: str = Form(...),
    model_name: str = Form("gemini-2.5-flash-lite"),
    style_data: str = Form(None),
    glossary_data: str = Form(None),
    segment_size: int = Form(15000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_required_user)
):
    """Create a new translation job."""
    if not TranslationService.validate_api_key(api_key, model_name):
        raise HTTPException(status_code=400, detail="Invalid API Key or unsupported model.")
    
    # Create job in database
    job_create = schemas.TranslationJobCreate(filename=file.filename, owner_id=current_user.id)
    db_job = crud.create_translation_job(db, job_create)
    
    # Save uploaded file
    sanitized_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', file.filename)
    unique_filename = f"{db_job.id}_{sanitized_filename}"
    file_path = f"uploads/{unique_filename}"
    
    os.makedirs("uploads", exist_ok=True)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        crud.update_job_status(db, db_job.id, "FAILED", error_message=f"Failed to save file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
    
    crud.update_job_filepath(db, job_id=db_job.id, filepath=file_path)
    
    # Start translation in background
    background_tasks.add_task(
        run_translation_in_background,
        db_job.id, file_path, file.filename, api_key, model_name,
        style_data, glossary_data, segment_size
    )
    
    return db_job


@router.get("/jobs/{job_id}", response_model=schemas.TranslationJob)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """Get a translation job."""
    db_job = crud.get_job(db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return db_job


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


@router.get("/jobs/{job_id}/glossary")
async def get_job_glossary(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_required_user)
):
    """Get the final glossary for a completed translation job."""
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
        return {}
    
    return db_job.final_glossary


@router.put("/jobs/{job_id}/validation")
async def trigger_validation(
    job_id: int,
    background_tasks: BackgroundTasks,
    quick_validation: bool = Form(False),
    validation_sample_rate: int = Form(100),  # percentage 0-100
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_required_user)
):
    """Trigger validation on a completed translation job."""
    db_job = crud.get_job(db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check ownership or admin role
    user_is_admin = await auth.is_admin(current_user)
    if not db_job.owner or (db_job.owner.clerk_user_id != current_user.clerk_user_id and not user_is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to validate this job")
    
    if db_job.status != "COMPLETED":
        raise HTTPException(status_code=400, detail=f"Can only validate completed jobs. Current status: {db_job.status}")
    
    # Update job with validation settings
    db_job.validation_enabled = True
    db_job.validation_status = "PENDING"
    db_job.quick_validation = quick_validation
    db_job.validation_sample_rate = validation_sample_rate
    db.commit()
    
    # Add background task to run validation
    background_tasks.add_task(
        run_validation_in_background,
        job_id, db_job.filepath, quick_validation, validation_sample_rate
    )
    
    return {"message": "Validation started", "job_id": job_id}


@router.get("/jobs/{job_id}/validation-report")
async def get_validation_report(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_required_user)
):
    """Get the validation report for a job."""
    print(f"--- [API] Getting validation report for job {job_id} ---")
    db_job = crud.get_job(db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check ownership or admin role
    user_is_admin = await auth.is_admin(current_user)
    if not db_job.owner or (db_job.owner.clerk_user_id != current_user.clerk_user_id and not user_is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to access this validation report")
    
    if db_job.validation_status != "COMPLETED":
        print(f"--- [API] Validation not completed. Status: {db_job.validation_status} ---")
        raise HTTPException(status_code=400, detail=f"Validation not completed. Current status: {db_job.validation_status}")
    
    print(f"--- [API] Validation report path: {db_job.validation_report_path} ---")
    if not db_job.validation_report_path or not os.path.exists(db_job.validation_report_path):
        print(f"--- [API] Report not found at path: {db_job.validation_report_path} ---")
        raise HTTPException(status_code=404, detail="Validation report not found")
    
    # Read and return the JSON report
    with open(db_job.validation_report_path, 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    print(f"--- [API] Successfully loaded validation report with {len(report.get('detailed_results', []))} results ---")
    return report


@router.put("/jobs/{job_id}/post-edit")
async def trigger_post_edit(
    job_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_required_user)
):
    """Trigger post-editing on a validated translation job."""
    db_job = crud.get_job(db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check ownership or admin role
    user_is_admin = await auth.is_admin(current_user)
    if not db_job.owner or (db_job.owner.clerk_user_id != current_user.clerk_user_id and not user_is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to post-edit this job")
    
    # Validate prerequisites
    try:
        PostEditService.validate_post_edit_prerequisites(db_job)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Update job with post-edit settings
    db_job.post_edit_enabled = True
    db_job.post_edit_status = "PENDING"
    db.commit()
    
    # Add background task to run post-editing
    background_tasks.add_task(
        run_post_edit_in_background,
        job_id, db_job.filepath, db_job.validation_report_path
    )
    
    return {"message": "Post-editing started", "job_id": job_id}


@router.get("/jobs/{job_id}/post-edit-log")
async def get_post_edit_log(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_required_user)
):
    """Get the post-edit log for a job."""
    db_job = crud.get_job(db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check ownership or admin role
    user_is_admin = await auth.is_admin(current_user)
    if not db_job.owner or (db_job.owner.clerk_user_id != current_user.clerk_user_id and not user_is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to access this post-edit log")
    
    if db_job.post_edit_status != "COMPLETED":
        raise HTTPException(status_code=400, detail=f"Post-editing not completed. Current status: {db_job.post_edit_status}")
    
    if not db_job.post_edit_log_path or not os.path.exists(db_job.post_edit_log_path):
        raise HTTPException(status_code=404, detail="Post-edit log not found")
    
    # Read and return the JSON log
    with open(db_job.post_edit_log_path, 'r', encoding='utf-8') as f:
        log = json.load(f)
    
    return log