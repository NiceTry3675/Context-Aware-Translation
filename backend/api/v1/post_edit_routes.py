"""Post-edit API endpoints."""

import os
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...dependencies import get_db, get_required_user
from ...services.post_edit_service import PostEditService
from ...tasks.post_edit import process_post_edit_task
from ... import models, auth
from ...schemas import PostEditRequest, StructuredPostEditLog
from ...domains.translation.repository import SqlAlchemyTranslationJobRepository

router = APIRouter(tags=["post-edit"])


@router.put("/jobs/{job_id}/post-edit")
async def trigger_post_edit(
    job_id: int,
    request: PostEditRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_required_user)
):
    """Trigger post-editing on a validated translation job."""
    repo = SqlAlchemyTranslationJobRepository(db)
    db_job = repo.get(job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check ownership or admin role
    user_is_admin = await auth.is_admin(current_user)
    if not db_job.owner or (db_job.owner.clerk_user_id != current_user.clerk_user_id and not user_is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to post-edit this job")
    
    # Validate prerequisites
    try:
        post_edit_service = PostEditService()
        post_edit_service.validate_post_edit_prerequisites(db_job)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Update job with post-edit settings
    db_job.post_edit_enabled = True
    db_job.post_edit_status = "PENDING"
    db.commit()
    
    # Start post-editing using Celery
    process_post_edit_task.delay(
        job_id=job_id,
        api_key=request.api_key,
        model_name=request.model_name,
        user_id=current_user.id
    )
    
    return {"message": "Post-editing started", "job_id": job_id}


@router.get("/jobs/{job_id}/post-edit-log", response_model=None)
async def get_post_edit_log(
    job_id: int,
    structured: bool = False,  # Optional parameter to return structured response
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_required_user)
):
    """Get the post-edit log for a job.
    
    Args:
        job_id: The job ID
        structured: If True, returns a StructuredPostEditLog with ValidationCase objects
    
    Returns:
        Either raw JSON log or StructuredPostEditLog depending on 'structured' param
    """
    repo = SqlAlchemyTranslationJobRepository(db)
    db_job = repo.get(job_id)
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
    
    # If structured response requested, parse and return StructuredPostEditLog
    if structured:
        return StructuredPostEditLog.from_json_log(log)
    
    # Default: return raw log
    return log
