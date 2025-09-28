"""
Illustration generation Celery tasks

This module provides Celery tasks for generating illustrations for translation jobs,
including character base images and scene illustrations.
"""

from typing import Optional, List, Dict, Any
from pathlib import Path
import os
import json
import traceback
import time
import logging

from ..celery_app import celery_app
from .base import TrackedTask
from ..config.database import SessionLocal
from ..config.settings import get_settings
from backend.domains.translation.models import TranslationJob, TranslationUsageLog
from backend.domains.shared.provider_context import (
    build_vertex_client,
    provider_context_from_payload,
    vertex_model_resource_name,
)
from core.translation.illustration import IllustrationGenerator
from core.config.loader import load_config
from core.config.builder import DynamicConfigBuilder
from backend.domains.shared.model_factory import ModelAPIFactory
from core.schemas.illustration import IllustrationConfig
from core.translation.usage_tracker import TokenUsageCollector


def _segment_sort_key(segment_key: Any) -> int:
    """Sort helper that safely handles non-numeric keys."""

    try:
        return int(segment_key)
    except (TypeError, ValueError):
        return 0


def _load_segment_from_data(seg_data: Dict[str, Any], seg_id: Optional[int] = None) -> Dict[str, Any]:
    """Construct a normalized segment dictionary from log data."""

    metadata = seg_data.get('metadata', {}) if isinstance(seg_data, dict) else {}

    segment_index = seg_data.get('segment_index') if isinstance(seg_data, dict) else None
    if segment_index is None and seg_id is not None:
        segment_index = seg_id - 1

    segment = {
        'segment_index': segment_index or 0,
        'source_text': seg_data.get('source', {}).get('text', '') if isinstance(seg_data, dict) else '',
        'translated_text': seg_data.get('translation', {}).get('text', '') if isinstance(seg_data, dict) else '',
        'world_atmosphere': metadata.get('world_atmosphere'),
        'chapter_title': metadata.get('chapter_title'),
        'chapter_filename': metadata.get('chapter_filename')
    }

    world_atmosphere = segment.get('world_atmosphere')
    if isinstance(world_atmosphere, dict):
        segment['segment_summary'] = world_atmosphere.get('segment_summary', '')

    return segment


