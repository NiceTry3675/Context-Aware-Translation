from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from .database import Base

class TranslationJob(Base):
    __tablename__ = "translation_jobs"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    status = Column(String, default="PENDING")
    progress = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    error_message = Column(String, nullable=True)

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

class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    message = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
