"""
Illustration generation Celery tasks

This module provides Celery tasks for generating illustrations for translation jobs,
including character base images and scene illustrations.
"""

from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import os
import json
import traceback

from ..celery_app import celery_app
from .base import TrackedTask
from ..config.database import SessionLocal
from ..config.settings import get_settings
from backend.domains.translation.models import TranslationJob
from core.translation.illustration import IllustrationGenerator
from core.schemas.illustration import IllustrationConfig


@celery_app.task(
    bind=True,
    base=TrackedTask,
    name="backend.celery_tasks.illustrations.generate_illustrations",
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,
    retry_jitter=True,
    acks_late=True
)
def generate_illustrations_task(
    self,
    job_id: int,
    config_dict: dict,
    api_key: str,
    max_illustrations: Optional[int] = None
):
    """
    Generate illustration prompts for a translation job.
    
    Args:
        job_id: Translation job ID
        config_dict: IllustrationConfig as dictionary
        api_key: API key for Gemini
        max_illustrations: Maximum number of illustrations to generate
        
    Returns:
        dict: Result with success status and generated illustrations count
    """
    print(f"[ILLUSTRATIONS TASK] Starting for job {job_id}")
    print(f"[ILLUSTRATIONS TASK] Config: {config_dict}")
    print(f"[ILLUSTRATIONS TASK] Max illustrations: {max_illustrations}")
    
    db = None
    try:
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 100, 'status': 'Initializing...'}
        )
        
        # Create database session
        db = SessionLocal()
        print(f"[ILLUSTRATIONS TASK] Database session created")
        
        # Get the job
        job = db.query(TranslationJob).filter(TranslationJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        print(f"[ILLUSTRATIONS TASK] Job found, initializing generator")
        print(f"[ILLUSTRATIONS TASK] API key provided: {api_key[:10] if api_key else 'None'}...")
        
        # Reconstruct config from dict
        config = IllustrationConfig(**config_dict)
        print(f"[ILLUSTRATIONS TASK] Config cache_enabled: {config.cache_enabled}")
        
        # Initialize illustration generator
        try:
            settings = get_settings()
            generator = IllustrationGenerator(
                api_key=api_key,
                job_id=job_id,
                enable_caching=config.cache_enabled,
                model_name=settings.illustration_model
            )
            print(f"[ILLUSTRATIONS TASK] Generator initialized successfully with model: {settings.illustration_model}")
        except Exception as e:
            print(f"[ILLUSTRATIONS TASK] Error initializing generator: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        # Get segments from the job
        segments = job.translation_segments
        if not segments:
            job.illustrations_status = "FAILED"
            job.illustrations_data = {"error": "No segments found"}
            db.commit()
            raise ValueError("No segments found in translation job")
        
        # Prepare segments for illustration
        segments_to_illustrate = []
        for i, segment in enumerate(segments):
            if max_illustrations and len(segments_to_illustrate) >= max_illustrations:
                break
            
            # Check if segment meets criteria
            segment_data = {
                'text': segment.get('source_text', ''),
                'index': i
            }
            
            # Apply filtering based on config
            if len(segment_data['text']) >= config.min_segment_length:
                if not config.skip_dialogue_heavy or segment_data['text'].count('"') < len(segment_data['text']) / 50:
                    segments_to_illustrate.append(segment_data)
        
        # Generate illustration prompts with progress tracking
        results = []
        total_segments = len(segments_to_illustrate)
        
        print(f"[ILLUSTRATIONS TASK] Will generate illustrations for {total_segments} segments")
        
        # Determine if we have a base selection and profile
        selected_base_index = job.character_base_selected_index
        character_profile = job.character_profile

        # Add a debug flag to disable profile lock for testing
        DISABLE_PROFILE_LOCK = os.environ.get('DISABLE_ILLUSTRATION_PROFILE_LOCK', '').lower() == 'true'
        if DISABLE_PROFILE_LOCK:
            print(f"[ILLUSTRATIONS TASK] WARNING: Profile lock disabled by environment variable")
            use_profile_lock = False
        else:
            use_profile_lock = (selected_base_index is not None) and bool(character_profile)

        print(f"[ILLUSTRATIONS TASK] Profile lock enabled: {use_profile_lock}")
        
        for idx, segment in enumerate(segments_to_illustrate):
            print(f"[ILLUSTRATIONS TASK] Processing segment {idx + 1}/{total_segments} (index: {segment['index']})")
            
            # Update progress
            progress = int(idx / total_segments * 100)
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': progress,
                    'total': 100,
                    'status': f'Generating illustration {idx + 1}/{total_segments}...'
                }
            )
            
            # Prepare prompt and reference image
            custom_prompt = None
            ref_tuple = None

            # Attempt to load selected base image as reference regardless of profile lock
            # (reference usage will still be gated by config below)
            try:
                bases = job.character_base_images or []
                if selected_base_index is not None:
                    print(f"[ILLUSTRATIONS TASK] Number of base images available: {len(bases)}")
                    if 0 <= selected_base_index < len(bases):
                        base_path = bases[selected_base_index].get('illustration_path')
                        print(f"[ILLUSTRATIONS TASK] Base path from DB: {base_path}")
                        if base_path and not os.path.isabs(base_path) and job.character_base_directory:
                            base_path = str(Path(job.character_base_directory) / Path(base_path).name)
                            print(f"[ILLUSTRATIONS TASK] Resolved base path: {base_path}")
                        if base_path and base_path.endswith('.png') and os.path.exists(base_path):
                            with open(base_path, 'rb') as bf:
                                ref_bytes = bf.read()
                            ref_tuple = (ref_bytes, 'image/png')
                            print(f"[ILLUSTRATIONS TASK] Reference image loaded, size: {len(ref_bytes)} bytes")
                        else:
                            print(f"[ILLUSTRATIONS TASK] No PNG base found for reference at: {base_path}")
            except Exception as e:
                print(f"[ILLUSTRATIONS TASK] Error loading base reference image: {e}")
                traceback.print_exc()

            if use_profile_lock:
                print(f"[ILLUSTRATIONS TASK] Using profile lock for segment {segment['index']}")
                print(f"[ILLUSTRATIONS TASK] Selected base index: {selected_base_index}")
                print(f"[ILLUSTRATIONS TASK] Character profile exists: {bool(character_profile)}")
                
                context_text = None
                if segment['index'] > 0 and segment['index'] < len(segments):
                    prev = segments[segment['index'] - 1]
                    context_text = prev.get('source_text') or prev.get('text') or None
                
                try:
                    custom_prompt = generator.create_scene_prompt_with_profile(
                        segment_text=segment['text'],
                        context=context_text,
                        profile=character_profile,
                        style_hints=config.style_hints
                    )
                    print(f"[ILLUSTRATIONS TASK] Created custom prompt: {custom_prompt[:100]}...")
                except Exception as e:
                    print(f"[ILLUSTRATIONS TASK] Error creating custom prompt: {e}")
                    custom_prompt = None
            else:
                print(f"[ILLUSTRATIONS TASK] Not using profile lock for segment {segment['index']}")
            
            # Generate illustration for this segment
            print(f"[ILLUSTRATIONS TASK] Calling generator.generate_illustration for segment {segment['index']}")
            print(f"[ILLUSTRATIONS TASK] Text length: {len(segment['text'])} chars")
            print(f"[ILLUSTRATIONS TASK] Has custom prompt: {custom_prompt is not None}")
            print(f"[ILLUSTRATIONS TASK] Has reference image: {ref_tuple is not None}")
            
            # Decide whether to use the selected base image as a reference
            use_reference = False
            if ref_tuple is not None and getattr(config, 'allow_reference_images', True):
                if getattr(config, 'reference_image_source', 'base_selection') == 'base_selection':
                    use_reference = True

            # If we plan to use reference, add a short instruction to the prompt
            effective_prompt = custom_prompt
            if use_reference and effective_prompt:
                effective_prompt = (
                    effective_prompt
                    + ". Use the attached reference image to preserve identity; do not copy any reference background."
                )

            # Extract world_atmosphere data if available in the segment
            world_atmosphere_data = None
            if segment['index'] < len(segments):
                full_segment = segments[segment['index']]
                if isinstance(full_segment, dict):
                    world_atmosphere_data = full_segment.get('world_atmosphere')

            print(f"[ILLUSTRATIONS TASK] World atmosphere data available: {world_atmosphere_data is not None}")
            if world_atmosphere_data:
                print(f"[ILLUSTRATIONS TASK] World atmosphere keys: {list(world_atmosphere_data.keys()) if isinstance(world_atmosphere_data, dict) else 'N/A'}")

            try:
                illustration_path, prompt = generator.generate_illustration(
                    segment_text=segment['text'],
                    segment_index=segment['index'],
                    style_hints=config.style_hints,
                    glossary=job.final_glossary,
                    world_atmosphere=world_atmosphere_data,
                    custom_prompt=effective_prompt,
                    reference_image=(ref_tuple if use_reference else None)
                )
                
                print(f"[ILLUSTRATIONS TASK] Completed generation for segment {segment['index']}")
                print(f"[ILLUSTRATIONS TASK] Result path: {illustration_path}")
            except Exception as e:
                print(f"[ILLUSTRATIONS TASK] Error generating illustration for segment {segment['index']}: {e}")
                
                # Just log the error and continue without retry since we're already not using reference
                print(f"[ILLUSTRATIONS TASK] Generation failed, continuing without image")
                illustration_path = None
                prompt = None
            
            # Determine if it's an image or prompt
            file_type = 'image' if illustration_path and illustration_path.endswith('.png') else 'prompt'
            
            result = {
                'segment_index': segment['index'],
                'illustration_path': illustration_path,
                'prompt': prompt,
                'success': illustration_path is not None,
                'type': file_type,
                'reference_used': bool(use_reference)
            }
            if use_profile_lock:
                result['used_base_index'] = selected_base_index
                result['consistency_mode'] = 'profile_locked'
            results.append(result)
            
            # Update job progress in database
            job.illustrations_progress = progress
            db.commit()
        
        # Update job with final results
        job.illustrations_data = results
        job.illustrations_count = sum(1 for r in results if r['success'])
        job.illustrations_directory = str(generator.job_output_dir)
        job.illustrations_status = "COMPLETED"
        job.illustrations_progress = 100
        
        db.commit()
        
        # Final task state
        self.update_state(
            state='SUCCESS',
            meta={
                'current': 100,
                'total': 100,
                'status': f'Generated {job.illustrations_count} illustrations',
                'result': {
                    'success': True,
                    'count': job.illustrations_count,
                    'directory': job.illustrations_directory
                }
            }
        )
        
        return {
            'success': True,
            'count': job.illustrations_count,
            'directory': job.illustrations_directory
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"[ILLUSTRATIONS TASK] Error: {error_msg}")
        traceback.print_exc()
        
        # Update job with error
        if db:
            try:
                job = db.query(TranslationJob).filter(TranslationJob.id == job_id).first()
                if job:
                    job.illustrations_status = "FAILED"
                    job.illustrations_data = {"error": error_msg}
                    job.illustrations_progress = 0
                    db.commit()
            except:
                pass
        
        # Retry if transient error
        if self.request.retries < self.max_retries:
            print(f"[ILLUSTRATIONS TASK] Retrying... (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        
        # Final failure
        self.update_state(
            state='FAILURE',
            meta={
                'exc_type': type(e).__name__,
                'exc_message': error_msg,
                'status': 'Failed to generate illustrations'
            }
        )
        
        raise
        
    finally:
        # Always close the database session
        if db:
            db.close()


@celery_app.task(
    bind=True,
    base=TrackedTask,
    name="backend.celery_tasks.illustrations.regenerate_single",
    max_retries=2,
    default_retry_delay=30,
    retry_backoff=True,
    acks_late=True
)
def regenerate_single_illustration(
    self,
    job_id: int,
    segment_index: int,
    style_hints: Optional[str],
    api_key: str
):
    """
    Regenerate a single illustration prompt.
    
    Args:
        job_id: Translation job ID
        segment_index: Index of the segment to regenerate
        style_hints: Optional style hints for regeneration
        api_key: API key for Gemini
        
    Returns:
        dict: Result with success status
    """
    db = None
    try:
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'status': f'Regenerating illustration for segment {segment_index}...'}
        )
        
        # Create database session
        db = SessionLocal()
        
        # Get the job
        job = db.query(TranslationJob).filter(TranslationJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Initialize illustration generator
        settings = get_settings()
        generator = IllustrationGenerator(
            api_key=api_key,
            job_id=job_id,
            enable_caching=False,  # Don't use cache for regeneration
            model_name=settings.illustration_model
        )
        
        # Get the segment
        segments = job.translation_segments
        if not segments or segment_index >= len(segments):
            raise ValueError(f"Segment {segment_index} not found")
        
        segment = segments[segment_index]

        # Extract world_atmosphere data if available
        world_atmosphere_data = None
        if isinstance(segment, dict):
            world_atmosphere_data = segment.get('world_atmosphere')

        print(f"[REGENERATE ILLUSTRATION] World atmosphere data available: {world_atmosphere_data is not None}")

        # If base selection exists, build a custom prompt using profile lock
        custom_prompt = None
        ref_tuple = None
        if job.character_base_selected_index is not None and job.character_profile:
            custom_prompt = generator.create_scene_prompt_with_profile(
                segment_text=segment.get('source_text', ''),
                context=None,
                profile=job.character_profile,
                style_hints=style_hints or (job.illustrations_config.get('style_hints', '') if job.illustrations_config else '')
            )

            # Optionally attach the selected base as a reference image
            try:
                bases = job.character_base_images or []
                idx = job.character_base_selected_index
                if 0 <= idx < len(bases):
                    base_path = bases[idx].get('illustration_path')
                    if base_path and not os.path.isabs(base_path) and job.character_base_directory:
                        base_path = str(Path(job.character_base_directory) / Path(base_path).name)
                    if base_path and base_path.endswith('.png') and os.path.exists(base_path):
                        with open(base_path, 'rb') as bf:
                            ref_bytes = bf.read()
                        ref_tuple = (ref_bytes, 'image/png')
            except Exception:
                ref_tuple = None

        # Decide reference usage based on config
        allow_ref = False
        cfg = job.illustrations_config or {}
        if cfg.get('allow_reference_images', True) and cfg.get('reference_image_source', 'base_selection') == 'base_selection':
            if ref_tuple is not None:
                allow_ref = True

        # If using reference, clarify how to use it without copying background
        if allow_ref and custom_prompt:
            custom_prompt = (
                custom_prompt +
                ". Use the attached reference image to preserve identity; do not copy any reference background."
            )

        # Generate new illustration prompt (with reference if allowed)
        prompt_path, prompt = generator.generate_illustration(
            segment_text=segment.get('source_text', ''),
            segment_index=segment_index,
            style_hints=style_hints or (job.illustrations_config.get('style_hints', '') if job.illustrations_config else ''),
            glossary=job.final_glossary,
            world_atmosphere=world_atmosphere_data,
            custom_prompt=custom_prompt,
            reference_image=(ref_tuple if allow_ref else None)
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
                    ill['reference_used'] = bool(allow_ref)
                    found = True
                    break
            
            if not found:
                illustrations_data.append({
                    'segment_index': segment_index,
                    'illustration_path': prompt_path,
                    'prompt': prompt,
                    'success': True,
                    'type': 'image' if prompt_path.endswith('.png') else 'prompt',
                    'reference_used': bool(allow_ref)
                })
            
            job.illustrations_data = illustrations_data
            job.illustrations_count = sum(1 for r in illustrations_data if r.get('success'))
            db.commit()
        
        # Final task state
        self.update_state(
            state='SUCCESS',
            meta={
                'status': f'Successfully regenerated illustration for segment {segment_index}',
                'result': {
                    'success': True,
                    'segment_index': segment_index,
                    'illustration_path': prompt_path
                }
            }
        )
        
        return {
            'success': True,
            'segment_index': segment_index,
            'illustration_path': prompt_path
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"[REGENERATE ILLUSTRATION] Error: {error_msg}")
        traceback.print_exc()
        
        # Retry if transient error
        if self.request.retries < self.max_retries:
            print(f"[REGENERATE ILLUSTRATION] Retrying... (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))
        
        # Final failure
        self.update_state(
            state='FAILURE',
            meta={
                'exc_type': type(e).__name__,
                'exc_message': error_msg,
                'status': f'Failed to regenerate illustration for segment {segment_index}'
            }
        )
        
        raise
        
    finally:
        # Always close the database session
        if db:
            db.close()


# Re-export for convenience
__all__ = [
    'generate_illustrations_task',
    'regenerate_single_illustration'
]
