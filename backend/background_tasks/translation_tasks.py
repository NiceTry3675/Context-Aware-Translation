import traceback
import gc
from typing import Optional

from ..database import SessionLocal
from ..services.translation_service import TranslationService
from .. import crud


def run_translation_in_background(
    job_id: int,
    api_key: str,
    model_name: str,
    style_data: Optional[str] = None,
    glossary_data: Optional[str] = None
):
    """Background task to run a translation job."""
    db = None
    try:
        db = SessionLocal()
        job = crud.get_job(db, job_id)
        if not job:
            print(f"--- [BACKGROUND] Job ID {job_id} not found, cannot start translation ---")
            return

        crud.update_job_status(db, job_id, "PROCESSING")
        print(f"--- [BACKGROUND] Starting translation for Job ID: {job_id}, File: {job.filename}, Model: {model_name} ---")
        
        # Prepare translation components
        translation_service = TranslationService()
        components = translation_service.prepare_translation_job(
            job_id=job_id,
            job=job, # Pass the full job object
            api_key=api_key,
            model_name=model_name,
            style_data=style_data,
            glossary_data=glossary_data
        )
        
        # Run the translation
        TranslationService.run_translation(
            job_id=job_id,
            translation_document=components['translation_document'],
            model_api=components['model_api'],
            protagonist_name=components['protagonist_name'],
            initial_glossary=components['initial_glossary'],
            initial_core_style_text=components['initial_core_style_text'],
            db=db
        )
        
        crud.update_job_status(db, job_id, "COMPLETED")
        print(f"--- [BACKGROUND] Translation finished for Job ID: {job_id}, File: {job.filename} ---")
        
    except Exception as e:
        if db:
            error_message = f"An unexpected error occurred: {str(e)}"
            crud.update_job_status(db, job_id, "FAILED", error_message=error_message)
        print(f"--- [BACKGROUND] An unexpected error occurred for Job ID: {job_id}, File: {job.filename}. Error: {e} ---")
        traceback.print_exc()
        
    finally:
        if db:
            db.close()
        gc.collect()
        print(f"--- [BACKGROUND] Job ID: {job_id} finished. DB session closed and GC collected. ---")