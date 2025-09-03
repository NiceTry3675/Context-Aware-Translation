"""Translation job management API endpoints."""

import os
import re
import shutil
from typing import List

from fastapi import APIRouter, File, UploadFile, BackgroundTasks, Depends, HTTPException, Form, Response
from sqlalchemy.orm import Session

from ...dependencies import get_db, get_required_user
from ...services.base.model_factory import ModelAPIFactory
from ...services.utils.file_manager import FileManager
from ...tasks.translation import process_translation_task
from ... import crud, models, schemas, auth

router = APIRouter(tags=["jobs"])


@router.get("/jobs", response_model=List[schemas.TranslationJob])
async def list_jobs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_required_user)
):
    """List all translation jobs for the current user."""
    jobs = crud.get_jobs_by_user(db, user_id=current_user.id, skip=skip, limit=limit)
    return jobs


@router.post("/jobs", response_model=schemas.TranslationJob)
async def create_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    api_key: str = Form(...),
    model_name: str = Form("gemini-2.5-flash-lite"),
    # Optional per-task model overrides
    translation_model_name: str | None = Form(None),
    style_model_name: str | None = Form(None),
    glossary_model_name: str | None = Form(None),
    style_data: str = Form(None),
    glossary_data: str = Form(None),
    segment_size: int = Form(15000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_required_user)
):
    """Create a new translation job."""
    if not ModelAPIFactory.validate_api_key(api_key, model_name):
        raise HTTPException(status_code=400, detail="Invalid API Key or unsupported model.")
    
    # Create job in database
    job_create = schemas.TranslationJobCreate(
        filename=file.filename, 
        owner_id=current_user.id,
        segment_size=segment_size
    )
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
    
    # Start translation in background using Celery
    process_translation_task.delay(
        job_id=db_job.id,
        api_key=api_key,
        model_name=model_name,
        style_data=style_data,
        glossary_data=glossary_data,
        translation_model_name=translation_model_name,
        style_model_name=style_model_name,
        glossary_model_name=glossary_model_name,
        user_id=current_user.id
    )
    
    return db_job


@router.get("/jobs/{job_id}", response_model=schemas.TranslationJob)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """Get a translation job."""
    db_job = crud.get_job(db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return db_job


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_required_user)
):
    """Delete a translation job and its associated files."""
    db_job = crud.get_job(db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check ownership or admin role
    user_is_admin = await auth.is_admin(current_user)
    if not db_job.owner or (db_job.owner.clerk_user_id != current_user.clerk_user_id and not user_is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to delete this job")

    # Delete associated files
    try:
        FileManager.delete_job_files(db_job)
    except Exception as e:
        # Log the error but proceed with deleting the DB record
        print(f"Error deleting files for job {job_id}: {e}")

    # Delete the job from the database
    crud.delete_job(db, job_id=job_id)

    return Response(status_code=204)
