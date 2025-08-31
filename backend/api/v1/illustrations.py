"""
Illustration API endpoints

This module provides API endpoints for managing and generating illustrations
for translation segments.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import os
import json
from pathlib import Path

from ...database import SessionLocal
from ...models import TranslationJob, User
from ...auth import get_required_user
from core.translation.illustration_generator import IllustrationGenerator
from core.schemas.illustration import (
    IllustrationConfig, 
    IllustrationData, 
    IllustrationBatch,
    IllustrationStatus
)

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/{job_id}/generate")
async def generate_illustrations(
    job_id: int,
    config: IllustrationConfig,
    api_key: str = Query(..., description="API key for Gemini"),
    max_illustrations: Optional[int] = Query(None, description="Maximum number of illustration prompts to generate"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user)
):
    """
    Generate illustration prompts for a translation job.
    
    This endpoint triggers generation of detailed illustration prompts for all or selected segments
    of a completed translation job. The prompts can then be used with image generation services
    like DALL-E, Midjourney, or Stable Diffusion to create actual illustrations.
    """
    # Get the translation job
    job = db.query(TranslationJob).filter(
        TranslationJob.id == job_id,
        TranslationJob.owner_id == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Translation job not found")
    
    if job.status != "COMPLETED":
        raise HTTPException(
            status_code=400, 
            detail="Translation must be completed before generating illustrations"
        )
    
    # Update job with illustration configuration
    job.illustrations_enabled = True
    job.illustrations_config = config.dict()
    job.illustrations_status = "IN_PROGRESS"
    job.illustrations_progress = 0
    db.commit()
    
    print(f"--- [ILLUSTRATIONS] Starting generation for job {job_id} with config: {config.dict()} ---")
    
    # Start background generation
    background_tasks.add_task(
        generate_illustrations_task,
        job_id=job_id,
        config=config,
        api_key=api_key,
        max_illustrations=max_illustrations
    )
    
    return {
        "message": "Illustration prompt generation started. Prompts will be created for use with external image generation services.",
        "job_id": job_id,
        "status": "IN_PROGRESS",
        "type": "prompt_generation",
        "note": "Generated prompts can be used with services like DALL-E, Midjourney, or Stable Diffusion to create actual illustrations."
    }


@router.get("/{job_id}/illustrations")
async def get_job_illustrations(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user)
):
    """
    Get all illustration prompts for a translation job.
    
    Returns metadata about all generated illustration prompts for the specified job.
    These prompts can be used with external image generation services.
    """
    # Get the translation job
    job = db.query(TranslationJob).filter(
        TranslationJob.id == job_id,
        TranslationJob.owner_id == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Translation job not found")
    
    if not job.illustrations_data:
        return {
            "job_id": job_id,
            "illustrations": [],
            "status": job.illustrations_status or "NOT_STARTED",
            "count": 0,
            "type": "prompts"
        }
    
    return {
        "job_id": job_id,
        "illustrations": job.illustrations_data,
        "status": job.illustrations_status,
        "count": job.illustrations_count,
        "directory": job.illustrations_directory,
        "type": "prompts",
        "note": "These are illustration prompts, not actual images. Use them with image generation services."
    }


@router.get("/{job_id}/illustration/{segment_index}")
async def get_illustration_prompt(
    job_id: int,
    segment_index: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user)
):
    """
    Get the illustration for a specific segment.
    
    Returns the generated image if available, otherwise returns the prompt JSON file.
    """
    # Get the translation job
    job = db.query(TranslationJob).filter(
        TranslationJob.id == job_id,
        TranslationJob.owner_id == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Translation job not found")
    
    if not job.illustrations_directory:
        raise HTTPException(status_code=404, detail="No illustrations generated for this job")
    
    # First check for image file
    image_filename = f"segment_{segment_index:04d}.png"
    image_path = Path(job.illustrations_directory) / image_filename
    
    if image_path.exists():
        # Return the actual image file
        return FileResponse(
            path=str(image_path),
            media_type="image/png",
            filename=image_filename
        )
    
    # Fall back to prompt file
    prompt_filename = f"segment_{segment_index:04d}_prompt.json"
    prompt_path = Path(job.illustrations_directory) / prompt_filename
    
    if not prompt_path.exists():
        raise HTTPException(status_code=404, detail=f"Illustration not found for segment {segment_index}")
    
    # Read and return the prompt data
    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt_data = json.load(f)
    
    return prompt_data


@router.delete("/{job_id}/illustration/{segment_index}")
async def delete_illustration_prompt(
    job_id: int,
    segment_index: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user)
):
    """
    Delete a specific illustration and its prompt.
    
    Removes both the image file (if exists) and prompt file, and updates the job metadata.
    """
    # Get the translation job
    job = db.query(TranslationJob).filter(
        TranslationJob.id == job_id,
        TranslationJob.owner_id == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Translation job not found")
    
    if not job.illustrations_directory:
        raise HTTPException(status_code=404, detail="No illustrations generated for this job")
    
    # Construct file paths
    image_filename = f"segment_{segment_index:04d}.png"
    image_path = Path(job.illustrations_directory) / image_filename
    prompt_filename = f"segment_{segment_index:04d}_prompt.json"
    prompt_path = Path(job.illustrations_directory) / prompt_filename
    
    if not image_path.exists() and not prompt_path.exists():
        raise HTTPException(status_code=404, detail=f"Illustration not found for segment {segment_index}")
    
    # Delete the files
    try:
        # Delete image if exists
        if image_path.exists():
            image_path.unlink()
        
        # Delete prompt if exists
        if prompt_path.exists():
            prompt_path.unlink()
        
        # Update job metadata
        if job.illustrations_data:
            illustrations_data = job.illustrations_data
            # Remove the illustration from the data
            illustrations_data = [
                ill for ill in illustrations_data 
                if ill.get("segment_index") != segment_index
            ]
            job.illustrations_data = illustrations_data
            job.illustrations_count = len(illustrations_data)
            db.commit()
        
        return {"message": f"Illustration for segment {segment_index} deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete illustration: {str(e)}")


@router.post("/{job_id}/regenerate/{segment_index}")
async def regenerate_illustration_prompt(
    job_id: int,
    segment_index: int,
    style_hints: Optional[str] = Query(None, description="Optional style hints for regeneration"),
    api_key: str = Query(..., description="API key for Gemini"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user)
):
    """
    Regenerate an illustration prompt for a specific segment.
    
    This allows regenerating a single illustration prompt with optional new style hints.
    """
    # Get the translation job
    job = db.query(TranslationJob).filter(
        TranslationJob.id == job_id,
        TranslationJob.owner_id == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Translation job not found")
    
    if job.status != "COMPLETED":
        raise HTTPException(
            status_code=400,
            detail="Translation must be completed before regenerating illustrations"
        )
    
    # Get the segment data
    if not job.translation_segments or segment_index >= len(job.translation_segments):
        raise HTTPException(status_code=404, detail=f"Segment {segment_index} not found")
    
    # Start background regeneration
    background_tasks.add_task(
        regenerate_single_illustration,
        job_id=job_id,
        segment_index=segment_index,
        style_hints=style_hints,
        api_key=api_key
    )
    
    return {
        "message": f"Regeneration started for segment {segment_index}",
        "job_id": job_id,
        "segment_index": segment_index
    }


def generate_illustrations_task(
    job_id: int,
    config: IllustrationConfig,
    api_key: str,
    max_illustrations: Optional[int]
):
    """
    Background task to generate illustrations for a translation job.
    
    This function runs in the background to generate illustrations
    without blocking the API response.
    """
    print(f"--- [ILLUSTRATIONS TASK] Starting background task for job {job_id} ---")
    print(f"--- [ILLUSTRATIONS TASK] Config: {config.dict()} ---")
    print(f"--- [ILLUSTRATIONS TASK] Max illustrations: {max_illustrations} ---")
    
    db = None
    try:
        # Create a new database session for the background task
        db = SessionLocal()
        print(f"--- [ILLUSTRATIONS TASK] Database session created ---")
        
        # Get the job
        job = db.query(TranslationJob).filter(TranslationJob.id == job_id).first()
        if not job:
            print(f"--- [ILLUSTRATIONS TASK] Job {job_id} not found in database ---")
            return
        
        print(f"--- [ILLUSTRATIONS TASK] Job found, initializing generator ---")
        
        # Initialize illustration generator
        generator = IllustrationGenerator(
            api_key=api_key,
            job_id=job_id,
            enable_caching=config.cache_enabled
        )
        
        print(f"--- [ILLUSTRATIONS TASK] Generator initialized ---")
        
        # Get segments from the job
        segments = job.translation_segments
        if not segments:
            job.illustrations_status = "FAILED"
            job.illustrations_data = {"error": "No segments found"}
            db.commit()
            return
        
        # Prepare segments for illustration
        segments_to_illustrate = []
        for i, segment in enumerate(segments):
            if max_illustrations and len(segments_to_illustrate) >= max_illustrations:
                break
            
            # Check if segment meets criteria
            segment_data = {
                'text': segment.get('source_text', ''),  # Fixed: use 'source_text' instead of 'source'
                'index': i
            }
            
            # Apply filtering based on config
            if len(segment_data['text']) >= config.min_segment_length:
                if not config.skip_dialogue_heavy or segment_data['text'].count('"') < len(segment_data['text']) / 50:
                    segments_to_illustrate.append(segment_data)
        
        # Generate illustration prompts with progress tracking
        results = []
        total_segments = len(segments_to_illustrate)
        
        print(f"--- [ILLUSTRATIONS TASK] Will generate illustrations for {total_segments} segments ---")
        
        for idx, segment in enumerate(segments_to_illustrate):
            print(f"--- [ILLUSTRATIONS TASK] Processing segment {idx + 1}/{total_segments} (index: {segment['index']}) ---")
            # Generate illustration for this segment
            illustration_path, prompt = generator.generate_illustration(
                segment_text=segment['text'],
                segment_index=segment['index'],
                style_hints=config.style_hints,
                glossary=job.final_glossary
            )
            
            # Determine if it's an image or prompt
            file_type = 'image' if illustration_path and illustration_path.endswith('.png') else 'prompt'
            
            result = {
                'segment_index': segment['index'],
                'illustration_path': illustration_path,
                'prompt': prompt,
                'success': illustration_path is not None,
                'type': file_type
            }
            results.append(result)
            
            # Update progress
            progress = int((idx + 1) / total_segments * 100)
            job.illustrations_progress = progress
            db.commit()
        
        # Update job with final results
        job.illustrations_data = results
        job.illustrations_count = sum(1 for r in results if r['success'])
        job.illustrations_directory = str(generator.job_output_dir)
        job.illustrations_status = "COMPLETED"
        job.illustrations_progress = 100
        
        db.commit()
        
    except Exception as e:
        # Update job with error
        if db:
            job = db.query(TranslationJob).filter(TranslationJob.id == job_id).first()
            if job:
                job.illustrations_status = "FAILED"
                job.illustrations_data = {"error": str(e)}
                job.illustrations_progress = 0
                db.commit()
        print(f"Error in generate_illustrations_task: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Always close the database session
        if db:
            db.close()


def regenerate_single_illustration(
    job_id: int,
    segment_index: int,
    style_hints: Optional[str],
    api_key: str
):
    """
    Background task to regenerate a single illustration prompt.
    """
    db = None
    try:
        # Create a new database session for the background task
        db = SessionLocal()
        
        # Get the job
        job = db.query(TranslationJob).filter(TranslationJob.id == job_id).first()
        if not job:
            return
        
        # Initialize illustration generator
        generator = IllustrationGenerator(
            api_key=api_key,
            job_id=job_id,
            enable_caching=False  # Don't use cache for regeneration
        )
        
        # Get the segment
        segments = job.translation_segments
        if not segments or segment_index >= len(segments):
            return
        
        segment = segments[segment_index]
        
        # Generate new illustration prompt
        prompt_path, prompt = generator.generate_illustration(
            segment_text=segment.get('source_text', ''),  # Fixed: use 'source_text' instead of 'source'
            segment_index=segment_index,
            style_hints=style_hints or job.illustrations_config.get('style_hints', ''),
            glossary=job.final_glossary
        )
        
        # Update job metadata
        if prompt_path:
            illustrations_data = job.illustrations_data or []
            
            # Update or add the illustration data
            found = False
            for ill in illustrations_data:
                if ill.get('segment_index') == segment_index:
                    ill['illustration_path'] = prompt_path
                    ill['prompt'] = prompt
                    ill['success'] = True
                    ill['type'] = 'image' if prompt_path.endswith('.png') else 'prompt'
                    found = True
                    break
            
            if not found:
                illustrations_data.append({
                    'segment_index': segment_index,
                    'illustration_path': prompt_path,
                    'prompt': prompt,
                    'success': True,
                    'type': 'image' if prompt_path.endswith('.png') else 'prompt'
                })
            
            job.illustrations_data = illustrations_data
            job.illustrations_count = sum(1 for r in illustrations_data if r.get('success'))
            db.commit()
            
    except Exception as e:
        print(f"Error regenerating illustration prompt: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Always close the database session
        if db:
            db.close()