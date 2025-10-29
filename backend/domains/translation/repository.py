from typing import Protocol, Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc

from backend.domains.translation.models import TranslationJob, TranslationUsageLog
from backend.domains.shared.repository import SqlAlchemyRepository


class TranslationJobRepository(Protocol):
    """Protocol for TranslationJob repository operations."""
    
    def get(self, id: int) -> Optional[TranslationJob]:
        """Get a translation job by ID."""
        ...
    
    def add(self, job: TranslationJob) -> TranslationJob:
        """Add a new translation job."""
        ...
    
    def delete(self, job: TranslationJob) -> None:
        """Delete a translation job."""
        ...
    
    def set_status(
        self, 
        id: int, 
        status: str, 
        *, 
        error: Optional[str] = None,
        progress: Optional[int] = None
    ) -> None:
        """Update job status with optional error message and progress."""
        ...
    
    def list_by_user(
        self, 
        user_id: int, 
        limit: int = 100, 
        cursor: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[TranslationJob]:
        """List jobs for a specific user with cursor- or offset-based pagination."""
        ...
    
    def find_by_idempotency_key(
        self, 
        owner_id: int, 
        idempotency_key: str
    ) -> Optional[TranslationJob]:
        """Find a job by owner and idempotency key for duplicate request handling."""
        ...
    
    def update_progress(self, id: int, progress: int) -> None:
        """Update job progress percentage."""
        ...
    
    def update_validation_status(
        self,
        id: int,
        status: str,
        *,
        progress: Optional[int] = None,
        report_path: Optional[str] = None
    ) -> None:
        """Update validation status and related fields."""
        ...
    
    def update_post_edit_status(
        self,
        id: int,
        status: str,
        *,
        progress: Optional[int] = None,
        log_path: Optional[str] = None
    ) -> None:
        """Update post-edit status and related fields."""
        ...


class SqlAlchemyTranslationJobRepository(SqlAlchemyRepository[TranslationJob]):
    """SQLAlchemy implementation of TranslationJobRepository."""

    def __init__(self, session: Session):
        """Initialize with a SQLAlchemy session."""
        super().__init__(session, TranslationJob)
        self._idempotency_cache: Dict[str, int] = {}

    def get(self, id: int) -> Optional[TranslationJob]:
        """Get a job by ID with owner eagerly loaded to prevent N+1 queries."""
        return self.session.query(TranslationJob).options(
            joinedload(TranslationJob.owner)
        ).filter(TranslationJob.id == id).first()
    
    def set_status(
        self, 
        id: int, 
        status: str, 
        *, 
        error: Optional[str] = None,
        progress: Optional[int] = None
    ) -> None:
        """Update job status with optional error message and progress."""
        job = self.get(id)
        if job:
            job.status = status
            if error is not None:
                job.error_message = error
            if progress is not None:
                job.progress = progress
            if status == "COMPLETED":
                job.completed_at = datetime.utcnow()
            self.session.flush()
    
    def list_by_user(
        self,
        user_id: int,
        limit: int = 100,
        cursor: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[TranslationJob]:
        """List jobs for a specific user with cursor-based or offset-based pagination."""
        query = self.session.query(TranslationJob).options(
            joinedload(TranslationJob.owner)
        ).filter(
            TranslationJob.owner_id == user_id
        ).order_by(desc(TranslationJob.created_at))

        if cursor:
            query = query.filter(TranslationJob.id < cursor)

        if offset:
            query = query.offset(offset)

        return query.limit(limit).all()
    
    def find_by_idempotency_key(
        self, 
        owner_id: int, 
        idempotency_key: str
    ) -> Optional[TranslationJob]:
        """
        Find a job by owner and idempotency key.
        
        Note: This implementation uses an in-memory cache for idempotency.
        In production, consider using a separate idempotency table or Redis.
        """
        cache_key = f"{owner_id}:{idempotency_key}"
        
        # Check cache first
        if cache_key in self._idempotency_cache:
            job_id = self._idempotency_cache[cache_key]
            return self.get(job_id)
        
        # For now, we can check by filename and owner within a time window
        # This is a simplified implementation
        recent_job = self.session.query(TranslationJob).filter(
            and_(
                TranslationJob.owner_id == owner_id,
                TranslationJob.filename == idempotency_key,  # Using filename as key
                TranslationJob.created_at > datetime.utcnow().replace(hour=0, minute=0, second=0)
            )
        ).order_by(desc(TranslationJob.created_at)).first()
        
        if recent_job:
            self._idempotency_cache[cache_key] = recent_job.id
            
        return recent_job
    
    def store_idempotency_key(self, owner_id: int, idempotency_key: str, job_id: int):
        """Store an idempotency key mapping."""
        cache_key = f"{owner_id}:{idempotency_key}"
        self._idempotency_cache[cache_key] = job_id
    
    def update_progress(self, id: int, progress: int) -> None:
        """Update job progress percentage."""
        job = self.get(id)
        if job:
            job.progress = min(100, max(0, progress))  # Ensure 0-100 range
            self.session.flush()
    
    def update_validation_status(
        self,
        id: int,
        status: str,
        *,
        progress: Optional[int] = None,
        report_path: Optional[str] = None
    ) -> None:
        """Update validation status and related fields."""
        job = self.get(id)
        if job:
            job.validation_status = status
            if progress is not None:
                job.validation_progress = min(100, max(0, progress))
            if report_path is not None:
                job.validation_report_path = report_path
            if status == "COMPLETED":
                job.validation_completed_at = datetime.utcnow()
            self.session.flush()
    
    def update_post_edit_status(
        self,
        id: int,
        status: str,
        *,
        progress: Optional[int] = None,
        log_path: Optional[str] = None
    ) -> None:
        """Update post-edit status and related fields."""
        job = self.get(id)
        if job:
            job.post_edit_status = status
            if progress is not None:
                job.post_edit_progress = min(100, max(0, progress))
            if log_path is not None:
                job.post_edit_log_path = log_path
            if status == "COMPLETED":
                job.post_edit_completed_at = datetime.utcnow()
            self.session.flush()
    
    def get_with_usage_logs(self, id: int) -> Optional[TranslationJob]:
        """Get a job with its usage logs eagerly loaded."""
        return self.session.query(TranslationJob).filter(
            TranslationJob.id == id
        ).first()
    
    def update_illustration_status(
        self,
        id: int,
        status: str,
        *,
        progress: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None,
        directory: Optional[str] = None
    ) -> None:
        """Update illustration generation status and related fields."""
        job = self.get(id)
        if job:
            job.illustrations_status = status
            if progress is not None:
                job.illustrations_progress = min(100, max(0, progress))
            if data is not None:
                job.illustrations_data = data
                job.illustrations_count = len(data.get("scenes", []))
            if directory is not None:
                job.illustrations_directory = directory
            self.session.flush()


class TranslationUsageLogRepository(SqlAlchemyRepository[TranslationUsageLog]):
    """Repository for TranslationUsageLog operations."""
    
    def __init__(self, session: Session):
        """Initialize with a SQLAlchemy session."""
        super().__init__(session, TranslationUsageLog)
    
    def get_by_job(self, job_id: int) -> List[TranslationUsageLog]:
        """Get all usage logs for a specific job."""
        return self.session.query(TranslationUsageLog).filter(
            TranslationUsageLog.job_id == job_id
        ).order_by(desc(TranslationUsageLog.created_at)).all()
    
    def get_total_usage_by_model(self, model: str, days: int = 30) -> Dict[str, Any]:
        """Get total usage statistics for a model over the last N days."""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        logs = self.session.query(TranslationUsageLog).filter(
            and_(
                TranslationUsageLog.model_used == model,
                TranslationUsageLog.created_at >= cutoff_date
            )
        ).all()
        
        return {
            "total_jobs": len(logs),
            "total_input_chars": sum(log.original_length for log in logs),
            "total_output_chars": sum(log.translated_length for log in logs),
            "total_duration_seconds": sum(log.translation_duration_seconds for log in logs),
            "error_count": sum(1 for log in logs if log.error_type),
        }
