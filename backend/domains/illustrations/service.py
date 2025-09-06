"""Service layer for illustration management."""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from pathlib import Path
import json
import os

from ..translation.models import TranslationJob
from ..user.models import User
from core.translation.illustration_generator import IllustrationGenerator
from core.schemas.illustration import (
    IllustrationConfig,
    IllustrationData,
    IllustrationBatch,
    IllustrationStatus,
    CharacterProfile
)
from ..analysis import StyleAnalysis, CharacterAnalysis


class IllustrationsService:
    """Service for managing illustration generation and storage."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_job_for_user(self, job_id: int, user: User) -> TranslationJob:
        """Get a translation job that belongs to the user."""
        job = self.db.query(TranslationJob).filter(
            TranslationJob.id == job_id,
            TranslationJob.owner_id == user.id
        ).first()
        
        if not job:
            raise ValueError("Translation job not found")
        
        return job
    
    def validate_job_completed(self, job: TranslationJob):
        """Ensure job is completed before generating illustrations."""
        if job.status != "COMPLETED":
            raise ValueError("Translation must be completed before generating illustrations")
    
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
        return Path(f"translated_novel/{job_id}/illustrations.json")
    
    def load_illustrations(self, job_id: int) -> Optional[IllustrationBatch]:
        """Load illustrations from file."""
        illustrations_path = self.get_illustrations_path(job_id)
        
        if not illustrations_path.exists():
            return None
        
        with open(illustrations_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return IllustrationBatch(**data)
    
    def save_illustrations(self, job_id: int, batch: IllustrationBatch):
        """Save illustrations to file."""
        illustrations_path = self.get_illustrations_path(job_id)
        illustrations_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(illustrations_path, 'w', encoding='utf-8') as f:
            json.dump(batch.dict(), f, ensure_ascii=False, indent=2)
    
    def get_character_base_prompts_path(self, job_id: int) -> Path:
        """Get the path to the character base prompts file."""
        return Path(f"translated_novel/{job_id}/character_base_prompts.json")
    
    def load_character_base_prompts(self, job_id: int) -> Optional[List[Dict[str, Any]]]:
        """Load character base prompts from file."""
        prompts_path = self.get_character_base_prompts_path(job_id)
        
        if not prompts_path.exists():
            return None
        
        with open(prompts_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_character_base_prompts(self, job_id: int, prompts: List[Dict[str, Any]]):
        """Save character base prompts to file."""
        prompts_path = self.get_character_base_prompts_path(job_id)
        prompts_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(prompts_path, 'w', encoding='utf-8') as f:
            json.dump(prompts, f, ensure_ascii=False, indent=2)
    
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