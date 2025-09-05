"""
Illustration API endpoints

This module provides API endpoints for managing and generating illustrations
for translation segments.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi import Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import os
import json
from pathlib import Path

from ...database import SessionLocal
from ...models import TranslationJob, User
from ...auth import get_required_user
from ...tasks.illustrations import generate_illustrations_task, regenerate_single_illustration
from core.translation.illustration_generator import IllustrationGenerator
from core.schemas.illustration import (
    IllustrationConfig, 
    IllustrationData, 
    IllustrationBatch,
    IllustrationStatus,
    CharacterProfile
)
from ...domains.shared.analysis import StyleAnalysis, CharacterAnalysis

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
    
    # Start illustration generation using Celery
    generate_illustrations_task.delay(
        job_id=job_id,
        config_dict=config.dict(),
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


@router.post("/{job_id}/character/base/generate")
async def generate_character_bases(
    job_id: int,
    request: Request,
    api_key: str = Query(..., description="API key for Gemini"),
    reference_image: UploadFile | None = File(default=None),
    profile_json: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user)
):
    """
    Generate base character images (3 variations) focusing only on appearance.
    """
    job = db.query(TranslationJob).filter(
        TranslationJob.id == job_id,
        TranslationJob.owner_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Translation job not found")

    try:
        # Parse profile from either JSON body or form
        profile_data: dict
        if request.headers.get('content-type', '').startswith('multipart/form-data'):
            if profile_json:
                profile_data = json.loads(profile_json)
            else:
                profile_data = {"name": "Protagonist"}
        else:
            body = await request.json()
            profile_model = CharacterProfile(**body)
            profile_data = profile_model.dict()

        generator = IllustrationGenerator(api_key=api_key, job_id=job_id, enable_caching=False)

        ref_tuple = None
        if reference_image is not None:
            ref_bytes = await reference_image.read()
            ref_mime = reference_image.content_type or 'image/png'
            ref_tuple = (ref_bytes, ref_mime)

        # Ensure protagonist name from core narrative style if none provided
        if not profile_data.get('name'):
            # Prefer existing stored profile name
            if job.character_profile and job.character_profile.get('name'):
                profile_data['name'] = job.character_profile.get('name')
            else:
                # Try extracting using style analysis
                try:
                    style_svc = StyleAnalysis()
                    protagonist = style_svc.extract_protagonist_name(
                        filepath=job.filepath,
                        api_key=api_key,
                        model_name='gemini-2.5-flash'
                    )
                    profile_data['name'] = protagonist or Path(job.filepath).stem
                except Exception:
                    profile_data['name'] = Path(job.filepath).stem

        # Read sample source text to guide minimal world hints
        sample_text = None
        try:
            if job.filepath and os.path.exists(job.filepath):
                with open(job.filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    sample_text = f.read(20000)
        except Exception:
            sample_text = None

        bases = generator.generate_character_bases(
            profile_data,
            num_variations=3,
            style_hints=profile_data.get('extra_style_hints') or "",
            reference_image=ref_tuple,
            context_text=sample_text
        )

        # Persist base info
        job.character_profile = profile_data
        job.character_base_images = bases
        job.character_base_directory = str((generator.job_output_dir / "base").resolve())
        # Reset selection
        job.character_base_selected_index = None
        db.commit()

        return {
            "job_id": job_id,
            "bases": bases,
            "directory": job.character_base_directory
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate character bases: {str(e)}")


@router.post("/{job_id}/character/appearance/analyze")
async def analyze_character_appearance(
    job_id: int,
    api_key: str = Query(..., description="API key for model"),
    protagonist_name: Optional[str] = Query(None, description="Optional protagonist name"),
    model_name: str = Query("gemini-2.5-flash", description="Model name for analysis"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user)
):
    """
    Analyze early novel text to produce appearance-only prompt candidates for the protagonist.
    """
    job = db.query(TranslationJob).filter(
        TranslationJob.id == job_id,
        TranslationJob.owner_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Translation job not found")

    try:
        svc = CharacterAnalysis()
        result = svc.analyze_appearance(
            filepath=job.filepath,
            api_key=api_key,
            model_name=model_name,
            protagonist_name=protagonist_name
        )
        return {
            'job_id': job_id,
            'prompts': result['prompts'],
            'protagonist_name': result['protagonist_name'],
            'sample_size': result['sample_size']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze appearance: {str(e)}")


@router.post("/{job_id}/character/base/generate-from-prompt")
async def generate_base_from_prompt(
    job_id: int,
    request: Request,
    api_key: str = Query(..., description="API key for Gemini"),
    reference_image: UploadFile | None = File(default=None),
    prompts_json: str | None = Form(default=None),
    prompt: str | None = Form(default=None),
    num_variations: int = Query(3, ge=1, le=10, description="How many variants to generate when a single prompt is provided"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user)
):
    """
    Generate base image(s) directly from provided prompt text(s).
    Accepts either JSON body with { prompts: string[] } or multipart with prompts_json/prompt.
    """
    job = db.query(TranslationJob).filter(
        TranslationJob.id == job_id,
        TranslationJob.owner_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Translation job not found")

    # Parse prompts
    prompts: List[str] = []
    if request.headers.get('content-type', '').startswith('application/json'):
        body = await request.json()
        if isinstance(body, dict) and 'prompts' in body and isinstance(body['prompts'], list):
            prompts = [str(p) for p in body['prompts'] if isinstance(p, str) and p.strip()]
        elif 'prompt' in body and isinstance(body['prompt'], str):
            prompts = [body['prompt']]
    else:
        if prompts_json:
            try:
                import json as _json
                data = _json.loads(prompts_json)
                if isinstance(data, list):
                    prompts = [str(p) for p in data if isinstance(p, str) and p.strip()]
            except Exception:
                pass
        if not prompts and prompt:
            prompts = [prompt]

    if not prompts:
        raise HTTPException(status_code=400, detail="No prompt(s) provided")

    try:
        generator = IllustrationGenerator(api_key=api_key, job_id=job_id, enable_caching=False)

        ref_tuple = None
        if reference_image is not None:
            ref_bytes = await reference_image.read()
            ref_mime = reference_image.content_type or 'image/png'
            ref_tuple = (ref_bytes, ref_mime)

        bases = generator.generate_bases_from_prompts(
            prompts=prompts,
            reference_image=ref_tuple,
            num_variations=num_variations,
        )

        # Persist base info
        job.character_base_images = bases
        job.character_base_directory = str((generator.job_output_dir / "base").resolve())
        job.character_base_selected_index = None
        db.commit()

        return {
            'job_id': job_id,
            'bases': bases,
            'directory': job.character_base_directory
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate base from prompt: {str(e)}")


@router.get("/{job_id}/character/base")
async def get_character_bases(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user)
):
    """
    Get generated base character images and current selection.
    """
    job = db.query(TranslationJob).filter(
        TranslationJob.id == job_id,
        TranslationJob.owner_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Translation job not found")

    return {
        "job_id": job_id,
        "profile": job.character_profile,
        "bases": job.character_base_images or [],
        "selected_index": job.character_base_selected_index,
        "directory": job.character_base_directory
    }


@router.get("/{job_id}/character/base/{index}")
async def get_character_base_asset(
    job_id: int,
    index: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user)
):
    """
    Get a specific base asset (image if available, otherwise prompt JSON).
    """
    job = db.query(TranslationJob).filter(
        TranslationJob.id == job_id,
        TranslationJob.owner_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Translation job not found")

    if not job.character_base_directory:
        raise HTTPException(status_code=404, detail="No character base assets for this job")

    base_dir = Path(job.character_base_directory)
    image_filename = f"base_{index+1:02d}.png"
    json_filename = f"base_{index+1:02d}_prompt.json"
    image_path = base_dir / image_filename
    json_path = base_dir / json_filename

    if image_path.exists():
        return FileResponse(path=str(image_path), media_type="image/png", filename=image_filename, headers={"Cache-Control": "no-store"})

    if json_path.exists():
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    raise HTTPException(status_code=404, detail="Base asset not found")


class BaseSelectionBody(dict):
    pass


@router.post("/{job_id}/character/base/select")
async def select_character_base(
    job_id: int,
    selection: Dict[str, int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user)
):
    """
    Select one of the generated base images by index.
    """
    job = db.query(TranslationJob).filter(
        TranslationJob.id == job_id,
        TranslationJob.owner_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Translation job not found")

    bases = job.character_base_images or []
    if not bases:
        raise HTTPException(status_code=400, detail="No character bases found for this job")

    selected_index = selection.get("selected_index")
    if selected_index is None or not (0 <= selected_index < len(bases)):
        raise HTTPException(status_code=400, detail="Invalid selected_index")

    job.character_base_selected_index = selected_index
    db.commit()

    return {"message": "Base image selected", "selected_index": selected_index}


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
        # Return the actual image file with no-store cache header
        return FileResponse(
            path=str(image_path),
            media_type="image/png",
            filename=image_filename,
            headers={"Cache-Control": "no-store"}
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
    
    # Start regeneration using Celery
    regenerate_single_illustration.delay(
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


def _legacy_generate_illustrations_task(
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
        
        # Determine if we have a base selection and profile
        selected_base_index = job.character_base_selected_index
        character_profile = job.character_profile
        use_profile_lock = (selected_base_index is not None) and bool(character_profile)

        for idx, segment in enumerate(segments_to_illustrate):
            print(f"--- [ILLUSTRATIONS TASK] Processing segment {idx + 1}/{total_segments} (index: {segment['index']}) ---")
            # Build custom prompt if profile locking is enabled
            custom_prompt = None
            ref_tuple = None
            if use_profile_lock:
                context_text = None
                if segment['index'] > 0 and segment['index'] < len(segments):
                    prev = segments[segment['index'] - 1]
                    context_text = prev.get('source_text') or prev.get('text') or None
                custom_prompt = generator.create_scene_prompt_with_profile(
                    segment_text=segment['text'],
                    context=context_text,
                    profile=character_profile,
                    style_hints=config.style_hints
                )
                # Attach selected base image as reference if available
                try:
                    bases = job.character_base_images or []
                    if 0 <= selected_base_index < len(bases):
                        base_path = bases[selected_base_index].get('illustration_path')
                        # Resolve relative paths via directory
                        if base_path and not os.path.isabs(base_path) and job.character_base_directory:
                            base_path = str(Path(job.character_base_directory) / Path(base_path).name)
                        if base_path and base_path.endswith('.png') and os.path.exists(base_path):
                            with open(base_path, 'rb') as bf:
                                ref_bytes = bf.read()
                            ref_tuple = (ref_bytes, 'image/png')
                except Exception as e:
                    print(f"--- [ILLUSTRATIONS TASK] Warning: failed to load base reference image: {e} ---")

            # Generate illustration for this segment
            illustration_path, prompt = generator.generate_illustration(
                segment_text=segment['text'],
                segment_index=segment['index'],
                style_hints=config.style_hints,
                glossary=job.final_glossary,
                custom_prompt=custom_prompt,
                reference_image=ref_tuple
            )
            
            # Determine if it's an image or prompt
            file_type = 'image' if illustration_path and illustration_path.endswith('.png') else 'prompt'
            
            result = {
                'segment_index': segment['index'],
                'illustration_path': illustration_path,
                'prompt': prompt,
                'success': illustration_path is not None,
                'type': file_type,
                'reference_used': ref_tuple is not None
            }
            if use_profile_lock:
                result['used_base_index'] = selected_base_index
                result['consistency_mode'] = 'profile_locked'
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


def _legacy_regenerate_single_illustration(
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
        
        # If base selection exists, build a custom prompt using profile lock
        custom_prompt = None
        if job.character_base_selected_index is not None and job.character_profile:
            custom_prompt = generator.create_scene_prompt_with_profile(
                segment_text=segment.get('source_text', ''),
                context=None,
                profile=job.character_profile,
                style_hints=style_hints or (job.illustrations_config.get('style_hints', '') if job.illustrations_config else '')
            )

        # Optionally load selected base as reference image
        ref_tuple = None
        try:
            if job.character_base_selected_index is not None and job.character_base_images:
                idx = job.character_base_selected_index
                bases = job.character_base_images or []
                if 0 <= idx < len(bases):
                    base_path = bases[idx].get('illustration_path')
                    if base_path and not os.path.isabs(base_path) and job.character_base_directory:
                        base_path = str(Path(job.character_base_directory) / Path(base_path).name)
                    if base_path and base_path.endswith('.png') and os.path.exists(base_path):
                        with open(base_path, 'rb') as bf:
                            ref_bytes = bf.read()
                        ref_tuple = (ref_bytes, 'image/png')
        except Exception as e:
            print(f"Warning: failed to attach base reference for regeneration: {e}")

        # Generate new illustration prompt
        prompt_path, prompt = generator.generate_illustration(
            segment_text=segment.get('source_text', ''),  # Fixed: use 'source_text' instead of 'source'
            segment_index=segment_index,
            style_hints=style_hints or (job.illustrations_config.get('style_hints', '') if job.illustrations_config else ''),
            glossary=job.final_glossary,
            custom_prompt=custom_prompt,
            reference_image=ref_tuple
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
                    ill['reference_used'] = ref_tuple is not None
                    found = True
                    break
            
            if not found:
                illustrations_data.append({
                    'segment_index': segment_index,
                    'illustration_path': prompt_path,
                    'prompt': prompt,
                    'success': True,
                    'type': 'image' if prompt_path.endswith('.png') else 'prompt',
                    'reference_used': ref_tuple is not None
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
