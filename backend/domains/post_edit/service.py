"""
Domain service for post-editing operations.

This service orchestrates post-editing logic using the repository pattern,
integrates with the Unit of Work for transaction management,
and publishes domain events for the post-edit lifecycle.
"""

import os
import json
from typing import Optional, Callable, Dict, Any, List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from core.translation.post_editor import PostEditEngine
from core.translation.document import TranslationDocument
from backend.domains.translation.models import TranslationJob
from backend.domains.translation.repository import TranslationJobRepository, SqlAlchemyTranslationJobRepository
from backend.domains.shared.uow import SqlAlchemyUoW
from backend.domains.shared.events import DomainEvent, EventType
from backend.domains.shared.utils import FileManager
from backend.config.settings import get_settings


class PostEditDomainService:
    """Service layer for post-editing operations using domain patterns."""
    
    def __init__(
        self,
        repository: Optional[TranslationJobRepository] = None,
        uow: Optional[SqlAlchemyUoW] = None,
        file_manager: Optional[FileManager] = None
    ):
        """
        Initialize post-edit service with dependencies.
        
        Args:
            repository: TranslationJob repository (optional, creates default if not provided)
            uow: Unit of Work for transaction management (optional)
            file_manager: File manager for file operations (optional, uses default if not provided)
        """
        self._repository = repository
        self._uow = uow
        self._file_manager = file_manager or FileManager()
    
    def _get_repository(self, session: Session) -> TranslationJobRepository:
        """Get or create repository instance."""
        if self._repository:
            return self._repository
        return SqlAlchemyTranslationJobRepository(session)
    
    def validate_prerequisites(
        self,
        session: Session,
        job_id: int
    ) -> TranslationJob:
        """
        Validate that a job is ready for post-editing.
        
        Args:
            session: Database session
            job_id: Translation job ID
            
        Returns:
            The validated translation job
            
        Raises:
            ValueError: If job not found or prerequisites not met
            FileNotFoundError: If required files not found
        """
        repository = self._get_repository(session)
        job = repository.get(job_id)
        
        if not job:
            raise ValueError(f"Translation job {job_id} not found")
        
        if job.validation_status != "COMPLETED":
            raise ValueError("Validation must be completed before post-editing")
        
        if not job.validation_report_path:
            raise ValueError("Validation report not found")
        
        if not self._file_manager.file_exists(job.validation_report_path):
            raise FileNotFoundError(
                f"Validation report file not found: {job.validation_report_path}"
            )
        
        return job
    
    def prepare_post_edit(
        self,
        session: Session,
        job_id: int,
        api_key: str,
        model_name: str = "gemini-2.0-flash-exp"
    ) -> Tuple[PostEditEngine, TranslationDocument, str]:
        """
        Prepare the post-editor and translation job for post-editing.
        
        Args:
            session: Database session
            job_id: Translation job ID
            api_key: API key for the model
            model_name: Name of the model to use for post-editing
            
        Returns:
            Tuple of (post_editor, translation_document, translated_path)
            
        Raises:
            ValueError: If job not found or translation segments invalid
            FileNotFoundError: If translated file not found
        """
        repository = self._get_repository(session)
        job = repository.get(job_id)
        
        if not job:
            raise ValueError(f"Translation job {job_id} not found")
        
        # Get the translated file path
        translated_path = self._get_translated_file_path(job)
        
        if not self._file_manager.file_exists(translated_path):
            raise FileNotFoundError(f"Translated file not found: {translated_path}")
        
        # Initialize post-editor with the model API
        from backend.domains.shared.model_factory import ModelAPIFactory
        model_factory = ModelAPIFactory()
        model_api = model_factory.create(api_key, model_name)
        post_editor = PostEditEngine(model_api)
        
        # Create translation document for post-editing
        translation_document = TranslationDocument(
            job.filepath,
            original_filename=job.filename,
            target_segment_size=job.segment_size
        )
        
        # Use stored translation segments from DB for exact alignment
        db_segments = getattr(job, 'translation_segments', None)
        if not db_segments or not isinstance(db_segments, list):
            raise ValueError(
                "Translation segments not found for this job. "
                "Post-editing requires saved segments."
            )
        
        # Extract translated_text list from DB segments
        if db_segments and isinstance(db_segments[0], dict):
            translated_list = [
                seg.get('translated_text')
                for seg in db_segments
                if isinstance(seg, dict)
            ]
        else:
            # Legacy format: list of plain strings
            translated_list = [seg for seg in db_segments if isinstance(seg, str)]
        
        # Validate extracted list
        if not translated_list or any(t is None for t in translated_list):
            raise ValueError(
                "Invalid translation segments schema. "
                "Expected 'translated_text' per segment."
            )
        
        translation_document.translated_segments = translated_list[:]
        
        # Strict count match with source segments
        if len(translation_document.translated_segments) != len(translation_document.segments):
            raise ValueError(
                f"Translation segments count mismatch "
                f"(source={len(translation_document.segments)}, "
                f"translated={len(translation_document.translated_segments)})."
            )
        
        return post_editor, translation_document, translated_path
    
    def run_post_edit(
        self,
        post_editor: PostEditEngine,
        translation_document: TranslationDocument,
        translated_path: str,
        validation_report_path: str,
        selected_cases: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[int], None]] = None,
        job_id: Optional[int] = None
    ) -> List[str]:
        """
        Run the post-editing process and overwrite the translated file.
        
        Args:
            post_editor: PostEditEngine instance
            translation_document: Document to post-edit
            translated_path: Path to the translated file
            validation_report_path: Path to the validation report
            selected_cases: Optional specific validation cases to address
            progress_callback: Optional callback for progress updates
            job_id: Optional job ID for logging
            
        Returns:
            List of edited segments
            
        Raises:
            IOError: If unable to write the edited file
        """
        # Run the post-editing process
        edited_segments = post_editor.post_edit_document(
            translation_document,
            validation_report_path,
            selected_cases,
            progress_callback=progress_callback,
            job_id=job_id
        )
        
        # Overwrite the translated file with the edited content
        try:
            edited_content = '\n'.join(edited_segments)
            self._file_manager.write_file(translated_path, edited_content)
            print(f"--- [POST-EDIT] Successfully updated translated file: {translated_path} ---")
        except IOError as e:
            print(f"--- [POST-EDIT] Error writing to translated file: {e} ---")
            raise e
        
        return edited_segments
    
    def get_post_edit_log_path(self, job: TranslationJob) -> str:
        """
        Get the post-edit log file path.
        
        Args:
            job: Translation job
            
        Returns:
            Path to the post-edit log file
        """
        # Use FileManager's standardized path for consistency
        return self._file_manager.get_post_edit_log_path(job)
    
    def update_job_post_edit_status(
        self,
        session: Session,
        job_id: int,
        status: str,
        progress: Optional[int] = None,
        log_path: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update the job's post-edit status in the database.
        
        Args:
            session: Database session
            job_id: Translation job ID
            status: New post-edit status
            progress: Optional progress percentage (0-100)
            log_path: Optional path to post-edit log
            error_message: Optional error message for failed post-edits
        """
        repository = self._get_repository(session)
        
        # Update post-edit status using repository
        repository.update_post_edit_status(
            job_id,
            status,
            progress=progress,
            log_path=log_path
        )
        
        # Emit appropriate domain event
        if self._uow:
            if status == "processing":
                event = DomainEvent(
                    event_type=EventType.POST_EDIT_STARTED,
                    aggregate_id=job_id,
                    aggregate_type="TranslationJob",
                    payload={"job_id": job_id}
                )
                self._uow.collect_event(event)
            
            elif status == "completed":
                event = DomainEvent(
                    event_type=EventType.POST_EDIT_COMPLETED,
                    aggregate_id=job_id,
                    aggregate_type="TranslationJob",
                    payload={
                        "job_id": job_id,
                        "log_path": log_path
                    }
                )
                self._uow.collect_event(event)
            
            elif status == "failed":
                event = DomainEvent(
                    event_type=EventType.POST_EDIT_FAILED,
                    aggregate_id=job_id,
                    aggregate_type="TranslationJob",
                    payload={
                        "job_id": job_id,
                        "error_message": error_message
                    }
                )
                self._uow.collect_event(event)
    
    async def post_edit_translation(
        self,
        session: Session,
        job_id: int,
        api_key: str,
        model_name: str = "gemini-2.0-flash-exp",
        selected_cases: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> Dict[str, Any]:
        """
        Complete post-editing workflow for a translation job.
        
        This is the main entry point that orchestrates the entire post-editing process.
        
        Args:
            session: Database session
            job_id: Translation job ID
            api_key: API key for the model
            model_name: Model to use for post-editing
            selected_cases: Optional specific validation cases to address
            progress_callback: Optional progress callback
            
        Returns:
            Post-edit result dictionary with status and log path
            
        Raises:
            ValueError: If job not found or prerequisites not met
            FileNotFoundError: If required files not found
        """
        # Validate prerequisites
        job = self.validate_prerequisites(session, job_id)
        
        # Start post-editing
        self.update_job_post_edit_status(
            session, job_id, "processing", progress=0
        )
        
        try:
            # Prepare post-edit
            post_editor, translation_document, translated_path = self.prepare_post_edit(
                session, job_id, api_key, model_name
            )
            
            # Run post-edit
            edited_segments = self.run_post_edit(
                post_editor,
                translation_document,
                translated_path,
                job.validation_report_path,
                selected_cases,
                progress_callback,
                job_id
            )
            
            # Get the log path
            log_path = self.get_post_edit_log_path(job)
            
            # Update status to completed
            self.update_job_post_edit_status(
                session, job_id, "completed",
                progress=100,
                log_path=log_path
            )
            
            return {
                "status": "completed",
                "log_path": log_path,
                "edited_segments_count": len(edited_segments),
                "completed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            # Update status to failed
            self.update_job_post_edit_status(
                session, job_id, "failed",
                error_message=str(e)
            )
            raise
    
    def _get_translated_file_path(self, job: TranslationJob) -> str:
        """Get the path to the translated file for a job."""
        # Use FileManager's method to get the correct translated file path
        file_path, _, _ = self._file_manager.get_translated_file_path(job)
        return file_path