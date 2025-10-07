"""
Export Domain Service

This service handles all export-related business logic including:
- File downloads
- PDF generation
- Log downloads
- Glossary exports
- Segment data exports
"""

import os
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session

from backend.domains.translation.models import TranslationJob
from backend.domains.translation.repository import SqlAlchemyTranslationJobRepository
from backend.domains.user.models import User
from backend.domains.shared.service_base import DomainServiceBase
from backend.auth import is_admin

from .pdf_generator import generate_translation_pdf
from .schemas import (
    PDFExportRequest,
    DownloadRequest,
    LogDownloadRequest,
    GlossaryDownloadRequest,
    SegmentDownloadRequest,
    ContentDownloadRequest,
    ExportResponse,
    SegmentResponse,
    ContentResponse
)


class ExportDomainService(DomainServiceBase):
    """Service for handling export operations."""
    
    def __init__(self, db: Session):
        super().__init__()
        self.db = db
        self.repo = SqlAlchemyTranslationJobRepository(db)
    
    async def _check_job_access(self, job_id: int, user: User) -> TranslationJob:
        """
        Check if user has access to the job.
        
        Args:
            job_id: Job ID
            user: Current user
            
        Returns:
            TranslationJob if authorized
            
        Raises:
            ValueError: If job not found or access denied
        """
        db_job = self.repo.get(job_id)
        if db_job is None:
            self.raise_not_found("Job")
        
        # Check ownership
        if not db_job.owner or db_job.owner.clerk_user_id != user.clerk_user_id:
            user_is_admin = await is_admin(user)
            if not user_is_admin:
                self.raise_forbidden("Not authorized to access this job")
        
        return db_job
    
    async def download_job_output(
        self, 
        user: User, 
        job_id: int
    ) -> Tuple[str, str, str]:
        """
        Download the output of a translation job.
        
        Args:
            user: Current user
            job_id: Job ID
            
        Returns:
            Tuple of (file_path, filename, media_type)
            
        Raises:
            ValueError: If job not found, not authorized, or file not available
        """
        db_job = await self._check_job_access(job_id, user)
        
        if db_job.status not in ["COMPLETED", "FAILED"]:
            self.raise_validation_error(f"Translation is not completed yet. Current status: {db_job.status}")
        
        if not db_job.filepath:
            self.raise_not_found("Filepath for this job")
        
        file_path, user_translated_filename, media_type = self.file_manager.get_translated_file_path(
            db_job,
            prefer_epub=True
        )
        
        if not os.path.exists(file_path):
            self.raise_not_found(f"Translated file at path: {file_path}")
        
        return file_path, user_translated_filename, media_type
    
    async def download_job_log(
        self,
        user: User,
        job_id: int,
        log_type: str
    ) -> Tuple[str, str]:
        """
        Download log files for a translation job.
        
        Args:
            user: Current user
            job_id: Job ID
            log_type: Type of log ('prompts' or 'context')
            
        Returns:
            Tuple of (file_path, filename)
            
        Raises:
            ValueError: If job not found, not authorized, or log not available
        """
        db_job = await self._check_job_access(job_id, user)
        
        if log_type not in ["prompts", "context"]:
            self.raise_validation_error("Invalid log type. Must be 'prompts' or 'context'.")
        
        if log_type == "prompts":
            log_path = self.file_manager.get_job_prompt_log_path(job_id)
        else:  # context
            log_path = self.file_manager.get_job_context_log_path(job_id)
        
        log_filename = f"job_{job_id}_{log_type}.json"
        
        if not os.path.exists(log_path):
            self.raise_not_found(f"{log_type.capitalize()} log file")
        
        return log_path, log_filename
    
    async def get_job_glossary(
        self,
        user: User,
        job_id: int,
        structured: bool = False
    ) -> Dict[str, Any]:
        """
        Get the final glossary for a completed translation job.
        
        Args:
            user: Current user
            job_id: Job ID
            structured: If True, returns structured format
            
        Returns:
            Glossary data
            
        Raises:
            ValueError: If job not found, not authorized, or glossary not available
        """
        db_job = await self._check_job_access(job_id, user)
        
        if db_job.status != "COMPLETED":
            self.raise_validation_error(f"Glossary is available only for completed jobs. Current status: {db_job.status}")
        
        if not db_job.final_glossary:
            if structured:
                from backend.domains.analysis.schemas import GlossaryAnalysisResponse
                from core.schemas import TranslatedTerms
                return GlossaryAnalysisResponse(
                    glossary=[], 
                    translated_terms=TranslatedTerms(translations=[])
                ).model_dump()
            return {}
        
        # If structured response requested, parse and return GlossaryAnalysisResponse
        if structured:
            from core.schemas import TranslatedTerms, TranslatedTerm
            from backend.domains.analysis.schemas import GlossaryAnalysisResponse
            
            # Parse glossary based on format
            if isinstance(db_job.final_glossary, dict):
                if 'translations' in db_job.final_glossary:
                    # Already in TranslatedTerms format
                    translated_terms = TranslatedTerms(**db_job.final_glossary)
                else:
                    # Convert from dict format
                    translations = [
                        TranslatedTerm(source=k, korean=v)
                        for k, v in db_job.final_glossary.items()
                    ]
                    translated_terms = TranslatedTerms(translations=translations)
            else:
                # Return empty if format is unexpected
                translated_terms = TranslatedTerms(translations=[])
            
            return GlossaryAnalysisResponse(
                glossary=[{"term": t.source, "translation": t.korean} for t in translated_terms.translations],
                translated_terms=translated_terms
            ).model_dump()
        
        # Default: return raw glossary
        return db_job.final_glossary
    
    async def get_job_segments(
        self,
        user: User,
        job_id: int,
        offset: int = 0,
        limit: int = 3
    ) -> SegmentResponse:
        """
        Get the segmented translation data for a completed translation job.
        
        Args:
            user: Current user
            job_id: Job ID
            offset: Starting segment index
            limit: Number of segments to return
            
        Returns:
            SegmentResponse with segments and pagination info
            
        Raises:
            ValueError: If job not found, not authorized, or segments not available
        """
        db_job = await self._check_job_access(job_id, user)
        
        # Check if either translation is completed OR validation is completed (validation creates segments too)
        if db_job.status != "COMPLETED":
            # If translation not complete, check if validation is done (which also provides segments)
            if db_job.validation_status != "COMPLETED":
                self.raise_validation_error(f"Translation segments are available only for completed jobs or validated jobs. Job status: {db_job.status}, Validation status: {db_job.validation_status}")
        
        # Get segments from different sources based on availability
        segments = db_job.translation_segments
        
        # If no translation segments but validation is complete, extract from validation report
        if not segments and db_job.validation_status == "COMPLETED" and db_job.validation_report_path:
            import json
            try:
                with open(db_job.validation_report_path, 'r', encoding='utf-8') as f:
                    report = json.load(f)
                
                # Extract segments from validation report
                segments = []
                for result in report.get('detailed_results', []):
                    segment_data = {
                        "source_text": result.get('source_text', ''),
                        "translated_text": result.get('translated_text', ''),
                        "segment_index": result.get('segment_index', 0)
                    }
                    segments.append(segment_data)
            except Exception as e:
                self.logger.warning(f"Error reading validation report for segments: {e}")
                segments = []
        
        # Return empty segments if still not available
        if not segments:
            return SegmentResponse(
                segments=[],
                total_count=0,
                offset=offset,
                limit=limit,
                has_more=False
            )
        total_count = len(segments)
        
        # Apply pagination
        end_index = min(offset + limit, total_count)
        paginated_segments = segments[offset:end_index]
        
        has_more = end_index < total_count
        
        return SegmentResponse(
            segments=paginated_segments,
            total_count=total_count,
            offset=offset,
            limit=limit,
            has_more=has_more
        )
    
    async def get_job_content(
        self,
        user: User,
        job_id: int,
        include_source: bool = True
    ) -> ContentResponse:
        """
        Get the raw translation content for a job.
        
        Args:
            user: Current user
            job_id: Job ID
            include_source: Whether to include source content
            
        Returns:
            ContentResponse with job content
            
        Raises:
            ValueError: If job not found, not authorized, or content not available
        """
        db_job = await self._check_job_access(job_id, user)
        
        # Check if either translation is completed OR validation is completed
        if db_job.status != "COMPLETED":
            # If translation not complete, check if validation is done (which also provides content)
            if db_job.validation_status != "COMPLETED":
                self.raise_validation_error(f"Translation content is available only for completed jobs or validated jobs. Job status: {db_job.status}, Validation status: {db_job.validation_status}")
        
        # Determine which file to return based on what's available
        file_path = None
        content = None
        
        # Check if we have a translation file (post-edit overwrites the original, so we use the same path)
        if db_job.filepath:
            file_path, _, _ = self.file_manager.get_translated_file_path(
                db_job,
                prefer_epub=True
            )
            if not os.path.exists(file_path):
                # If translated file doesn't exist but validation is complete, we can extract from validation report
                if db_job.validation_status != "COMPLETED" or not db_job.validation_report_path:
                    self.raise_not_found("Translated file")
                file_path = None  # Will extract from validation report
        elif db_job.validation_status == "COMPLETED" and db_job.validation_report_path:
            # For validation-only case, we need to extract content from validation report
            file_path = None  # Will handle below
        else:
            self.raise_not_found("Content file for this job")
        
        # Handle validation report case specially - extract translated content from report
        if file_path is None and db_job.validation_status == "COMPLETED" and db_job.validation_report_path:
            import json
            try:
                with open(db_job.validation_report_path, 'r', encoding='utf-8') as f:
                    report = json.load(f)
                
                # Extract translated segments from validation report
                translated_segments = []
                for result in report.get('detailed_results', []):
                    translated_text = result.get('translated_text', '')
                    if translated_text:
                        translated_segments.append(translated_text)
                
                content = '\n'.join(translated_segments) if translated_segments else ""
                if not content:
                    self.raise_not_found("Translated content in validation report")
            except Exception as e:
                self.logger.error(f"Error reading validation report: {e}")
                self.raise_server_error("Error extracting content from validation report")
        else:
            # Regular file reading
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                self.raise_server_error(f"Error reading file: {str(e)}")
        
        # Try to read the original source file
        source_content = None
        if include_source and db_job.filepath and os.path.exists(db_job.filepath):
            try:
                # Parse the original file to get the text content
                from core.utils.file_parser import parse_document
                source_content = parse_document(db_job.filepath)
            except Exception as e:
                # Log error but don't fail the whole request
                self.logger.warning(f"Error reading source file: {e}")
        
        return ContentResponse(
            job_id=job_id,
            filename=db_job.filename,
            content=content,
            source_content=source_content,
            completed_at=db_job.completed_at.isoformat() if db_job.completed_at else None
        )
    
    async def generate_pdf(
        self,
        user: User,
        request: PDFExportRequest
    ) -> bytes:
        """
        Generate PDF for a translation job.
        
        Args:
            user: Current user
            request: PDF export request
            
        Returns:
            PDF bytes
            
        Raises:
            ValueError: If job not found, not authorized, or PDF generation fails
        """
        db_job = await self._check_job_access(request.job_id, user)
        
        # Check if job is completed
        if db_job.status != "COMPLETED":
            self.raise_validation_error(f"PDF generation is available only for completed jobs. Current status: {db_job.status}")
        
        try:
            # Generate PDF
            pdf_bytes = generate_translation_pdf(
                job_id=request.job_id,
                db=self.db,
                include_source=request.include_source,
                include_illustrations=request.include_illustrations,
                page_size=request.page_size,
                illustration_position=request.illustration_position
            )
            return pdf_bytes
            
        except ValueError as e:
            self.raise_validation_error(str(e))
        except Exception as e:
            self.logger.error(f"Error generating PDF for job {request.job_id}: {e}")
            self.raise_server_error(f"Error generating PDF: {str(e)}")
    
    def get_pdf_filename(self, job_id: int) -> str:
        """Get the PDF filename for a job."""
        db_job = self.repo.get(job_id)
        if not db_job:
            self.raise_not_found("Job")
        
        base_filename = db_job.filename.rsplit('.', 1)[0] if '.' in db_job.filename else db_job.filename
        return f"{base_filename}_translation.pdf"

    def get_glossary_filename(self, job_id: int) -> str:
        """Get the glossary filename for a job."""
        db_job = self.repo.get(job_id)
        if not db_job:
            self.raise_not_found("Job")
        base_filename = db_job.filename.rsplit('.', 1)[0] if '.' in db_job.filename else db_job.filename
        return f"{base_filename}_glossary.json"

    async def update_job_glossary(
        self,
        user: User,
        job_id: int,
        glossary_json: str,
        *,
        mode: str = "merge",
        structured: bool = False,
    ) -> Dict[str, Any]:
        """
        Update a job's final glossary by merging or replacing with provided JSON.

        Args:
            user: Current user
            job_id: Job ID
            glossary_json: New glossary payload (supports multiple formats)
            mode: 'merge' (default) or 'replace'
            structured: If True, returns structured response

        Returns:
            Updated glossary (structured or raw dict)
        """
        db_job = await self._check_job_access(job_id, user)

        # Only allow updates when translation completed or failed (to tweak terms)
        if db_job.status not in ["COMPLETED", "FAILED"]:
            self.raise_validation_error(
                f"Glossary can be updated only after translation completes or fails. Current status: {db_job.status}"
            )

        # Parse incoming glossary using analysis utility (accepts flexible formats)
        from backend.domains.analysis.glossary_analysis import GlossaryAnalysis
        parser = GlossaryAnalysis()
        try:
            new_glossary_dict: Dict[str, str] = parser._process_user_glossary(glossary_json)
        except Exception as e:
            self.raise_validation_error(f"Invalid glossary payload: {e}")

        # Normalize existing glossary to simple dict[str, str]
        existing_dict: Dict[str, str] = {}
        if db_job.final_glossary:
            if isinstance(db_job.final_glossary, dict) and 'translations' in db_job.final_glossary:
                from core.schemas import TranslatedTerms
                try:
                    tt = TranslatedTerms(**db_job.final_glossary)
                    existing_dict = {t.source: t.korean for t in tt.translations}
                except Exception:
                    # Fallback: ignore malformed structured data
                    existing_dict = {}
            elif isinstance(db_job.final_glossary, dict):
                existing_dict = {str(k): str(v) for k, v in db_job.final_glossary.items()}

        # Merge or replace
        merged_dict: Dict[str, str]
        if (mode or "merge").lower() == "replace":
            merged_dict = new_glossary_dict
        else:
            merged_dict = parser.merge_glossaries(existing_dict, new_glossary_dict, prefer_new=True)

        # Store as structured TranslatedTerms for new pipeline
        from core.schemas import TranslatedTerm, TranslatedTerms
        structured_terms = TranslatedTerms(
            translations=[TranslatedTerm(source=k, korean=v) for k, v in merged_dict.items()]
        )
        db_job.final_glossary = structured_terms.model_dump()
        self.db.commit()

        if structured:
            # Build structured response compatible with analysis response
            from backend.domains.analysis.schemas import GlossaryAnalysisResponse
            return GlossaryAnalysisResponse(
                glossary=[{"term": k, "translation": v} for k, v in merged_dict.items()],
                translated_terms=structured_terms,
            ).model_dump()
        # Raw dict
        return merged_dict
