import os
from typing import Optional
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
        translation_job = TranslationJob(job.filepath, original_filename=job.filename)
        
        # Load the translated segments from the translated file
        with open(translated_path, 'r', encoding='utf-8') as f:
            translated_text = f.read()
            translation_job.translated_segments = translated_text.split('\n')
            # Filter out empty strings from the list
            translation_job.translated_segments = [s for s in translation_job.translated_segments if s.strip()]
        
        # Handle segment count mismatch
        if len(translation_job.segments) != len(translation_job.translated_segments):
            print(f"Warning: Segment count mismatch - Source: {len(translation_job.segments)}, Translated: {len(translation_job.translated_segments)}")
            if len(translation_job.translated_segments) > len(translation_job.segments):
                # Too many translated segments, might be due to line breaks
                combined_segments = []
                lines_per_segment = len(translation_job.translated_segments) // len(translation_job.segments)
                for i in range(0, len(translation_job.translated_segments), lines_per_segment):
                    combined_segments.append('\n'.join(translation_job.translated_segments[i:i+lines_per_segment]))
                translation_job.translated_segments = combined_segments[:len(translation_job.segments)]
        
        return post_editor, translation_job, translated_path
    
    @staticmethod
    def run_post_edit(
        post_editor: PostEditEngine,
        translation_job: TranslationJob,
        translated_path: str,
        validation_report_path: str
    ) -> str:
        """Run the post-editing process."""
        postedited_path = post_editor.post_edit_job(
            translation_job,
            validation_report_path
        )
        
        return postedited_path
    
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