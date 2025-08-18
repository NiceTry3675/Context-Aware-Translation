import os
import traceback
import gc

from ..database import SessionLocal
from ..services.validation_service import ValidationService
from .. import crud


def run_validation_in_background(
    job_id: int,
    file_path: str,
    quick_validation: bool,
    validation_sample_rate: int,
    model_name: str,
):
    """Background task to run validation on a completed translation."""
    db = None
    try:
        db = SessionLocal()
        job = crud.get_job(db, job_id=job_id)
        if not job:
            print(f"--- [VALIDATION] Job ID {job_id} not found ---")
            return
        
        # Update status to IN_PROGRESS
        ValidationService.update_job_validation_status(db, job, "IN_PROGRESS", progress=0)
        print(f"--- [VALIDATION] Starting validation for Job ID: {job_id} ---")
        
        # Get API key - for now using environment variable
        # In production, this should be retrieved from secure storage
        api_key = os.environ.get("GEMINI_API_KEY", "")
        
        # Prepare validation components
        validator, validation_job, translated_path = ValidationService.prepare_validation(
            job=job,
            api_key=api_key,
            model_name=model_name
        )
        print(f"--- [VALIDATION] Using model: {model_name} ---")
        
        # Define progress callback
        def update_progress(progress: int):
            crud.update_job_validation_progress(db, job_id, progress)
            print(f"--- [VALIDATION] Progress: {progress}% ---")
        
        # Run validation
        sample_rate = validation_sample_rate / 100.0  # Convert percentage to decimal
        report = ValidationService.run_validation(
            validator=validator,
            validation_job=validation_job,
            sample_rate=sample_rate,
            quick_mode=quick_validation,
            progress_callback=update_progress
        )
        
        # Save validation report
        report_path = ValidationService.save_validation_report(job, report)
        
        # Update job with results
        ValidationService.update_job_validation_status(
            db, job, "COMPLETED", progress=100, report_path=report_path
        )
        
        print(f"--- [VALIDATION] Completed validation for Job ID: {job_id} ---")
        
    except Exception as e:
        if db:
            job = crud.get_job(db, job_id=job_id)
            if job:
                ValidationService.update_job_validation_status(db, job, "FAILED")
        print(f"--- [VALIDATION] Error validating Job ID {job_id}: {e} ---")
        traceback.print_exc()
        
    finally:
        if db:
            db.close()
        gc.collect()
