import os
import traceback
import gc

from ..database import SessionLocal
from ..services.post_edit_service import PostEditService
from .. import crud


def run_post_edit_in_background(
    job_id: int,
    file_path: str,
    validation_report_path: str
):
    """Background task to run post-editing on a validated translation."""
    db = None
    try:
        db = SessionLocal()
        job = crud.get_job(db, job_id=job_id)
        if not job:
            print(f"--- [POST-EDIT] Job ID {job_id} not found ---")
            return
        
        # Update status to IN_PROGRESS
        PostEditService.update_job_post_edit_status(db, job, "IN_PROGRESS")
        print(f"--- [POST-EDIT] Starting post-editing for Job ID: {job_id} ---")
        
        # Get API key - for now using environment variable
        # In production, this should be retrieved from secure storage
        api_key = os.environ.get("GEMINI_API_KEY", "")
        model_name = "gemini-2.5-flash-lite"
        
        # Prepare post-edit components
        post_editor, translation_job, translated_path = PostEditService.prepare_post_edit(
            job=job,
            api_key=api_key,
            model_name=model_name
        )
        
        # Run post-editing
        postedited_path = PostEditService.run_post_edit(
            post_editor=post_editor,
            translation_job=translation_job,
            translated_path=translated_path,
            validation_report_path=validation_report_path
        )
        
        # Get the post-edit log path
        log_path = PostEditService.get_post_edit_log_path(job)
        
        # Update job with results
        PostEditService.update_job_post_edit_status(
            db, job, "COMPLETED", log_path=log_path
        )
        
        print(f"--- [POST-EDIT] Completed post-editing for Job ID: {job_id} ---")
        
    except Exception as e:
        if db:
            job = crud.get_job(db, job_id=job_id)
            if job:
                PostEditService.update_job_post_edit_status(db, job, "FAILED")
        print(f"--- [POST-EDIT] Error post-editing Job ID {job_id}: {e} ---")
        traceback.print_exc()
        
    finally:
        if db:
            db.close()
        gc.collect()