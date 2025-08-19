from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ._base import Base

class TranslationJob(Base):
    __tablename__ = "translation_jobs"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    status = Column(String, default="PENDING")
    progress = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    error_message = Column(String, nullable=True)
    filepath = Column(String, nullable=True)

    # --- Add these lines ---
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Start as nullable for existing jobs
    owner = relationship("User", back_populates="jobs")
    final_glossary = Column(JSON, nullable=True)
    # -----------------------
    segment_size = Column(Integer, default=15000)
    # Segment data for displaying in segment view
    translation_segments = Column(JSON, nullable=True)  # Stores both source and translated segments
    
    # Validation and Post-Edit fields
    validation_enabled = Column(Boolean, default=False)
    validation_status = Column(String, nullable=True)  # PENDING, IN_PROGRESS, COMPLETED, FAILED
    validation_progress = Column(Integer, default=0)  # Progress percentage 0-100
    validation_sample_rate = Column(Integer, default=100)  # Percentage 0-100
    quick_validation = Column(Boolean, default=False)
    validation_report_path = Column(String, nullable=True)
    validation_completed_at = Column(DateTime(timezone=True), nullable=True)
    
    post_edit_enabled = Column(Boolean, default=False)
    post_edit_status = Column(String, nullable=True)  # PENDING, IN_PROGRESS, COMPLETED, FAILED
    post_edit_progress = Column(Integer, default=0) # Progress percentage 0-100
    post_edit_log_path = Column(String, nullable=True)
    post_edit_completed_at = Column(DateTime(timezone=True), nullable=True)

class TranslationUsageLog(Base):
    __tablename__ = "translation_usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("translation_jobs.id"), index=True)
    original_length = Column(Integer)
    translated_length = Column(Integer)
    translation_duration_seconds = Column(Integer)
    model_used = Column(String)
    error_type = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())