def _persist_usage_events(
    db,
    job: TranslationJob,
    usage_collector: TokenUsageCollector | None,
    usage_category: str = "illustration",
) -> None:
    """Persist collected usage events for the given job."""

    if usage_collector is None:
        return

    events = usage_collector.events()
    if not events:
        return

    owner_id = getattr(job, "owner_id", None)
    if owner_id is None:
        owner = getattr(job, "owner", None)
        owner_id = getattr(owner, "id", None) if owner is not None else None

    if owner_id is None:
        return

    for event in events:
        normalized = event.normalized()
        db.add(
            TranslationUsageLog(
                job_id=job.id,
                user_id=owner_id,
                original_length=0,
                translated_length=0,
                translation_duration_seconds=0,
                model_used=normalized.model_name or "unknown",
                prompt_tokens=normalized.prompt_tokens,
                completion_tokens=normalized.completion_tokens,
                total_tokens=normalized.total_tokens,
                usage_category=usage_category,
            )
        )

    try:
        db.commit()
    except Exception:
        db.rollback()
        logging.exception("Failed to persist illustration usage events for job %s", job.id)
    finally:
        usage_collector.clear()


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
    api_key: Optional[str],
    max_illustrations: Optional[int] = None,
    provider_context: Optional[Dict[str, object]] = None,
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
    usage_collector = TokenUsageCollector()
    job_for_usage: Optional[TranslationJob] = None
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
        job_for_usage = job
        
        print(f"[ILLUSTRATIONS TASK] Job found, initializing generator")
        context = provider_context_from_payload(provider_context)
        provider_name = context.name if context else "gemini"
        print(f"[ILLUSTRATIONS TASK] Provider: {provider_name}")
        print(f"[ILLUSTRATIONS TASK] API key provided: {api_key[:10] if api_key else 'None'}...")

        # Reconstruct config from dict
        config = IllustrationConfig(**config_dict)
        print(f"[ILLUSTRATIONS TASK] Config cache_enabled: {config.cache_enabled}")

        # Initialize illustration generator
        try:
            settings = get_settings()
            client = None
            model_name = settings.illustration_model

            if context and context.name == "vertex":
                client = build_vertex_client(context)
                model_name = vertex_model_resource_name(model_name, context)
            elif not api_key:
                raise ValueError("API key is required for illustration generation")

            generator = IllustrationGenerator(
                api_key=api_key,
                job_id=job_id,
                enable_caching=config.cache_enabled,
                model_name=model_name,
                client=client,
                output_dir=settings.job_storage_base,
                usage_callback=usage_collector.record_event,
            )
            print(f"[ILLUSTRATIONS TASK] Generator initialized successfully with model: {settings.illustration_model}")
        except Exception as e:
            print(f"[ILLUSTRATIONS TASK] Error initializing generator: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        # Prepare a text model for world/atmosphere analysis when needed
        try:
            text_model_name = load_config().get('gemini_model_name', 'gemini-flash-latest')
        except Exception:
            text_model_name = 'gemini-flash-latest'

        try:
            text_model_api_key = None if (context and context.name == "vertex") else api_key
            text_model = ModelAPIFactory.create(
                api_key=text_model_api_key,
                model_name=text_model_name,
                config=load_config(),
                provider_context=context,
                usage_callback=usage_collector.record_event,
            )
            protagonist_name = None
            try:
                if job.character_profile and isinstance(job.character_profile, dict):
                    protagonist_name = job.character_profile.get('name')
            except Exception:
                protagonist_name = None
            if not protagonist_name:
                # Fallback to filename stem as a neutral protagonist label
                protagonist_name = Path(job.filename or "Protagonist").stem or "Protagonist"
            dyn_builder = DynamicConfigBuilder(
                model=text_model,
                protagonist_name=protagonist_name,
                initial_glossary=job.final_glossary or {},
                character_style_model=None,
                turbo_mode=True,  # keep light; we only need world/atmosphere on-demand
            )
        except Exception as e:
            print(f"[ILLUSTRATIONS TASK] Warning: Failed to initialize text model for world/atmosphere analysis: {e}")
            text_model = None
            dyn_builder = None

        # Load segments from log files instead of database for richer metadata
        log_dir = Path(settings.job_storage_base) / str(job_id) / "segments" / "translation"
        segments = []

        if log_dir.exists():
            summary_file = log_dir / "summary.json"
            if summary_file.exists():
                print(f"[ILLUSTRATIONS TASK] Loading segments from {summary_file}")
                try:
                    with open(summary_file, 'r', encoding='utf-8') as f:
                        summary_data = json.load(f)

                    # Extract segments from summary data
                    segments_dict = summary_data.get('segments', {})
                    for seg_id_key in sorted(segments_dict.keys(), key=_segment_sort_key):
                        seg_data = segments_dict[seg_id_key]
                        try:
                            seg_id_int = int(seg_id_key)
                        except (TypeError, ValueError):
                            seg_id_int = None

                        segments.append(_load_segment_from_data(seg_data, seg_id_int))

                    print(f"[ILLUSTRATIONS TASK] Loaded {len(segments)} segments from log summary")
                except Exception as e:
                    print(f"[ILLUSTRATIONS TASK] Error loading from summary.json: {e}")
                    import traceback
                    traceback.print_exc()

            # Fallback: load individual segment files if summary doesn't work
            if not segments:
                print(f"[ILLUSTRATIONS TASK] Attempting to load individual segment files from {log_dir}")
                for seg_file in sorted(log_dir.glob("segment_*.json")):
                    try:
                        with open(seg_file, 'r', encoding='utf-8') as f:
                            seg_data = json.load(f)
                            segments.append(_load_segment_from_data(seg_data))
                    except Exception as e:
                        print(f"[ILLUSTRATIONS TASK] Error loading {seg_file}: {e}")

        # Fallback to database if log files don't exist
        if not segments:
            print(f"[ILLUSTRATIONS TASK] Log files not found, falling back to database")
            segments = job.translation_segments
            if not segments:
                job.illustrations_status = "FAILED"
                job.illustrations_data = {"error": "No segments found in logs or database"}
                db.commit()
                raise ValueError("No segments found in translation job")

        # Log what we found
        print(f"[ILLUSTRATIONS TASK] Total segments loaded: {len(segments)}")
        if segments and segments[0].get('world_atmosphere'):
            print(f"[ILLUSTRATIONS TASK] First segment has world_atmosphere data")

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

            # Extract world_atmosphere data from the segment (now loaded from logs)
            world_atmosphere_data = None
            segment_summary = None

            if segment['index'] < len(segments):
                full_segment = segments[segment['index']]
                if isinstance(full_segment, dict):
                    world_atmosphere_data = full_segment.get('world_atmosphere')
                    segment_summary = full_segment.get('segment_summary', '')

            print(f"[ILLUSTRATIONS TASK] World atmosphere data available: {world_atmosphere_data is not None}")
            if world_atmosphere_data:
                print(f"[ILLUSTRATIONS TASK] World atmosphere keys: {list(world_atmosphere_data.keys()) if isinstance(world_atmosphere_data, dict) else 'N/A'}")
                if segment_summary:
                    print(f"[ILLUSTRATIONS TASK] Segment summary: {segment_summary[:100]}...")

            # If we don't have world/atmosphere data, compute it on-demand
            if not world_atmosphere_data and dyn_builder is not None:
                try:
                    prev_context = None
                    try:
                        if segment['index'] > 0 and segment['index'] < len(segments):
                            prev_seg = segments[segment['index'] - 1]
                            prev_context = prev_seg.get('source_text') or prev_seg.get('text') or None
                    except Exception:
                        prev_context = None
                    analysis = dyn_builder.analyze_world_atmosphere(
                        segment_text=segment['text'],
                        previous_context=prev_context,
                        glossary=job.final_glossary or {},
                        job_base_filename=job.filename or f"job_{job_id}",
                        segment_index=segment['index'],
                    )
                    if analysis is not None:
                        world_atmosphere_data = analysis.model_dump()
                        # Attach to in-memory segment for downstream consistency
                        try:
                            if segment['index'] < len(segments) and isinstance(segments[segment['index']], dict):
                                segments[segment['index']]['world_atmosphere'] = world_atmosphere_data
                        except Exception:
                            pass
                except Exception as wa_exc:
                    print(f"[ILLUSTRATIONS TASK] World/atmosphere analysis failed for segment {segment['index']}: {wa_exc}")

            try:
                # Check if we should return base64 data instead of saving to disk
                return_base64 = settings.illustrations_to_user_side

                illustration_result, prompt = generator.generate_illustration(
                    segment_text=segment['text'],
                    segment_index=segment['index'],
                    style_hints=config.style_hints,
                    glossary=job.final_glossary,
                    world_atmosphere=world_atmosphere_data,
                    custom_prompt=effective_prompt,
                    reference_image=(ref_tuple if use_reference else None),
                    return_base64=return_base64
                )

                print(f"[ILLUSTRATIONS TASK] Completed generation for segment {segment['index']}")
                if return_base64:
                    print(f"[ILLUSTRATIONS TASK] Generated base64 data for client-side storage")
                else:
                    print(f"[ILLUSTRATIONS TASK] Result path: {illustration_result}")
            except Exception as e:
                print(f"[ILLUSTRATIONS TASK] Error generating illustration for segment {segment['index']}: {e}")

                # Just log the error and continue without retry since we're already not using reference
                print(f"[ILLUSTRATIONS TASK] Generation failed, continuing without image")
                illustration_result = None
                prompt = None

            # Determine if it's an image or prompt, and handle base64 data
            result = {
                'segment_index': segment['index'],
                'prompt': prompt,
                'success': illustration_result is not None,
                'reference_used': bool(use_reference)
            }

            if return_base64 and illustration_result and isinstance(illustration_result, dict):
                # Base64 mode - store data directly
                result['type'] = 'base64_image' if illustration_result.get('type') == 'image' else 'prompt'
                result['illustration_data'] = illustration_result
            else:
                # Traditional file-based mode
                result['type'] = 'image' if illustration_result and str(illustration_result).endswith('.png') else 'prompt'
                result['illustration_path'] = str(illustration_result) if illustration_result else None
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
            try:
                if job_for_usage is not None:
                    _persist_usage_events(db, job_for_usage, usage_collector)
            finally:
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
    api_key: Optional[str],
    provider_context: Optional[Dict[str, object]] = None,
    custom_prompt: Optional[str] = None,
    api_token: Optional[str] = None,
):
    """
    Regenerate a single illustration prompt.

    Args:
        job_id: Translation job ID
        segment_index: Index of the segment to regenerate
        style_hints: Optional style hints for regeneration
        api_key: API key for Gemini
        custom_prompt: Optional custom prompt to override automatic generation

    Returns:
        dict: Result with success status
    """
    db = None
    usage_collector = TokenUsageCollector()
    job_for_usage: Optional[TranslationJob] = None
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
        job_for_usage = job
        
        # Initialize illustration generator
        settings = get_settings()
        context = provider_context_from_payload(provider_context)
        provider_name = context.name if context else "gemini"

        client = None
        model_name = settings.illustration_model
        effective_api_key = api_key or api_token

        if context and context.name == "vertex":
            client = build_vertex_client(context)
            model_name = vertex_model_resource_name(model_name, context)
        elif not effective_api_key:
            raise ValueError("API key is required for illustration regeneration")

        generator = IllustrationGenerator(
            api_key=effective_api_key,
            job_id=job_id,
            enable_caching=False,  # Don't use cache for regeneration
            model_name=model_name,
            client=client,
            usage_callback=usage_collector.record_event,
        )
        
        # Prepare a text model for world/atmosphere analysis if needed
        try:
            text_model_name = load_config().get('gemini_model_name', 'gemini-flash-latest')
        except Exception:
            text_model_name = 'gemini-flash-latest'

        text_model = None
        dyn_builder = None
        try:
            text_model_api_key = None if (context and context.name == "vertex") else effective_api_key
            text_model = ModelAPIFactory.create(
                api_key=text_model_api_key,
                model_name=text_model_name,
                config=load_config(),
                provider_context=context,
                usage_callback=usage_collector.record_event,
            )
            protagonist_name = None
            try:
                if job.character_profile and isinstance(job.character_profile, dict):
                    protagonist_name = job.character_profile.get('name')
            except Exception:
                protagonist_name = None
            if not protagonist_name:
                protagonist_name = Path(job.filename or "Protagonist").stem or "Protagonist"
            dyn_builder = DynamicConfigBuilder(
                model=text_model,
                protagonist_name=protagonist_name,
                initial_glossary=job.final_glossary or {},
                character_style_model=None,
                turbo_mode=True,
            )
        except Exception as e:
            print(f"[REGENERATE ILLUSTRATION] Warning: Failed to initialize text model for world/atmosphere analysis: {e}")

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

        # If missing, compute world/atmosphere on-demand
        if world_atmosphere_data is None and dyn_builder is not None:
            try:
                previous_context = None
                try:
                    if segment_index > 0 and segment_index < len(segments):
                        prev_seg = segments[segment_index - 1]
                        if isinstance(prev_seg, dict):
                            previous_context = prev_seg.get('source_text') or prev_seg.get('text') or None
                except Exception:
                    previous_context = None

                analysis = dyn_builder.analyze_world_atmosphere(
                    segment_text=segment.get('source_text', '') or segment.get('text', ''),
                    previous_context=previous_context,
                    glossary=job.final_glossary or {},
                    job_base_filename=job.filename or f"job_{job_id}",
                    segment_index=segment_index,
                )
                if analysis is not None:
                    world_atmosphere_data = analysis.model_dump()
                    # Store back to the segment for future reuse
                    try:
                        segment['world_atmosphere'] = world_atmosphere_data
                        job.translation_segments[segment_index] = segment
                        db.commit()
                    except Exception:
                        pass
            except Exception as wa_exc:
                print(f"[REGENERATE ILLUSTRATION] World/atmosphere analysis failed for segment {segment_index}: {wa_exc}")

        # Preserve any user-supplied custom prompt
        final_custom_prompt = custom_prompt if custom_prompt else None
        profile_locked_prompt = None

        # Build a consistency prompt when profile data exists
        has_profile = bool(job.character_profile)
        if has_profile:
            profile_locked_prompt = generator.create_scene_prompt_with_profile(
                segment_text=segment.get('source_text', ''),
                context=None,
                profile=job.character_profile,
                style_hints=style_hints or (job.illustrations_config.get('style_hints', '') if job.illustrations_config else '')
            )

            if final_custom_prompt is None:
                final_custom_prompt = profile_locked_prompt

        # Always attempt to load the selected base as reference when one is chosen
        ref_tuple = None
        if job.character_base_selected_index is not None:
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
        if allow_ref:
            reference_instruction = "Use the attached reference image to preserve identity; do not copy any reference background."
            prompt_with_reference = final_custom_prompt or profile_locked_prompt
            if prompt_with_reference and reference_instruction not in prompt_with_reference:
                prompt_text = prompt_with_reference.rstrip()
                if not prompt_text.endswith('.'):
                    prompt_text = f"{prompt_text}."
                prompt_with_reference = f"{prompt_text} {reference_instruction}"
            if prompt_with_reference:
                final_custom_prompt = prompt_with_reference

        # Generate new illustration prompt (with reference if allowed)
        return_base64 = settings.illustrations_to_user_side
        illustration_result, prompt = generator.generate_illustration(
            segment_text=segment.get('source_text', ''),
            segment_index=segment_index,
            style_hints=style_hints or (job.illustrations_config.get('style_hints', '') if job.illustrations_config else ''),
            glossary=job.final_glossary,
            world_atmosphere=world_atmosphere_data,
            custom_prompt=final_custom_prompt,
            reference_image=(ref_tuple if allow_ref else None),
            return_base64=return_base64
        )

        # Update job metadata
        if illustration_result:
            illustrations_data = job.illustrations_data or []

            # Update or add the illustration data
            found = False
            for ill in illustrations_data:
                if ill.get('segment_index') == segment_index:
                    ill['prompt'] = prompt
                    ill['success'] = True
                    ill['reference_used'] = bool(allow_ref)
                    if return_base64 and isinstance(illustration_result, dict):
                        ill['type'] = 'base64_image' if illustration_result.get('type') == 'image' else 'prompt'
                        ill['illustration_data'] = illustration_result
                        ill.pop('illustration_path', None)
                    else:
                        path_str = str(illustration_result)
                        ill['type'] = 'image' if path_str.endswith('.png') else 'prompt'
                        ill['illustration_path'] = path_str
                        ill.pop('illustration_data', None)
                    found = True
                    break

            if not found:
                entry = {
                    'segment_index': segment_index,
                    'prompt': prompt,
                    'success': True,
                    'reference_used': bool(allow_ref)
                }
                if return_base64 and isinstance(illustration_result, dict):
                    entry['type'] = 'base64_image' if illustration_result.get('type') == 'image' else 'prompt'
                    entry['illustration_data'] = illustration_result
                else:
                    path_str = str(illustration_result)
                    entry['type'] = 'image' if path_str.endswith('.png') else 'prompt'
                    entry['illustration_path'] = path_str
                illustrations_data.append(entry)

            job.illustrations_data = illustrations_data
            job.illustrations_count = sum(1 for r in illustrations_data if r.get('success'))
            db.commit()

        # Final task state
        result_payload: Dict[str, Any] = {
            'success': True,
            'segment_index': segment_index
        }
        if return_base64 and isinstance(illustration_result, dict):
            result_payload['illustration_data'] = illustration_result
        else:
            result_payload['illustration_path'] = illustration_result if illustration_result else None

        self.update_state(
            state='SUCCESS',
            meta={
                'status': f'Successfully regenerated illustration for segment {segment_index}',
                'result': result_payload
            }
        )

        return result_payload
        
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
            try:
                if job_for_usage is not None:
                    _persist_usage_events(db, job_for_usage, usage_collector)
            finally:
                db.close()


