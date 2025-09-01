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
    model_name: str | None = None,
    api_key: str | None = None,
):
    """Background task to run validation on a completed translation."""
    db = None
    try:
        db = SessionLocal()
        job = crud.get_job(db, job_id=job_id)
        if not job:
            print(f"--- [VALIDATION] Job ID {job_id} not found ---")
            return
        
        # Create validation service instance
        validation_service = ValidationService()
        
        # Update status to IN_PROGRESS
        validation_service.update_job_validation_status(db, job, "IN_PROGRESS", progress=0)
        print(f"--- [VALIDATION] Starting validation for Job ID: {job_id} ---")
        
        # Determine API key: prefer provided, then fall back to env
        # Supports deployments where .env isn't loaded in the worker
        api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            # Some setups use GOOGLE_API_KEY — try that as a fallback
            api_key = os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            raise RuntimeError("No API key provided for validation. Supply api_key in the request or set GEMINI_API_KEY/GOOGLE_API_KEY in env.")
        model_name = model_name or "gemini-2.5-flash-lite"
        
        # Prepare validation components
        validator, validation_job, translated_path = validation_service.prepare_validation(
            job=job,
            api_key=api_key,
            model_name=model_name
        )
        
        # Define progress callback
        def update_progress(progress: int):
            crud.update_job_validation_progress(db, job_id, progress)
            print(f"--- [VALIDATION] Progress: {progress}% ---")
        
        # Run validation
        sample_rate = validation_sample_rate / 100.0  # Convert percentage to decimal
        report = validation_service.run_validation(
            validator=validator,
            validation_document=validation_job,
            sample_rate=sample_rate,
            quick_mode=quick_validation,
            progress_callback=update_progress
        )
        
        # Save validation report
        report_path = validation_service.save_validation_report(job, report)
        
        # Update job with results
        validation_service.update_job_validation_status(
            db, job, "COMPLETED", progress=100, report_path=report_path
        )
        
        print(f"--- [VALIDATION] Completed validation for Job ID: {job_id} ---")
        
    except Exception as e:
        if db:
            job = crud.get_job(db, job_id=job_id)
            if job:
                validation_service = ValidationService()
                validation_service.update_job_validation_status(db, job, "FAILED")
        print(f"--- [VALIDATION] Error validating Job ID {job_id}: {e} ---")
        traceback.print_exc()
        
    finally:
        if db:
            db.close()
        gc.collect()
