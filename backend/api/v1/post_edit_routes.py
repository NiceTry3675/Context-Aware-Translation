"""Post-edit API endpoints."""

import os
import json
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from ...dependencies import get_db, get_required_user
from ...services.post_edit_service import PostEditService
from ...background_tasks.post_edit_tasks import run_post_edit_in_background
from ... import crud, models, auth
from ...schemas import PostEditRequest

router = APIRouter(tags=["post-edit"])


@router.put("/jobs/{job_id}/post-edit")
async def trigger_post_edit(
    job_id: int,
    request: PostEditRequest,
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
        job_id, db_job.filepath, db_job.validation_report_path,
        request.selected_issue_types,
        request.selected_issues
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