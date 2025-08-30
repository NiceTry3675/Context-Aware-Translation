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
from ...models import TranslationJob
from ...auth import get_current_user
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
    api_key: str = Query(..., description="API key for Gemini image generation"),
    max_illustrations: Optional[int] = Query(None, description="Maximum number of illustrations to generate"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Generate illustrations for a translation job.
    
    This endpoint triggers illustration generation for all or selected segments
    of a completed translation job.
    """
    # Get the translation job
    job = db.query(TranslationJob).filter(
        TranslationJob.id == job_id,
        TranslationJob.owner_id == current_user.get("id")
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
    db.commit()
    
    # Start background generation
    background_tasks.add_task(
        generate_illustrations_task,
        job_id=job_id,
        config=config,
        api_key=api_key,
        max_illustrations=max_illustrations,
        db_session=db
    )
    
    return {
        "message": "Illustration generation started",
        "job_id": job_id,
        "status": "IN_PROGRESS"
    }


@router.get("/{job_id}/illustrations")
async def get_job_illustrations(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all illustrations for a translation job.
    
    Returns metadata about all generated illustrations for the specified job.
    """
    # Get the translation job
    job = db.query(TranslationJob).filter(
        TranslationJob.id == job_id,
        TranslationJob.owner_id == current_user.get("id")
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Translation job not found")
    
    if not job.illustrations_data:
        return {
            "job_id": job_id,
            "illustrations": [],
            "status": job.illustrations_status or "NOT_STARTED",
            "count": 0
        }
    
    return {
        "job_id": job_id,
        "illustrations": job.illustrations_data,
        "status": job.illustrations_status,
        "count": job.illustrations_count,
        "directory": job.illustrations_directory
    }


@router.get("/{job_id}/illustration/{segment_index}")
async def get_illustration_image(
    job_id: int,
    segment_index: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific illustration image file.
    
    Returns the actual image file for download or display.
    """
    # Get the translation job
    job = db.query(TranslationJob).filter(
        TranslationJob.id == job_id,
        TranslationJob.owner_id == current_user.get("id")
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Translation job not found")
    
    if not job.illustrations_directory:
        raise HTTPException(status_code=404, detail="No illustrations generated for this job")
    
    # Construct the image path
    image_filename = f"segment_{segment_index:04d}_illustration.png"
    image_path = Path(job.illustrations_directory) / image_filename
    
    if not image_path.exists():
        raise HTTPException(status_code=404, detail=f"Illustration not found for segment {segment_index}")
    
    return FileResponse(
        path=str(image_path),
        media_type="image/png",
        filename=image_filename
    )


@router.delete("/{job_id}/illustration/{segment_index}")
async def delete_illustration(
    job_id: int,
    segment_index: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a specific illustration.
    
    Removes the illustration file and updates the job metadata.
    """
    # Get the translation job
    job = db.query(TranslationJob).filter(
        TranslationJob.id == job_id,
        TranslationJob.owner_id == current_user.get("id")
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Translation job not found")
    
    if not job.illustrations_directory:
        raise HTTPException(status_code=404, detail="No illustrations generated for this job")
    
    # Construct the image path
    image_filename = f"segment_{segment_index:04d}_illustration.png"
    image_path = Path(job.illustrations_directory) / image_filename
    
    if not image_path.exists():
        raise HTTPException(status_code=404, detail=f"Illustration not found for segment {segment_index}")
    
    # Delete the file
    try:
        image_path.unlink()
        
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
async def regenerate_illustration(
    job_id: int,
    segment_index: int,
    style_hints: Optional[str] = Query(None, description="Optional style hints for regeneration"),
    api_key: str = Query(..., description="API key for Gemini image generation"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Regenerate an illustration for a specific segment.
    
    This allows regenerating a single illustration with optional new style hints.
    """
    # Get the translation job
    job = db.query(TranslationJob).filter(
        TranslationJob.id == job_id,
        TranslationJob.owner_id == current_user.get("id")
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
        api_key=api_key,
        db_session=db
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
    max_illustrations: Optional[int],
    db_session: Session
):
    """
    Background task to generate illustrations for a translation job.
    
    This function runs in the background to generate illustrations
    without blocking the API response.
    """
    try:
        # Get the job
        job = db_session.query(TranslationJob).filter(TranslationJob.id == job_id).first()
        if not job:
            return
        
        # Initialize illustration generator
        generator = IllustrationGenerator(
            api_key=api_key,
            job_id=job_id,
            enable_caching=config.cache_enabled
        )
        
        # Get segments from the job
        segments = job.translation_segments
        if not segments:
            job.illustrations_status = "FAILED"
            job.illustrations_data = {"error": "No segments found"}
            db_session.commit()
            return
        
        # Prepare segments for illustration
        segments_to_illustrate = []
        for i, segment in enumerate(segments):
            if max_illustrations and len(segments_to_illustrate) >= max_illustrations:
                break
            
            # Check if segment meets criteria
            segment_data = {
                'text': segment.get('source', ''),
                'index': i
            }
            
            # Apply filtering based on config
            if len(segment_data['text']) >= config.min_segment_length:
                if not config.skip_dialogue_heavy or segment_data['text'].count('"') < len(segment_data['text']) / 50:
                    segments_to_illustrate.append(segment_data)
        
        # Generate illustrations
        results = generator.generate_batch_illustrations(
            segments=segments_to_illustrate,
            style_hints=config.style_hints,
            glossary=job.final_glossary
        )
        
        # Update job with results
        job.illustrations_data = results
        job.illustrations_count = sum(1 for r in results if r['success'])
        job.illustrations_directory = str(generator.job_output_dir)
        job.illustrations_status = "COMPLETED"
        
        db_session.commit()
        
    except Exception as e:
        # Update job with error
        job = db_session.query(TranslationJob).filter(TranslationJob.id == job_id).first()
        if job:
            job.illustrations_status = "FAILED"
            job.illustrations_data = {"error": str(e)}
            db_session.commit()


def regenerate_single_illustration(
    job_id: int,
    segment_index: int,
    style_hints: Optional[str],
    api_key: str,
    db_session: Session
):
    """
    Background task to regenerate a single illustration.
    """
    try:
        # Get the job
        job = db_session.query(TranslationJob).filter(TranslationJob.id == job_id).first()
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
        
        # Generate new illustration
        illustration_path, prompt = generator.generate_illustration(
            segment_text=segment.get('source', ''),
            segment_index=segment_index,
            style_hints=style_hints or job.illustrations_config.get('style_hints', ''),
            glossary=job.final_glossary
        )
        
        # Update job metadata
        if illustration_path:
            illustrations_data = job.illustrations_data or []
            
            # Update or add the illustration data
            found = False
            for ill in illustrations_data:
                if ill.get('segment_index') == segment_index:
                    ill['illustration_path'] = illustration_path
                    ill['prompt'] = prompt
                    ill['success'] = True
                    found = True
                    break
            
            if not found:
                illustrations_data.append({
                    'segment_index': segment_index,
                    'illustration_path': illustration_path,
                    'prompt': prompt,
                    'success': True
                })
            
            job.illustrations_data = illustrations_data
            job.illustrations_count = sum(1 for r in illustrations_data if r.get('success'))
            db_session.commit()
            
    except Exception as e:
        print(f"Error regenerating illustration: {e}")