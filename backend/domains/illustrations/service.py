"""Service layer for illustration management."""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from pathlib import Path
import os

from ..translation.models import TranslationJob
from ..user.models import User
from ..shared.service_base import ServiceBase
from core.translation.illustration_generator import IllustrationGenerator
from core.schemas.illustration import (
    IllustrationConfig,
    IllustrationData,
    IllustrationBatch,
    IllustrationStatus,
    CharacterProfile
)
from ..analysis import StyleAnalysis, CharacterAnalysis


class IllustrationsService(ServiceBase):
    """Service for managing illustration generation and storage."""
    
    def __init__(self, db: Session):
        super().__init__()
        self.db = db
    
    def get_job_for_user(self, job_id: int, user: User) -> TranslationJob:
        """Get a translation job that belongs to the user."""
        job = self.db.query(TranslationJob).filter(
            TranslationJob.id == job_id,
            TranslationJob.owner_id == user.id
        ).first()
        
        if not job:
            self.raise_not_found("Translation job")
        
        return job
    
    def validate_job_completed(self, job: TranslationJob):
        """Ensure job is completed before generating illustrations."""
        if job.status != "COMPLETED":
            self.raise_validation_error("Translation must be completed before generating illustrations")
    
    def start_illustration_generation(
        self,
        job: TranslationJob,
        config: IllustrationConfig
    ):
        """Update job to indicate illustration generation has started."""
        job.illustrations_enabled = True
        job.illustrations_config = config.dict()
        job.illustrations_status = "IN_PROGRESS"
        job.illustrations_progress = 0
        self.db.commit()
    
    def get_illustrations_path(self, job_id: int) -> Path:
        """Get the path to the illustrations file for a job."""
        return Path(self.file_manager.get_job_illustration_path(job_id))
    
    def load_illustrations(self, job_id: int) -> Optional[IllustrationBatch]:
        """Load illustrations from file."""
        illustrations_path = self.get_illustrations_path(job_id)
        
        if not illustrations_path.exists():
            return None
        
        try:
            data = self.load_structured_data(str(illustrations_path))
            return IllustrationBatch(**data)
        except FileNotFoundError:
            return None
    
    def save_illustrations(self, job_id: int, batch: IllustrationBatch):
        """Save illustrations to file."""
        illustrations_path = self.get_illustrations_path(job_id)
        self.save_structured_output(batch.dict(), str(illustrations_path))
    
    def get_character_base_prompts_path(self, job_id: int) -> Path:
        """Get the path to the character base prompts file."""
        return Path(self.file_manager.get_job_character_prompts_path(job_id))
    
    def load_character_base_prompts(self, job_id: int) -> Optional[List[Dict[str, Any]]]:
        """Load character base prompts from file."""
        prompts_path = self.get_character_base_prompts_path(job_id)
        
        if not prompts_path.exists():
            return None
        
        try:
            return self.load_structured_data(str(prompts_path))
        except FileNotFoundError:
            return None
    
    def save_character_base_prompts(self, job_id: int, prompts: List[Dict[str, Any]]):
        """Save character base prompts to file."""
        prompts_path = self.get_character_base_prompts_path(job_id)
        self.save_structured_output(prompts, str(prompts_path))
    
    def delete_illustration(self, job_id: int, segment_index: int) -> bool:
        """Delete a specific illustration from the batch."""
        batch = self.load_illustrations(job_id)
        
        if not batch:
            return False
        
        # Find and remove the illustration
        original_count = len(batch.illustrations)
        batch.illustrations = [
            ill for ill in batch.illustrations
            if ill.segment_index != segment_index
        ]
        
        # If we removed an illustration, save the updated batch
        if len(batch.illustrations) < original_count:
            self.save_illustrations(job_id, batch)
            return True
        
        return False