# Re-export for convenience
__all__ = [
    'generate_illustrations_task',
    'regenerate_single_illustration',
    'regenerate_single_base'
]


@celery_app.task(
    bind=True,
    base=TrackedTask,
    name="backend.celery_tasks.illustrations.regenerate_single_base",
    max_retries=2,
    default_retry_delay=30,
    retry_backoff=True,
    acks_late=True
)
def regenerate_single_base(
    self,
    job_id: int,
    base_index: int,
    custom_prompt: str,
    api_key: Optional[str] = None,
    provider_context: Optional[Dict[str, object]] = None,
    api_token: Optional[str] = None,
):
    """
    Regenerate a single character base image with custom prompt.

    Args:
        job_id: Translation job ID
        base_index: Index of the base to regenerate
        custom_prompt: Custom prompt to use for regeneration
        api_key: API key for Gemini
        provider_context: Provider context for Vertex AI

    Returns:
        dict: Result with success status
    """
    db = None
    usage_collector = TokenUsageCollector()
    job_for_usage: Optional[TranslationJob] = None
    try:
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'status': f'Regenerating base {base_index}...'}
        )

        # Create database session
        db = SessionLocal()

        # Get the job
        job = db.query(TranslationJob).filter(TranslationJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        job_for_usage = job

        # Get current bases
        bases = job.character_base_images or []
        if not (0 <= base_index < len(bases)):
            raise ValueError(f"Base index {base_index} not found")

        # Get the base to regenerate
        base_to_regenerate = bases[base_index]
        if not base_to_regenerate:
            raise ValueError(f"No base found at index {base_index}")

        # Initialize illustration generator
        settings = get_settings()
        context = provider_context_from_payload(provider_context)
        provider_name = context.name if context else "gemini"

        client = None
        model_name = settings.illustration_model

        if context and context.name == "vertex":
            client = build_vertex_client(context)
            model_name = vertex_model_resource_name(model_name, context)
        elif not api_key:
            raise ValueError("API key is required for base regeneration. Please provide API key or use Vertex AI provider.")

        generator = IllustrationGenerator(
            api_key=api_key,
            job_id=job_id,
            enable_caching=False,  # Don't use cache for regeneration
            model_name=model_name,
            client=client,
            usage_callback=usage_collector.record_event,
        )

        # Get the character profile for consistency
        profile = job.character_profile or {}

        # Generate new base with custom prompt
        new_bases = generator.generate_bases_from_prompts(
            prompts=[custom_prompt],
            reference_image=None,  # TODO: Could use existing base as reference for consistency
            max_retries=3,
            num_variations=1,
            target_indices=[base_index]
        )

        if new_bases and len(new_bases) > 0:
            new_base = new_bases[0]
            illustration_path = new_base.get('illustration_path')
            logging.info(f"[REGENERATE BASE] Generated path: {illustration_path}")

            if not new_base.get('success') or not illustration_path or not str(illustration_path).endswith('.png'):
                raise ValueError("Image regeneration did not produce a valid PNG. Check the prompt or API response.")

            # Ensure the generated image exists
            image_path = Path(illustration_path)
            if not image_path.exists():
                raise ValueError(f"Generated image file not found at {illustration_path}")

            # Replace the base entry, preserving new prompt
            bases[base_index] = dict(new_base)
            job.character_base_images = bases

            # Update directory if needed
            if not job.character_base_directory:
                job.character_base_directory = str((generator.job_output_dir / "base").resolve())

            db.commit()

            # Final task state
            self.update_state(
                state='SUCCESS',
                meta={
                    'status': f'Successfully regenerated base {base_index}',
                    'result': {
                        'success': True,
                        'base_index': base_index,
                        'updated_base': new_base
                    }
                }
            )

            return {
                'success': True,
                'base_index': base_index,
                'updated_base': new_base
            }
        else:
            raise ValueError("Failed to generate new base image")

    except Exception as e:
        error_msg = str(e)
        print(f"[REGENERATE BASE] Error: {error_msg}")
        traceback.print_exc()

        # Retry if transient error
        if self.request.retries < self.max_retries:
            print(f"[REGENERATE BASE] Retrying... (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))

        # Final failure
        self.update_state(
            state='FAILURE',
            meta={
                'exc_type': type(e).__name__,
                'exc_message': error_msg,
                'status': f'Failed to regenerate base {base_index}'
            }
        )

        raise

    finally:
        # Always close the database session
        if db:
            try:
                if job_for_usage is not None:
                    _persist_usage_events(db, job_for_usage, usage_collector)
            finally:
                db.close()
