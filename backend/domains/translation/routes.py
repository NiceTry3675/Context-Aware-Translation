"""
Translation domain routes with business logic.

This module contains the core business logic for translation operations,
separated from the API routing layer.
"""

import os
import re
import shutil
import json
import logging
from typing import List, Optional

from fastapi import HTTPException, UploadFile, File, Form, Response, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ...domains.shared.base import ModelAPIFactory
from ...domains.shared.utils import FileManager
from ...domains.shared import schemas
from ...tasks.translation import process_translation_task
from ...tasks.validation import process_validation_task
from backend.domains.translation.models import TranslationJob
from backend.domains.user.models import User
from .repository import SqlAlchemyTranslationJobRepository
from .service import TranslationDomainService
from .schemas import (
    PostEditRequest,
    StructuredPostEditLog
)
from ...auth import is_admin


class TranslationRoutes:
    """Business logic for translation-related operations."""
    
    @staticmethod
    def list_jobs(
        db: Session,
        user: User,
        skip: int = 0,
        limit: int = 100
    ) -> List[TranslationJob]:
        """
        List all translation jobs for a user.
        
        Args:
            db: Database session
            user: Current user
            skip: Number of jobs to skip
            limit: Maximum number of jobs to return
            
        Returns:
            List of translation jobs
        """
        repo = SqlAlchemyTranslationJobRepository(db)
        
        # For now, use list_by_user with limit
        # TODO: Add skip support to repository
        jobs = repo.list_by_user(user.id, limit=limit)
        
        # Apply skip manually for now
        if skip > 0:
            jobs = jobs[skip:]
        
        return jobs
    
    @staticmethod
    async def create_job(
        db: Session,
        user: User,
        file: UploadFile,
        api_key: str,
        model_name: str = "gemini-2.5-flash-lite",
        translation_model_name: Optional[str] = None,
        style_model_name: Optional[str] = None,
        glossary_model_name: Optional[str] = None,
        style_data: Optional[str] = None,
        glossary_data: Optional[str] = None,
        segment_size: int = 15000
    ) -> TranslationJob:
        """
        Create a new translation job.
        
        Args:
            db: Database session
            user: Current user
            file: Uploaded file
            api_key: API key for translation service
            model_name: Default model name
            translation_model_name: Optional override for translation model
            style_model_name: Optional override for style model
            glossary_model_name: Optional override for glossary model
            style_data: Optional style data
            glossary_data: Optional glossary data
            segment_size: Segment size for translation
            
        Returns:
            Created translation job
            
        Raises:
            HTTPException: If API key is invalid or file save fails
        """
        # Validate API key
        if not ModelAPIFactory.validate_api_key(api_key, model_name):
            raise HTTPException(status_code=400, detail="Invalid API Key or unsupported model.")
        
        # Create job using domain service
        service = TranslationDomainService(lambda: db)
        job_with_id = service.create_translation_job(
            filename=file.filename,
            owner_id=user.id,
            segment_size=segment_size
        )
        
        # Fetch the complete job using the ID
        repo = SqlAlchemyTranslationJobRepository(db)
        job = repo.get(job_with_id.id)
        
        # Save uploaded file
        sanitized_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', file.filename)
        unique_filename = f"{job.id}_{sanitized_filename}"
        file_path = f"uploads/{unique_filename}"
        
        os.makedirs("uploads", exist_ok=True)
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            # Update job status to failed
            repo = SqlAlchemyTranslationJobRepository(db)
            repo.set_status(job.id, "FAILED", error=f"Failed to save file: {e}")
            db.commit()
            raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
        
        # Update job with file path
        repo = SqlAlchemyTranslationJobRepository(db)
        job.filepath = file_path
        db.commit()
        
        # Start translation in background using Celery
        process_translation_task.delay(
            job_id=job.id,
            api_key=api_key,
            model_name=model_name,
            style_data=style_data,
            glossary_data=glossary_data,
            translation_model_name=translation_model_name,
            style_model_name=style_model_name,
            glossary_model_name=glossary_model_name,
            user_id=user.id
        )
        
        return job
    
    @staticmethod
    def get_job(
        db: Session,
        job_id: int
    ) -> TranslationJob:
        """
        Get a translation job by ID.
        
        Args:
            db: Database session
            job_id: Job ID
            
        Returns:
            Translation job
            
        Raises:
            HTTPException: If job not found
        """
        repo = SqlAlchemyTranslationJobRepository(db)
        job = repo.get(job_id)
        
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return job
    
    @staticmethod
    async def delete_job(
        db: Session,
        user: User,
        job_id: int
    ) -> None:
        """
        Delete a translation job and its associated files.
        
        Args:
            db: Database session
            user: Current user
            job_id: Job ID
            
        Raises:
            HTTPException: If job not found or user not authorized
        """
        repo = SqlAlchemyTranslationJobRepository(db)
        job = repo.get(job_id)
        
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check ownership or admin role
        user_is_admin = await is_admin(user)
        if not job.owner or (job.owner.clerk_user_id != user.clerk_user_id and not user_is_admin):
            raise HTTPException(status_code=403, detail="Not authorized to delete this job")
        
        # Delete associated files
        try:
            file_manager = FileManager()
            file_manager.delete_job_files(job)
        except Exception as e:
            # Log the error but proceed with deleting the DB record
            print(f"Error deleting files for job {job_id}: {e}")
        
        # Delete the job from the database
        repo.delete(job.id)
        db.commit()
    
    # Download and content methods
    @staticmethod
    async def download_job_output(
        db: Session,
        user: User,
        job_id: int
    ):
        """
        Download the output of a translation job.
        
        Args:
            db: Database session
            user: Current user
            job_id: Job ID
            
        Returns:
            FileResponse with the translated file
            
        Raises:
            HTTPException: If job not found, not authorized, or file not available
        """
        repo = SqlAlchemyTranslationJobRepository(db)
        db_job = repo.get(job_id)
        if db_job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check ownership
        if not db_job.owner or db_job.owner.clerk_user_id != user.clerk_user_id:
            user_is_admin = await is_admin(user)
            if not user_is_admin:
                raise HTTPException(status_code=403, detail="Not authorized to download this file")
        
        if db_job.status not in ["COMPLETED", "FAILED"]:
            raise HTTPException(status_code=400, detail=f"Translation is not completed yet. Current status: {db_job.status}")
        
        if not db_job.filepath:
            raise HTTPException(status_code=404, detail="Filepath not found for this job.")
        
        file_manager = FileManager()
        file_path, user_translated_filename, media_type = file_manager.get_translated_file_path(db_job)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"Translated file not found at path: {file_path}")
        
        return FileResponse(path=file_path, filename=user_translated_filename, media_type=media_type)
    
    @staticmethod
    async def download_job_log(
        db: Session,
        user: User,
        job_id: int,
        log_type: str
    ):
        """
        Download log files for a translation job.
        
        Args:
            db: Database session
            user: Current user
            job_id: Job ID
            log_type: Type of log ('prompts' or 'context')
            
        Returns:
            FileResponse with the log file
            
        Raises:
            HTTPException: If job not found, not authorized, or log not available
        """
        repo = SqlAlchemyTranslationJobRepository(db)
        db_job = repo.get(job_id)
        if db_job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check ownership
        if not db_job.owner or db_job.owner.clerk_user_id != user.clerk_user_id:
            user_is_admin = await is_admin(user)
            if not user_is_admin:
                raise HTTPException(status_code=403, detail="Not authorized to download logs for this file")
        
        if log_type not in ["prompts", "context"]:
            raise HTTPException(status_code=400, detail="Invalid log type. Must be 'prompts' or 'context'.")
        
        base, _ = os.path.splitext(db_job.filename)
        log_dir = "logs/debug_prompts" if log_type == "prompts" else "logs/context_log"
        log_filename = f"{log_type}_job_{job_id}_{base}.txt"
        log_path = os.path.join(log_dir, log_filename)
        
        if not os.path.exists(log_path):
            raise HTTPException(status_code=404, detail=f"{log_type.capitalize()} log file not found.")
        
        return FileResponse(path=log_path, filename=log_filename, media_type="text/plain")
    
    @staticmethod
    async def get_job_glossary(
        db: Session,
        user: User,
        job_id: int,
        structured: bool = False
    ):
        """
        Get the final glossary for a completed translation job.
        
        Args:
            db: Database session
            user: Current user
            job_id: Job ID
            structured: If True, returns a GlossaryAnalysisResponse
            
        Returns:
            Either raw glossary dict or GlossaryAnalysisResponse
            
        Raises:
            HTTPException: If job not found, not authorized, or glossary not available
        """
        repo = SqlAlchemyTranslationJobRepository(db)
        db_job = repo.get(job_id)
        if db_job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check ownership or admin role
        user_is_admin = await is_admin(user)
        if not db_job.owner or (db_job.owner.clerk_user_id != user.clerk_user_id and not user_is_admin):
            raise HTTPException(status_code=403, detail="Not authorized to access this glossary")
        
        if db_job.status != "COMPLETED":
            raise HTTPException(status_code=400, detail=f"Glossary is available only for completed jobs. Current status: {db_job.status}")
        
        if not db_job.final_glossary:
            if structured:
                return schemas.GlossaryAnalysisResponse(glossary=[], translated_terms=schemas.TranslatedTerms(translations=[]))
            return {}
        
        # If structured response requested, parse and return GlossaryAnalysisResponse
        if structured:
            from core.schemas import TranslatedTerms, TranslatedTerm
            
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
            
            return schemas.GlossaryAnalysisResponse(
                glossary=translated_terms.translations,
                translated_terms=translated_terms
            )
        
        # Default: return raw glossary
        return db_job.final_glossary
    
    @staticmethod
    async def get_job_segments(
        db: Session,
        user: User,
        job_id: int,
        offset: int = 0,
        limit: int = 3
    ):
        """
        Get the segmented translation data for a completed translation job.
        
        Args:
            db: Database session
            user: Current user
            job_id: Job ID
            offset: Starting segment index
            limit: Number of segments to return
            
        Returns:
            Dict with segments and pagination info
            
        Raises:
            HTTPException: If job not found, not authorized, or segments not available
        """
        repo = SqlAlchemyTranslationJobRepository(db)
        db_job = repo.get(job_id)
        if db_job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check ownership
        if not db_job.owner or db_job.owner.clerk_user_id != user.clerk_user_id:
            user_is_admin = await is_admin(user)
            if not user_is_admin:
                raise HTTPException(status_code=403, detail="Not authorized to access this content")
        
        # Check if either translation is completed OR validation is completed (validation creates segments too)
        if db_job.status != "COMPLETED":
            # If translation not complete, check if validation is done (which also provides segments)
            if db_job.validation_status != "COMPLETED":
                raise HTTPException(status_code=400, detail=f"Translation segments are available only for completed jobs or validated jobs. Job status: {db_job.status}, Validation status: {db_job.validation_status}")
        
        # Get segments from different sources based on availability
        segments = db_job.translation_segments
        
        # If no translation segments but validation is complete, extract from validation report
        if not segments and db_job.validation_status == "COMPLETED" and db_job.validation_report_path:
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
                print(f"Error reading validation report for segments: {e}")
                segments = []
        
        # Return empty segments if still not available
        if not segments:
            return {
                "job_id": job_id,
                "filename": db_job.filename,
                "segments": [],
                "total_segments": 0,
                "has_more": False,
                "offset": offset,
                "limit": limit,
                "completed_at": db_job.completed_at.isoformat() if db_job.completed_at else None,
                "message": "No segments available for this job."
            }
        
        # Get total segments
        total_segments = len(segments)
        
        # Apply pagination
        end_index = min(offset + limit, total_segments)
        paginated_segments = segments[offset:end_index]
        
        # Return paginated segments as JSON
        return {
            "job_id": job_id,
            "filename": db_job.filename,
            "segments": paginated_segments,
            "total_segments": total_segments,
            "has_more": end_index < total_segments,
            "offset": offset,
            "limit": limit,
            "completed_at": db_job.completed_at.isoformat() if db_job.completed_at else None
        }
    
    @staticmethod
    async def get_job_content(
        db: Session,
        user: User,
        job_id: int
    ):
        """
        Get the translated content as text for a completed translation job.
        
        Args:
            db: Database session
            user: Current user
            job_id: Job ID
            
        Returns:
            Dict with content and metadata
            
        Raises:
            HTTPException: If job not found, not authorized, or content not available
        """
        repo = SqlAlchemyTranslationJobRepository(db)
        db_job = repo.get(job_id)
        if db_job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check ownership
        if not db_job.owner or db_job.owner.clerk_user_id != user.clerk_user_id:
            user_is_admin = await is_admin(user)
            if not user_is_admin:
                raise HTTPException(status_code=403, detail="Not authorized to access this content")
        
        # Check if either translation is completed OR validation is completed
        if db_job.status != "COMPLETED":
            # If translation not complete, check if validation is done (which also provides content)
            if db_job.validation_status != "COMPLETED":
                raise HTTPException(status_code=400, detail=f"Translation content is available only for completed jobs or validated jobs. Job status: {db_job.status}, Validation status: {db_job.validation_status}")
        
        # Determine which file to return based on what's available
        file_path = None
        
        # Check if we have a translation file (post-edit overwrites the original, so we use the same path)
        if db_job.filepath:
            file_manager = FileManager()
            file_path, _, _ = file_manager.get_translated_file_path(db_job)
            if not os.path.exists(file_path):
                # If translated file doesn't exist but validation is complete, we can extract from validation report
                if db_job.validation_status != "COMPLETED" or not db_job.validation_report_path:
                    raise HTTPException(status_code=404, detail=f"Translated file not found")
                file_path = None  # Will extract from validation report
        elif db_job.validation_status == "COMPLETED" and db_job.validation_report_path:
            # For validation-only case, we need to extract content from validation report
            file_path = None  # Will handle below
        else:
            raise HTTPException(status_code=404, detail="No content file found for this job.")
        
        # Handle validation report case specially - extract translated content from report
        if file_path is None and db_job.validation_status == "COMPLETED" and db_job.validation_report_path:
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
                    raise HTTPException(status_code=404, detail="No translated content found in validation report")
            except Exception as e:
                print(f"Error reading validation report: {e}")
                raise HTTPException(status_code=500, detail="Error extracting content from validation report")
        else:
            # Regular file reading
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")
        
        # Try to read the original source file
        source_content = None
        if db_job.filepath and os.path.exists(db_job.filepath):
            try:
                # Parse the original file to get the text content
                from core.utils.file_parser import parse_document
                source_content = parse_document(db_job.filepath)
            except Exception as e:
                # Log error but don't fail the whole request
                print(f"Error reading source file: {e}")
        
        # Return content as JSON with metadata
        return {
            "job_id": job_id,
            "filename": db_job.filename,
            "content": content,
            "source_content": source_content,
            "completed_at": db_job.completed_at.isoformat() if db_job.completed_at else None
        }
    
    @staticmethod
    async def download_job_pdf(
        db: Session,
        user: User,
        job_id: int,
        include_source: bool = True,
        include_illustrations: bool = True,
        page_size: str = "A4"
    ):
        """
        Download the translation as a PDF document.
        
        Args:
            db: Database session
            user: Current user
            job_id: Job ID
            include_source: Whether to include source text
            include_illustrations: Whether to include illustrations
            page_size: Page size format
            
        Returns:
            Response with PDF file
            
        Raises:
            HTTPException: If job not found, not authorized, or PDF generation fails
        """
        # Get the job from database
        repo = SqlAlchemyTranslationJobRepository(db)
        db_job = repo.get(job_id)
        if db_job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check ownership
        if not db_job.owner or db_job.owner.clerk_user_id != user.clerk_user_id:
            user_is_admin = await is_admin(user)
            if not user_is_admin:
                raise HTTPException(status_code=403, detail="Not authorized to download this PDF")
        
        # Check if job is completed
        if db_job.status != "COMPLETED":
            raise HTTPException(
                status_code=400, 
                detail=f"PDF generation is available only for completed jobs. Current status: {db_job.status}"
            )
        
        # Validate page size
        if page_size not in ["A4", "Letter"]:
            raise HTTPException(status_code=400, detail="Invalid page size. Must be 'A4' or 'Letter'")
        
        try:
            # Generate PDF
            pdf_bytes = generate_translation_pdf(
                job_id=job_id,
                db=db,
                include_source=include_source,
                include_illustrations=include_illustrations,
                page_size=page_size
            )
            
            # Generate filename
            base_filename = db_job.filename.rsplit('.', 1)[0] if '.' in db_job.filename else db_job.filename
            pdf_filename = f"{base_filename}_translation.pdf"
            
            # Return PDF response
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{pdf_filename}"'
                }
            )
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logging.error(f"Error generating PDF for job {job_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")
