"""
Post-edit domain routes - thin routing layer.

This module provides a thin routing layer for post-editing operations,
delegating all business logic to the PostEditDomainService.
"""

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.config.dependencies import get_db, get_required_user
from backend.domains.user.models import User
from backend.domains.post_edit.schemas import PostEditRequest
from backend.domains.post_edit.service import PostEditDomainService


def get_post_edit_service(db: Session = Depends(get_db)) -> PostEditDomainService:
    """Dependency injection for PostEditDomainService."""
    return PostEditDomainService(lambda: db)


async def post_edit_job(
    job_id: int,
    request: PostEditRequest,
    user: User = Depends(get_required_user),
    service: PostEditDomainService = Depends(get_post_edit_service)
):
    """
    Trigger post-editing on a validated translation job.
    
    Args:
        job_id: Job ID
        request: Post-edit request parameters
        user: Current authenticated user
        service: Post-edit domain service
        
    Returns:
        Task information for the post-edit job
    """
    return await service.trigger_post_edit(user, job_id, request)


async def get_post_edit_status(
    job_id: int,
    user: User = Depends(get_required_user),
    service: PostEditDomainService = Depends(get_post_edit_service)
):
    """
    Get the post-edit report for a job.
    
    Args:
        job_id: Job ID
        user: Current authenticated user
        service: Post-edit domain service
        
    Returns:
        Post-edit report with changes and statistics
    """
    return await service.get_post_edit_report(user, job_id)