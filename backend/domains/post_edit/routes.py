"""
Post-Edit domain routes with business logic.

This module contains the core business logic for post-editing operations,
separated from the API routing layer.
"""

import os
import json
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException

from backend.domains.translation.models import TranslationJob
from backend.domains.user.models import User
from backend.domains.translation.repository import SqlAlchemyTranslationJobRepository
from backend.auth import is_admin
from backend.tasks.post_edit import process_post_edit_task
from .service import PostEditDomainService
from .schemas import PostEditRequest, StructuredPostEditLog


class PostEditRoutes:
    """Business logic for post-editing operations."""
    
    @staticmethod
    async def trigger_post_edit(
        db: Session,
        user: User,
        job_id: int,
        request: PostEditRequest
    ):
        """
        Trigger post-editing on a validated translation job.
        
        Args:
            db: Database session
            user: Current user
            job_id: Job ID
            request: Post-edit request parameters
            
        Returns:
            Dict with message and job_id
            
        Raises:
            HTTPException: If job not found, not authorized, or prerequisites not met
        """
        repo = SqlAlchemyTranslationJobRepository(db)
        db_job = repo.get(job_id)
        if db_job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check ownership or admin role
        user_is_admin = await is_admin(user)
        if not db_job.owner or (db_job.owner.clerk_user_id != user.clerk_user_id and not user_is_admin):
            raise HTTPException(status_code=403, detail="Not authorized to post-edit this job")
        
        # Validate prerequisites
        try:
            post_edit_service = PostEditDomainService()
            post_edit_service.validate_prerequisites(db, job_id)
        except (ValueError, FileNotFoundError) as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Update job with post-edit settings
        db_job.post_edit_enabled = True
        db_job.post_edit_status = "PENDING"
        db.commit()
        
        # Start post-editing using Celery
        process_post_edit_task.delay(
            job_id=job_id,
            api_key=request.api_key,
            model_name=request.model_name,
            user_id=user.id
        )
        
        return {"message": "Post-editing started", "job_id": job_id}
    
    @staticmethod
    async def get_post_edit_log(
        db: Session,
        user: User,
        job_id: int,
        structured: bool = False
    ):
        """
        Get the post-edit log for a job.
        
        Args:
            db: Database session
            user: Current user
            job_id: Job ID
            structured: If True, returns a StructuredPostEditLog
            
        Returns:
            Either raw JSON log or StructuredPostEditLog
            
        Raises:
            HTTPException: If job not found, not authorized, or log not available
        """
        repo = SqlAlchemyTranslationJobRepository(db)
        db_job = repo.get(job_id)
        if db_job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check ownership or admin role
        user_is_admin = await is_admin(user)
        if not db_job.owner or (db_job.owner.clerk_user_id != user.clerk_user_id and not user_is_admin):
            raise HTTPException(status_code=403, detail="Not authorized to access this post-edit log")
        
        if db_job.post_edit_status != "COMPLETED":
            raise HTTPException(status_code=400, detail=f"Post-editing not completed. Current status: {db_job.post_edit_status}")
        
        if not db_job.post_edit_log_path or not os.path.exists(db_job.post_edit_log_path):
            raise HTTPException(status_code=404, detail="Post-edit log not found")
        
        # Read and return the JSON log
        with open(db_job.post_edit_log_path, 'r', encoding='utf-8') as f:
            log = json.load(f)
        
        # If structured response requested, parse and return StructuredPostEditLog
        if structured:
            return StructuredPostEditLog.from_json_log(log)
        
        # Default: return raw log
        return log