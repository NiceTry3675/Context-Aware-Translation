"""
Translation domain routes with business logic.

This module contains the core business logic for translation operations,
separated from the API routing layer.
"""

import os
import re
import shutil
from typing import List, Optional

from fastapi import HTTPException, UploadFile, File, Form, Response
from sqlalchemy.orm import Session

from ...domains.shared.base import ModelAPIFactory
from ...domains.shared.utils import FileManager
from ...tasks.translation import process_translation_task
from ...models.translation import TranslationJob
from ...models.user import User
from .repository import SqlAlchemyTranslationJobRepository
from .service import TranslationDomainService
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
        job = service.create_translation_job(
            filename=file.filename,
            owner_id=user.id,
            segment_size=segment_size
        )
        
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