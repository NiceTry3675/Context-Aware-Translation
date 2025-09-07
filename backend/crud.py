"""CRUD operations for translation jobs."""

from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from backend.domains.translation.models import TranslationJob


def update_job_progress(db: Session, job_id: int, progress: int) -> None:
    """
    Update the progress percentage for a translation job.
    
    Args:
        db: Database session
        job_id: Job ID
        progress: Progress percentage (0-100)
    """
    job = db.query(TranslationJob).filter(TranslationJob.id == job_id).first()
    if job:
        job.progress = progress
        db.commit()


def update_job_final_glossary(db: Session, job_id: int, glossary: Dict[str, str]) -> None:
    """
    Update the final glossary for a translation job.
    
    Args:
        db: Database session
        job_id: Job ID
        glossary: Final glossary dictionary
    """
    job = db.query(TranslationJob).filter(TranslationJob.id == job_id).first()
    if job:
        job.final_glossary = glossary
        db.commit()


def update_job_translation_segments(db: Session, job_id: int, segments_data: List[Dict]) -> None:
    """
    Update the translation segments for a job.
    
    Args:
        db: Database session
        job_id: Job ID
        segments_data: List of segment dictionaries with source and translated text
    """
    job = db.query(TranslationJob).filter(TranslationJob.id == job_id).first()
    if job:
        job.translation_segments = segments_data
        db.commit()