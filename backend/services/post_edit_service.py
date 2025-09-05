import os
from typing import Optional, Callable
from sqlalchemy.orm import Session

from core.translation.post_editor import PostEditEngine
from core.translation.document import TranslationDocument
from .base.base_service import BaseService
from .. import models


class PostEditService(BaseService):
    """Service layer for post-editing operations."""
    
    def __init__(self):
        """Initialize post-edit service."""
        super().__init__()
    
    def prepare_post_edit(
        self,
        job: models.TranslationJob,
        api_key: str,
        model_name: str = "gemini-2.5-flash-lite"
    ) -> tuple[PostEditEngine, TranslationDocument, str]:
        """Prepare the post-editor and translation job for post-editing."""
        # Get the translated file path using FileManager
        translated_path, _, _ = self.file_manager.get_translated_file_path(job)
        
        if not self.file_manager.file_exists(translated_path):
            raise FileNotFoundError(f"Translated file not found: {translated_path}")
        
        # Initialize post-editor
        model_api = self.create_model_api(api_key, model_name)
        
        post_editor = PostEditEngine(model_api)
        
        # Create translation document for post-editing
        translation_document = TranslationDocument(
            job.filepath, 
            original_filename=job.filename,
            target_segment_size=job.segment_size
        )
        
        # Fail-fast: Use stored translation segments from DB for exact alignment only
        db_segments = getattr(job, 'translation_segments', None)
        if not db_segments or not isinstance(db_segments, list):
            raise ValueError(
                "Translation segments not found for this job. Post-editing requires saved segments."
            )

        # Extract translated_text list from DB segments
        if any(isinstance(seg, dict) for seg in db_segments):
            translated_list = [
                (seg.get('translated_text') if isinstance(seg, dict) else None)
                for seg in db_segments
            ]
        else:
            # Legacy format: list of plain strings
            translated_list = [seg for seg in db_segments if isinstance(seg, str)]

        # Validate extracted list
        if not translated_list or any(t is None for t in translated_list):
            raise ValueError(
                "Invalid translation segments schema. Expected 'translated_text' per segment."
            )

        translation_document.translated_segments = translated_list[:]

        # Strict count match with source segments
        if len(translation_document.translated_segments) != len(translation_document.segments):
            raise ValueError(
                f"Translation segments count mismatch (source={len(translation_document.segments)}, "
                f"translated={len(translation_document.translated_segments)})."
            )
        
        return post_editor, translation_document, translated_path
    
    def run_post_edit(
        self,
        post_editor: PostEditEngine,
        translation_document: TranslationDocument,
        translated_path: str,
        validation_report_path: str,
        selected_cases: dict | None = None,
        progress_callback: Optional[Callable[[int], None]] = None,
        job_id: Optional[int] = None,
    ):
        """Run the post-editing process and overwrite the translated file."""
        edited_segments = post_editor.post_edit_document(
            translation_document,
            validation_report_path,
            selected_cases,
            progress_callback=progress_callback,
            job_id=job_id,
        )

        # Overwrite the translated file with the edited content
        try:
            with open(translated_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(edited_segments))
            print(f"--- [POST-EDIT] Successfully updated translated file: {translated_path} ---")
        except IOError as e:
            print(f"--- [POST-EDIT] Error writing to translated file: {e} ---")
            # Optionally, re-raise or handle the error appropriately
            raise e
    
    def get_post_edit_log_path(self, job: models.TranslationJob) -> str:
        """Get the post-edit log file path."""
        # Use FileManager to get the post-edit log path
        return self.file_manager.get_post_edit_log_path(job)
    
    def update_job_post_edit_status(
        self,
        db: Session,
        job: models.TranslationJob,
        status: str,
        log_path: Optional[str] = None
    ):
        """Update the job's post-edit status in the database."""
        job.post_edit_status = status
        
        if log_path:
            job.post_edit_log_path = log_path
            
        if status == "COMPLETED":
            from sqlalchemy.sql import func
            job.post_edit_completed_at = func.now()
        
        db.commit()
    
    def validate_post_edit_prerequisites(self, job: models.TranslationJob):
        """Validate that a job is ready for post-editing."""
        if job.validation_status != "COMPLETED":
            raise ValueError("Validation must be completed before post-editing")
        
        if not job.validation_report_path:
            raise ValueError("Validation report not found")
        
        if not self.file_manager.file_exists(job.validation_report_path):
            raise FileNotFoundError(f"Validation report file not found: {job.validation_report_path}")