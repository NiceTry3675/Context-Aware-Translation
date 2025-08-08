import os
from typing import Optional, Callable
from sqlalchemy.orm import Session

from core.translation.post_editor import PostEditEngine
from core.translation.job import TranslationJob
from .translation_service import TranslationService
from .. import crud, models


class PostEditService:
    """Service layer for post-editing operations."""
    
    @staticmethod
    def prepare_post_edit(
        job: models.TranslationJob,
        api_key: str,
        model_name: str = "gemini-2.5-flash-lite"
    ) -> tuple[PostEditEngine, TranslationJob, str]:
        """Prepare the post-editor and translation job for post-editing."""
        # Get the translated file path
        unique_base = os.path.splitext(os.path.basename(job.filepath))[0]
        original_ext = os.path.splitext(job.filename)[1].lower()
        
        if original_ext == '.epub':
            output_ext = '.epub'
        else:
            output_ext = '.txt'
        
        translated_filename = f"{unique_base}_translated{output_ext}"
        translated_path = os.path.join("translated_novel", translated_filename)
        
        if not os.path.exists(translated_path):
            raise FileNotFoundError(f"Translated file not found: {translated_path}")
        
        # Initialize post-editor
        from core.config.loader import load_config
        config = load_config()
        model_api = TranslationService.get_model_api(api_key, model_name, config)
        
        post_editor = PostEditEngine(model_api)
        
        # Create translation job for post-editing
        translation_job = TranslationJob(
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

        translation_job.translated_segments = translated_list[:]

        # Strict count match with source segments
        if len(translation_job.translated_segments) != len(translation_job.segments):
            raise ValueError(
                f"Translation segments count mismatch (source={len(translation_job.segments)}, "
                f"translated={len(translation_job.translated_segments)})."
            )
        
        return post_editor, translation_job, translated_path
    
    @staticmethod
    def run_post_edit(
        post_editor: PostEditEngine,
        translation_job: TranslationJob,
        translated_path: str,
        validation_report_path: str,
        selected_issue_types: dict = None,
        selected_issues: dict = None,
        progress_callback: Optional[Callable[[int], None]] = None
    ):
        """Run the post-editing process and overwrite the translated file."""
        edited_segments = post_editor.post_edit_job(
            translation_job,
            validation_report_path,
            selected_issue_types,
            selected_issues,
            progress_callback=progress_callback
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
    
    @staticmethod
    def get_post_edit_log_path(job: models.TranslationJob) -> str:
        """Get the post-edit log file path."""
        log_filename = f"{os.path.splitext(job.filename)[0]}_postedit_log.json"
        log_path = os.path.join("postedit_logs", log_filename)
        return log_path
    
    @staticmethod
    def update_job_post_edit_status(
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
    
    @staticmethod
    def validate_post_edit_prerequisites(job: models.TranslationJob):
        """Validate that a job is ready for post-editing."""
        if job.validation_status != "COMPLETED":
            raise ValueError("Validation must be completed before post-editing")
        
        if not job.validation_report_path:
            raise ValueError("Validation report not found")
        
        if not os.path.exists(job.validation_report_path):
            raise FileNotFoundError(f"Validation report file not found: {job.validation_report_path}")