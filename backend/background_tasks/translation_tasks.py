import traceback
import gc
from typing import Optional

from ..database import SessionLocal
from ..services.translation_service import TranslationService
from .. import crud


def run_translation_in_background(
    job_id: int,
    file_path: str,
    filename: str,
    api_key: str,
    model_name: str,
    style_data: Optional[str] = None,
    glossary_data: Optional[str] = None,
    segment_size: int = 15000
):
    """Background task to run a translation job."""
    db = None
    try:
        db = SessionLocal()
        crud.update_job_status(db, job_id, "PROCESSING")
        print(f"--- [BACKGROUND] Starting translation for Job ID: {job_id}, File: {filename}, Model: {model_name} ---")
        
        # Prepare translation components
        components = TranslationService.prepare_translation_job(
            job_id=job_id,
            file_path=file_path,
            filename=filename,
            api_key=api_key,
            model_name=model_name,
            style_data=style_data,
            glossary_data=glossary_data,
            segment_size=segment_size
        )
        
        # Run the translation
        TranslationService.run_translation(
            job_id=job_id,
            translation_job=components['translation_job'],
            gemini_api=components['gemini_api'],
            protagonist_name=components['protagonist_name'],
            initial_glossary=components['initial_glossary'],
            initial_core_style_text=components['initial_core_style_text'],
            db=db
        )
        
        crud.update_job_status(db, job_id, "COMPLETED")
        print(f"--- [BACKGROUND] Translation finished for Job ID: {job_id}, File: {filename} ---")
        
    except Exception as e:
        if db:
            error_message = f"An unexpected error occurred: {str(e)}"
            crud.update_job_status(db, job_id, "FAILED", error_message=error_message)
        print(f"--- [BACKGROUND] An unexpected error occurred for Job ID: {job_id}, File: {filename}. Error: {e} ---")
        traceback.print_exc()
        
    finally:
        if db:
            db.close()
        gc.collect()
        print(f"--- [BACKGROUND] Job ID: {job_id} finished. DB session closed and GC collected. ---")