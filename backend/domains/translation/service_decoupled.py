"""
Example of Translation Service using decoupled user interfaces.

This demonstrates how to refactor services to use UserContext interfaces
instead of direct User model references.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from backend.domains.translation.models import TranslationJob, TranslationUsageLog
from backend.domains.translation.schemas import (
    TranslationJobCreate,
    TranslationJobResponse,
    TranslationJobUpdate
)
from backend.domains.shared.interfaces import (
    UserContext,
    IUserProvider,
    UserPermissions
)
from backend.domains.shared.events import (
    EventPublisher,
    TranslationStartedEvent,
    TranslationCompletedEvent,
    TranslationFailedEvent
)
from backend.domains.translation.user_provider import (
    TranslationUserProvider,
    TranslationOwnershipService
)

logger = logging.getLogger(__name__)


class DecoupledTranslationService:
    """
    Translation service that uses UserContext interfaces instead of
    direct User model references.
    
    This demonstrates the decoupled approach where the service doesn't
    import or depend on the User model directly.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_provider = TranslationUserProvider(session)
        self.ownership_service = TranslationOwnershipService(self.user_provider)
        self.event_publisher = EventPublisher(session)
    
    async def create_job(
        self,
        job_data: TranslationJobCreate,
        user_context: UserContext  # Instead of User model
    ) -> TranslationJobResponse:
        """
        Create a new translation job.
        
        Note: We receive UserContext instead of User model instance.
        """
        # Create the job
        job = TranslationJob(
            filename=job_data.filename,
            filepath=job_data.filepath,
            owner_id=user_context.id,  # Use context ID
            segment_size=job_data.segment_size,
            validation_enabled=job_data.validation_enabled,
            post_edit_enabled=job_data.post_edit_enabled,
            status="PENDING"
        )
        
        self.session.add(job)
        await self.session.flush()  # Get job ID
        
        # Publish domain event
        await self.event_publisher.publish(
            TranslationStartedEvent(
                event_id=f"trans_started_{job.id}_{datetime.utcnow().timestamp()}",
                aggregate_id=str(job.id),
                job_id=job.id,
                user_id=user_context.id,
                filename=job_data.filename,
                segment_size=job_data.segment_size,
                validation_enabled=job_data.validation_enabled,
                post_edit_enabled=job_data.post_edit_enabled
            )
        )
        
        await self.session.commit()
        
        # Return response with user info from context
        return TranslationJobResponse(
            id=job.id,
            filename=job.filename,
            status=job.status,
            owner={
                "id": user_context.id,
                "name": user_context.name,
                "email": user_context.email
            },
            created_at=job.created_at
        )
    
    async def get_job(
        self,
        job_id: int,
        user_context: UserContext
    ) -> Optional[TranslationJobResponse]:
        """
        Get a translation job if user has access.
        """
        # Get the job
        result = await self.session.execute(
            select(TranslationJob).where(TranslationJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            return None
        
        # Check permissions using the ownership service
        if not await self.ownership_service.can_access_job(
            user_context.id,
            job.owner_id
        ):
            raise PermissionError("Access denied to this job")
        
        # Get owner info if needed
        owner_info = None
        if job.owner_id:
            owner_context = await self.user_provider.get_user_context(job.owner_id)
            if owner_context:
                owner_info = {
                    "id": owner_context.id,
                    "name": owner_context.name,
                    "email": owner_context.email
                }
        
        return TranslationJobResponse(
            id=job.id,
            filename=job.filename,
            status=job.status,
            owner=owner_info,
            created_at=job.created_at,
            completed_at=job.completed_at
        )
    
    async def list_user_jobs(
        self,
        user_context: UserContext,
        limit: int = 10,
        offset: int = 0
    ) -> List[TranslationJobResponse]:
        """
        List jobs for a specific user.
        """
        permissions = UserPermissions(user_context)
        
        # Build query based on permissions
        query = select(TranslationJob)
        
        if not permissions.is_admin():
            # Regular users see only their own jobs
            query = query.where(TranslationJob.owner_id == user_context.id)
        
        # Add pagination
        query = query.order_by(TranslationJob.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        jobs = result.scalars().all()
        
        # Convert to response objects
        responses = []
        for job in jobs:
            # For admin viewing all jobs, fetch owner info
            owner_info = None
            if job.owner_id:
                if job.owner_id == user_context.id:
                    # It's the current user's job
                    owner_info = {
                        "id": user_context.id,
                        "name": user_context.name,
                        "email": user_context.email
                    }
                elif permissions.is_admin():
                    # Admin viewing another user's job
                    owner_context = await self.user_provider.get_user_context(job.owner_id)
                    if owner_context:
                        owner_info = {
                            "id": owner_context.id,
                            "name": owner_context.name,
                            "email": owner_context.email
                        }
            
            responses.append(TranslationJobResponse(
                id=job.id,
                filename=job.filename,
                status=job.status,
                owner=owner_info,
                created_at=job.created_at,
                completed_at=job.completed_at
            ))
        
        return responses
    
    async def update_job_status(
        self,
        job_id: int,
        status: str,
        user_context: Optional[UserContext] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update job status and publish appropriate events.
        
        Note: user_context is optional here as this might be called
        from background tasks where we don't have user context.
        """
        # Update job status
        await self.session.execute(
            update(TranslationJob)
            .where(TranslationJob.id == job_id)
            .values(
                status=status,
                error_message=error_message,
                completed_at=datetime.utcnow() if status in ["COMPLETED", "FAILED"] else None
            )
        )
        
        # Get job details for event
        result = await self.session.execute(
            select(TranslationJob).where(TranslationJob.id == job_id)
        )
        job = result.scalar_one()
        
        # Publish appropriate event based on status
        if status == "COMPLETED":
            # Get usage log for metrics
            usage_result = await self.session.execute(
                select(TranslationUsageLog)
                .where(TranslationUsageLog.job_id == job_id)
                .order_by(TranslationUsageLog.created_at.desc())
                .limit(1)
            )
            usage_log = usage_result.scalar_one_or_none()
            
            await self.event_publisher.publish_translation_completed(
                job_id=job_id,
                user_id=job.owner_id,
                filename=job.filename,
                duration_seconds=usage_log.translation_duration_seconds if usage_log else 0,
                output_path=job.filepath or "",
                segment_count=len(job.translation_segments or []),
                total_characters=usage_log.translated_length if usage_log else 0
            )
            
        elif status == "FAILED":
            await self.event_publisher.publish_translation_failed(
                job_id=job_id,
                user_id=job.owner_id,
                error_message=error_message or "Unknown error",
                error_type="TranslationError"
            )
        
        await self.session.commit()
    
    async def delete_job(
        self,
        job_id: int,
        user_context: UserContext
    ) -> bool:
        """
        Delete a translation job if user has permission.
        """
        # Get the job
        result = await self.session.execute(
            select(TranslationJob).where(TranslationJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            return False
        
        # Check permissions
        permissions = UserPermissions(user_context)
        if not (permissions.is_admin() or job.owner_id == user_context.id):
            raise PermissionError("Cannot delete this job")
        
        # Delete the job
        await self.session.delete(job)
        await self.session.commit()
        
        return True
    
    async def get_job_statistics(
        self,
        user_context: UserContext
    ) -> Dict[str, Any]:
        """
        Get translation statistics for a user.
        """
        permissions = UserPermissions(user_context)
        
        # Base query for jobs
        jobs_query = select(TranslationJob)
        
        if not permissions.is_admin():
            # Regular users see only their own stats
            jobs_query = jobs_query.where(TranslationJob.owner_id == user_context.id)
        
        result = await self.session.execute(jobs_query)
        jobs = result.scalars().all()
        
        # Calculate statistics
        total_jobs = len(jobs)
        completed_jobs = sum(1 for j in jobs if j.status == "COMPLETED")
        failed_jobs = sum(1 for j in jobs if j.status == "FAILED")
        pending_jobs = sum(1 for j in jobs if j.status == "PENDING")
        in_progress_jobs = sum(1 for j in jobs if j.status == "IN_PROGRESS")
        
        return {
            "user_id": user_context.id,
            "is_admin": permissions.is_admin(),
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "pending_jobs": pending_jobs,
            "in_progress_jobs": in_progress_jobs,
            "success_rate": (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
        }


# Example usage in routes
"""
from fastapi import APIRouter, Depends
from backend.auth import get_current_user_context  # Modified auth to return UserContext

router = APIRouter()

@router.post("/jobs")
async def create_job(
    job_data: TranslationJobCreate,
    user_context: UserContext = Depends(get_current_user_context),
    session: AsyncSession = Depends(get_session)
):
    service = DecoupledTranslationService(session)
    return await service.create_job(job_data, user_context)

@router.get("/jobs/{job_id}")
async def get_job(
    job_id: int,
    user_context: UserContext = Depends(get_current_user_context),
    session: AsyncSession = Depends(get_session)
):
    service = DecoupledTranslationService(session)
    job = await service.get_job(job_id, user_context)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
"""