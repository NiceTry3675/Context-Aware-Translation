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
from core.utils.document_io import DocumentOutputManager
from backend.domains.translation.storage_adapter import create_storage_handler
from shared.utils.logging import get_logger
from backend.domains.translation.models import TranslationJob
from backend.domains.translation.repository import TranslationJobRepository, SqlAlchemyTranslationJobRepository
from backend.domains.shared.provider_context import ProviderContext
from backend.domains.shared.service_base import DomainServiceBase
from backend.domains.shared.uow import SqlAlchemyUoW
from backend.domains.shared.events import DomainEvent, EventType
from backend.config.settings import get_settings


class PostEditDomainService(DomainServiceBase):
    """Service layer for post-editing operations using domain patterns."""
    
    def __init__(
        self,
        session_factory=None,
        repository: Optional[TranslationJobRepository] = None,
        uow: Optional[SqlAlchemyUoW] = None,
        storage=None
    ):
        """
        Initialize post-edit service with dependencies.
        
        Args:
            session_factory: Database session factory for creating sessions
            repository: TranslationJob repository (optional, creates default if not provided)
            uow: Unit of Work for transaction management (optional)
            storage: Storage abstraction for file operations
        """
        super().__init__(session_factory=session_factory, repository=repository, uow=uow, storage=storage)
    
    def _get_repository(self, session: Session) -> TranslationJobRepository:
        """Get or create repository instance."""
        return self.get_or_create_repository(session, SqlAlchemyTranslationJobRepository)
    
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
            self.raise_not_found(f"Translation job {job_id}")
        
        if job.validation_status != "COMPLETED":
            self.raise_validation_error("Validation must be completed before post-editing")
        
        if not job.validation_report_path:
            self.raise_validation_error("Validation report not found")
        
        if not self.file_manager.file_exists(job.validation_report_path):
            raise FileNotFoundError(
                f"Validation report file not found: {job.validation_report_path}"
            )
        
        return job
    
    def prepare_post_edit(
        self,
        session: Session,
        job_id: int,
        api_key: Optional[str],
        model_name: str = "gemini-flash-lite-latest",
        provider_context: Optional[ProviderContext] = None,
        *,
        backup_api_keys: list[str] | None = None,
        requests_per_minute: int | None = None,
    ) -> Tuple[PostEditEngine, TranslationDocument, str, Any, Any]:
        """
        Prepare the post-editor and translation job for post-editing.
        
        Args:
            session: Database session
            job_id: Translation job ID
            api_key: API key for the model
            model_name: Name of the model to use for post-editing
            
        Returns:
            Tuple of (post_editor, translation_document, translated_path, segment_logger)

        Raises:
            ValueError: If job not found or translation segments invalid
            FileNotFoundError: If translated file not found
        """
        repository = self._get_repository(session)
        job = repository.get(job_id)
        
        if not job:
            self.raise_not_found(f"Translation job {job_id}")
        
        # Get the translated file path
        translated_path = self._get_translated_file_path(job)
        
        if not self.file_manager.file_exists(translated_path):
            raise FileNotFoundError(f"Translated file not found: {translated_path}")
        
        # Create a logger for segment I/O
        segment_logger = get_logger(
            job_id=job_id,
            filename=job.filename,
            task_type="post_edit"
        )
        segment_logger.initialize_session()

        # Initialize post-editor with the model API and logger
        from core.translation.usage_tracker import TokenUsageCollector
        usage_collector = TokenUsageCollector()
        model_api = self.validate_and_create_model(
            api_key,
            model_name,
            provider_context=provider_context,
            usage_callback=usage_collector.record_event,
            backup_api_keys=backup_api_keys,
            requests_per_minute=requests_per_minute,
        )
        post_editor = PostEditEngine(model_api, logger=segment_logger)
        
        # Create translation document for post-editing
        translation_document = TranslationDocument(
            job.filepath,
            original_filename=job.filename,
            target_segment_size=job.segment_size,
            job_id=job.id
        )
        
        # Use stored translation segments from DB for exact alignment
        db_segments = getattr(job, 'translation_segments', None)
        if not db_segments or not isinstance(db_segments, list):
            self.raise_validation_error(
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
            self.raise_validation_error(
                "Invalid translation segments schema. "
                "Expected 'translated_text' per segment."
            )
        
        translation_document.translated_segments = translated_list[:]
        
        # Strict count match with source segments
        if len(translation_document.translated_segments) != len(translation_document.segments):
            self.raise_validation_error(
                f"Translation segments count mismatch "
                f"(source={len(translation_document.segments)}, "
                f"translated={len(translation_document.translated_segments)})."
            )
        
        return post_editor, translation_document, translated_path, segment_logger, usage_collector
    
    def run_post_edit(
        self,
        post_editor: PostEditEngine,
        translation_document: TranslationDocument,
        translated_path: str,
        validation_report_path: str,
        selected_cases: Optional[Dict[str, Any]] = None,
        modified_cases: Optional[Dict[str, Any]] = None,
        default_select_all: bool = True,
        progress_callback: Optional[Callable[[int], None]] = None,
        job_id: Optional[int] = None,
        job_filename: Optional[str] = None,
        segment_logger=None
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
            job_id: Optional job ID used for persistence hooks
            job_filename: Optional original filename for storage synchronization
            
        Returns:
            List of edited segments
            
        Raises:
            IOError: If unable to write the edited file
        """
        # Normalize possible string keys from JSON to int indices
        def _normalize_index_dict(d: Optional[Dict[str, Any]]) -> Optional[Dict[int, Any]]:
            if not isinstance(d, dict):
                return None
            out: Dict[int, Any] = {}
            for k, v in d.items():
                try:
                    out[int(k)] = v
                except (ValueError, TypeError):
                    continue
            return out

        normalized_selected = _normalize_index_dict(selected_cases) or selected_cases
        normalized_modified = _normalize_index_dict(modified_cases) or modified_cases

        # Run the post-editing process
        # Normalize selection into explicit boolean masks per segment based on the report
        effective_selected = self._normalize_selected_cases_from_report(
            validation_report_path,
            normalized_selected,
            default_select_all
        )

        edited_segments = post_editor.post_edit_document(
            translation_document,
            validation_report_path,
            effective_selected,
            normalized_modified,
            progress_callback=progress_callback,
            job_id=job_id
        )
        
        # Persist the edited content with legacy TXT compatibility
        edited_content = '\n\n'.join(edited_segments)

        if job_id and job_filename:
            try:
                storage_handler = create_storage_handler()
                saved_paths = storage_handler(
                    job_id=job_id,
                    content=edited_content,
                    original_filename=job_filename
                )
                if saved_paths:
                    print(
                        "--- [POST-EDIT] Storage artifacts refreshed: "
                        f"{', '.join(saved_paths)} ---"
                    )
            except Exception as exc:
                print(f"--- [POST-EDIT] Storage handler failed: {exc} ---")

        try:
            self.file_manager.write_file(translated_path, edited_content)
            print(f"--- [POST-EDIT] Successfully updated translated file: {translated_path} ---")
        except IOError as e:
            print(f"--- [POST-EDIT] Error writing to translated file: {e} ---")
            raise e

        # Keep the in-memory document aligned with the edited output
        translation_document.translated_segments = edited_segments[:]

        # Regenerate EPUB artifacts when the original input was an EPUB
        data_model = translation_document.get_data_model()
        if data_model.input_format == '.epub':
            epub_targets = []
            if data_model.output_filename:
                epub_targets.append(data_model.output_filename)
            if data_model.job_output_filename:
                epub_targets.append(data_model.job_output_filename)

            for epub_path in epub_targets:
                try:
                    DocumentOutputManager.save_epub_output(
                        data_model.filepath,
                        edited_segments,
                        epub_path,
                        data_model.style_map
                    )
                    print(f"--- [POST-EDIT] EPUB artifact refreshed: {epub_path} ---")
                except Exception as exc:
                    print(f"--- [POST-EDIT] Failed to update EPUB artifact at {epub_path}: {exc} ---")

        # Log completion if logger is available
        if segment_logger:
            segment_logger.log_completion(
                total_segments=len(edited_segments),
                total_time=None
            )

        return edited_segments

    def _normalize_selected_cases_from_report(
        self,
        report_path: str,
        selected_cases: Optional[Dict[int, Any]],
        default_select_all: bool
    ) -> Optional[Dict[int, List[bool]]]:
        """
        Normalize selection to explicit boolean masks per segment index.

        - If a segment has no cases, it is excluded (not returned).
        - If selected_cases is None: all cases selected when default_select_all=True, else all False.
        - Accepts list[bool] or dict[int|str,bool] per segment.
        """
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                report = json.load(f)
        except Exception:
            # If report cannot be loaded, fall back to original selected_cases behavior
            return selected_cases  # type: ignore

        detailed = report.get('detailed_results', []) or []
        if not detailed:
            return None

        # Build a map: seg_idx -> case_count
        seg_case_counts: Dict[int, int] = {}
        for res in detailed:
            try:
                seg_idx = int(res.get('segment_index'))
            except Exception:
                continue
            cases = res.get('structured_cases') or []
            if cases:
                seg_case_counts[seg_idx] = len(cases)

        if not seg_case_counts:
            return None

        effective: Dict[int, List[bool]] = {}

        for seg_idx, count in seg_case_counts.items():
            # Start with default mask per policy
            base = [True if default_select_all else False for _ in range(count)]

            if isinstance(selected_cases, dict) and seg_idx in selected_cases:
                value = selected_cases.get(seg_idx)
                if isinstance(value, list):
                    # Copy values within bounds, fill rest with base
                    for i in range(min(count, len(value))):
                        base[i] = bool(value[i])
                elif isinstance(value, dict):
                    # Accept sparse dict mask
                    # Normalize possible string keys
                    for k, v in value.items():
                        try:
                            idx = int(k)
                        except (ValueError, TypeError):
                            continue
                        if 0 <= idx < count:
                            base[idx] = bool(v)
                # else: ignore unknown types, keep base

            # If all False, we still keep mask; engine will exclude this segment.
            # If all True and default_select_all True, it's equivalent to selecting all.
            effective[seg_idx] = base

        return effective
    
    def get_post_edit_log_path(self, job: TranslationJob) -> str:
        """
        Get the post-edit log file path.
        
        Args:
            job: Translation job
            
        Returns:
            Path to the post-edit log file
        """
        # Use FileManager's standardized path for consistency
        return self.file_manager.get_post_edit_log_path(job)
    
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
        model_name: str = "gemini-flash-lite-latest",
        selected_cases: Optional[Dict[str, Any]] = None,
        modified_cases: Optional[Dict[str, Any]] = None,
        default_select_all: bool = True,
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
            modified_cases: Optional overrides for reason/recommend_korean_sentence per case
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
            post_editor, translation_document, translated_path, segment_logger, usage_collector = self.prepare_post_edit(
                session, job_id, api_key, model_name
            )
            
            # Run post-edit
            edited_segments = self.run_post_edit(
                post_editor,
                translation_document,
                translated_path,
                job.validation_report_path,
                selected_cases,
                modified_cases,
                default_select_all,
                progress_callback,
                job_id,
                job.filename
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
        file_path, _, _ = self.file_manager.get_translated_file_path(job)
        return file_path
