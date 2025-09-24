"""
Main Illustration Generator Module

Orchestrates illustration generation by coordinating between various components:
cache management, prompt building, visual extraction, and image generation.
"""
import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

from shared.utils.logging import TranslationLogger
from shared.errors import TranslationError
from ...schemas.illustration import IllustrationStyle

from .cache_manager import IllustrationCacheManager
from .visual_extractor import VisualElementExtractor
from .prompt_builder import IllustrationPromptBuilder
from .image_service import ImageGenerationService
from .character_generator import CharacterIllustrationGenerator


# Check if genai is available
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logging.warning("google-genai package not installed. Image generation will be disabled.")


class IllustrationGenerator:
    """
    Handles illustration generation for translation segments using Gemini's image generation API.

    This class orchestrates the illustration generation process by coordinating between:
    - Cache management for avoiding redundant API calls
    - Prompt building from text segments and context
    - Visual element extraction from text
    - Actual image generation via Gemini API
    - Character-specific illustration generation
    """

    def __init__(
        self,
        api_key: Optional[str],
        job_id: Optional[int] = None,
        output_dir: str = "logs/jobs",
        enable_caching: bool = True,
        model_name: str = "gemini-2.5-flash-image-preview",
        client: Optional[genai.Client] = None,
    ):
        """
        Initialize the illustration generator.

        Args:
            api_key: Google API key for Gemini access
            job_id: Optional job ID for tracking and organization
            output_dir: Directory to store generated illustrations
            enable_caching: Whether to cache generated illustrations
            model_name: Name of the Gemini model to use for image generation
        """
        if not GENAI_AVAILABLE:
            raise ImportError("google-genai package is required for illustration generation. "
                            "Please install it with: pip install google-genai")

        if client is not None:
            self.client = client
            logging.info("[ILLUSTRATION] Reusing provided GenAI client instance")
        else:
            if not api_key:
                raise ValueError("API key or Vertex client is required for illustration generation")

            logging.info(f"[ILLUSTRATION] Initializing GenAI client with API key: {api_key[:10]}...")
            try:
                self.client = genai.Client(api_key=api_key)
                logging.info("[ILLUSTRATION] GenAI client initialized successfully")
            except Exception as e:
                logging.error(f"[ILLUSTRATION] Failed to initialize GenAI client: {e}")
                raise

        self.job_id = job_id
        self.output_dir = output_dir
        self.enable_caching = enable_caching
        self.model_name = model_name

        # Setup output directory
        self.job_output_dir = self._setup_output_directory()

        # Initialize logger
        self.logger = TranslationLogger(
            job_id, "illustration_generator",
            job_storage_base=output_dir,
            task_type="illustration"
        ) if job_id else None

        # Initialize components
        self.cache_manager = IllustrationCacheManager(self.job_output_dir, enable_caching)
        self.visual_extractor = VisualElementExtractor()
        self.prompt_builder = IllustrationPromptBuilder(self.visual_extractor)
        self.image_service = ImageGenerationService(
            self.client, self.job_output_dir, self.cache_manager, self.logger, self.model_name
        )
        self.character_generator = CharacterIllustrationGenerator(
            self.client, self.job_output_dir, self.prompt_builder, self.logger, self.model_name
        )

        # Initialize logging session
        if self.logger:
            self.logger.initialize_session()

    def _setup_output_directory(self) -> Path:
        """
        Setup the output directory structure for illustrations.

        Returns:
            Path to the job-specific output directory
        """
        base_dir = Path(self.output_dir)
        if self.job_id:
            job_dir = base_dir / str(self.job_id) / "illustrations"
        else:
            job_dir = base_dir / "default" / "illustrations"

        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir

    def create_illustration_prompt(self,
                                 segment_text: str,
                                 context: Optional[str] = None,
                                 style_hints: str = "",
                                 glossary: Optional[Dict[str, str]] = None,
                                 world_atmosphere=None) -> str:
        """
        Create an illustration prompt from segment text.

        Args:
            segment_text: The text segment to illustrate
            context: Optional context from previous segments
            style_hints: Style preferences for the illustration
            glossary: Optional glossary for character/place names
            world_atmosphere: World and atmosphere analysis data

        Returns:
            Generated prompt for image generation
        """
        prompt = self.prompt_builder.create_illustration_prompt(
            segment_text, context, style_hints, glossary, world_atmosphere
        )

        # Log prompt generation details if logger available
        if self.logger:
            # Use summary from world atmosphere if available, otherwise fallback to segment text
            segment_preview = ''
            if world_atmosphere:
                # Handle both object and dictionary formats
                if hasattr(world_atmosphere, 'segment_summary'):
                    segment_preview = world_atmosphere.segment_summary
                elif isinstance(world_atmosphere, dict) and 'segment_summary' in world_atmosphere:
                    segment_preview = world_atmosphere['segment_summary']

            if not segment_preview:
                segment_preview = segment_text[:500] if segment_text else ''

            self._log_prompt_generation_details({
                'segment_summary': segment_preview,
                'context_preview': context[:300] if context else None,
                'style_hints': style_hints,
                'has_world_atmosphere': world_atmosphere is not None,
                'glossary_terms': list(glossary.keys()) if glossary else [],
                'final_prompt': prompt,
                'prompt_length': len(prompt)
            })

        return prompt

    def create_character_base_prompt(self,
                                    profile: Dict[str, Any],
                                    style_hints: str = "",
                                    context_text: Optional[str] = None) -> str:
        """
        Build a minimal prompt anchored on the protagonist's name only.

        Args:
            profile: Character profile dictionary
            style_hints: Optional style hints
            context_text: Optional context text for world inference

        Returns:
            Character base prompt
        """
        return self.prompt_builder.create_character_base_prompt(
            profile, style_hints, context_text
        )

    def create_scene_prompt_with_profile(self,
                                        segment_text: str,
                                        context: Optional[str],
                                        profile: Dict[str, Any],
                                        style_hints: str = "") -> str:
        """
        Compose a richer scene prompt with profile lock and cinematic details.

        Args:
            segment_text: Current segment text
            context: Previous context
            profile: Character profile for consistency
            style_hints: Optional style hints

        Returns:
            Scene prompt with character consistency
        """
        return self.prompt_builder.create_scene_prompt_with_profile(
            segment_text, context, profile, style_hints
        )

    def generate_illustration(self,
                            segment_text: str,
                            segment_index: int,
                            context: Optional[str] = None,
                            style_hints: str = "",
                            glossary: Optional[Dict[str, str]] = None,
                            world_atmosphere=None,
                            custom_prompt: Optional[str] = None,
                            reference_image: Optional[Tuple[bytes, str]] = None,
                            max_retries: int = 3,
                            character_styles: Optional[Dict[str, str]] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Generate an illustration for a text segment using Gemini's image generation.

        Args:
            segment_text: The text segment to illustrate
            segment_index: Index of the segment for naming
            context: Optional context from previous segments
            style_hints: Style preferences for the illustration
            glossary: Optional glossary for names
            world_atmosphere: World and atmosphere analysis data
            custom_prompt: Optional custom prompt to override automatic generation
            reference_image: Optional reference image as tuple of (bytes, mime_type)
            max_retries: Maximum number of retry attempts
            character_styles: Optional character styles dictionary

        Returns:
            Tuple of (image_file_path, prompt_used) or (None, None) on failure
        """
        # Log full context before generating illustration
        if self.logger:
            context_data = {
                'style_deviation': 'N/A',  # Not available for illustrations
                'contextual_glossary': glossary or {},
                'full_glossary': glossary or {},
                'character_styles': character_styles or {},
                'immediate_context_source': context[:500] if context else 'N/A',
                'immediate_context_ko': 'N/A',  # Korean translation not available here
            }

            # Add world atmosphere data if available
            if world_atmosphere:
                context_data['world_atmosphere'] = {
                    'summary': getattr(world_atmosphere, 'segment_summary', 'N/A'),
                    'physical_world': str(getattr(world_atmosphere, 'physical_world', 'N/A')),
                    'atmosphere': str(getattr(world_atmosphere, 'atmosphere', 'N/A')),
                    'visual_mood': str(getattr(world_atmosphere, 'visual_mood', 'N/A')),
                    'cultural_context': str(getattr(world_atmosphere, 'cultural_context', 'N/A')),
                    'narrative_elements': str(getattr(world_atmosphere, 'narrative_elements', 'N/A')),
                }
            else:
                context_data['world_atmosphere'] = None

            self.logger.log_segment_context(segment_index, context_data)

        # Generate or use custom prompt
        if custom_prompt:
            prompt = custom_prompt
        else:
            prompt = self.create_illustration_prompt(
                segment_text, context, style_hints, glossary, world_atmosphere
            )

        # Generate the illustration
        return self.image_service.generate_illustration(
            segment_text=segment_text,
            segment_index=segment_index,
            prompt=prompt,
            style_hints=style_hints,
            custom_prompt=custom_prompt,
            reference_image=reference_image,
            max_retries=max_retries,
            glossary=glossary,
            world_atmosphere=world_atmosphere,
            character_styles=character_styles
        )

    def generate_batch_illustrations(self,
                                   segments: List[Dict[str, Any]],
                                   style_hints: str = "",
                                   glossary: Optional[Dict[str, str]] = None,
                                   world_atmosphere=None,
                                   parallel: bool = False) -> List[Dict[str, Any]]:
        """
        Generate illustrations for multiple segments.

        Args:
            segments: List of segment dictionaries with 'text' and 'index' keys
            style_hints: Style preferences for all illustrations
            glossary: Optional glossary for names
            world_atmosphere: World atmosphere analysis data
            parallel: Whether to generate in parallel (not implemented yet)

        Returns:
            List of dictionaries with illustration data
        """
        return self.image_service.generate_batch_illustrations(
            segments=segments,
            prompt_builder=self.prompt_builder,
            style_hints=style_hints,
            glossary=glossary,
            world_atmosphere=world_atmosphere,
            parallel=parallel
        )

    def generate_character_bases(self,
                                profile: Dict[str, Any],
                                num_variations: int = 3,
                                style_hints: str = "",
                                reference_image: Optional[Tuple[bytes, str]] = None,
                                context_text: Optional[str] = None,
                                max_retries: int = 3) -> List[Dict[str, Any]]:
        """
        Generate N base character images focusing on appearance only.

        Args:
            profile: Character profile dictionary
            num_variations: Number of variations to generate
            style_hints: Optional style hints
            reference_image: Optional reference image
            context_text: Optional context text for world inference
            max_retries: Maximum number of retry attempts

        Returns:
            List of dictionaries: {index, path, prompt, success, type}
        """
        return self.character_generator.generate_character_bases(
            profile=profile,
            num_variations=num_variations,
            style_hints=style_hints,
            reference_image=reference_image,
            context_text=context_text,
            max_retries=max_retries
        )

    def generate_bases_from_prompts(self,
                                   prompts: List[str],
                                   reference_image: Optional[Tuple[bytes, str]] = None,
                                   max_retries: int = 3,
                                   num_variations: int = 3,
                                   add_variant_hints: bool = True,
                                   target_indices: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """
        Generate base images directly from provided prompts.

        Args:
            prompts: List of prompts
            reference_image: Optional reference image
            max_retries: Maximum number of retry attempts
            num_variations: Number of variations to generate
            add_variant_hints: Whether to add variation hints
            target_indices: Optional list of target indices to overwrite

        Returns:
            List of dictionaries: {index, illustration_path, prompt, success, type, used_reference}
        """
        return self.character_generator.generate_bases_from_prompts(
            prompts=prompts,
            reference_image=reference_image,
            max_retries=max_retries,
            num_variations=num_variations,
            add_variant_hints=add_variant_hints,
            target_indices=target_indices
        )

    def _log_prompt_generation_details(self, log_data: Dict[str, Any]):
        """
        Log detailed prompt generation information to file.

        Args:
            log_data: Dictionary containing prompt generation details
        """
        if not self.logger or not self.job_id:
            return

        # Create a dedicated prompt generation log file
        prompt_gen_log_dir = Path(self.output_dir) / str(self.job_id) / "prompt_generation"
        prompt_gen_log_dir.mkdir(parents=True, exist_ok=True)

        # Generate timestamp for this log entry
        timestamp = datetime.now().isoformat()

        # Create log entry
        log_entry = {
            'timestamp': timestamp,
            'generation_details': log_data
        }

        # Append to prompt generation log file
        log_file = prompt_gen_log_dir / "prompt_generation_log.json"

        # Read existing log if it exists
        existing_logs = []
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    existing_logs = json.load(f)
            except:
                existing_logs = []

        # Append new entry
        existing_logs.append(log_entry)

        # Write back to file
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(existing_logs, f, ensure_ascii=False, indent=2)

    def cleanup_old_illustrations(self, keep_days: int = 30):
        """
        Clean up old illustration files.

        Args:
            keep_days: Number of days to keep illustrations
        """
        import time
        from datetime import timedelta

        cutoff_time = time.time() - (keep_days * 24 * 60 * 60)

        # Clean up both PNG images and JSON prompts
        for pattern in ["*.png", "*.json"]:
            for filepath in self.job_output_dir.glob(pattern):
                if filepath.stat().st_mtime < cutoff_time:
                    try:
                        filepath.unlink()
                        logging.info(f"Deleted old illustration file: {filepath}")
                    except Exception as e:
                        logging.error(f"Failed to delete {filepath}: {e}")

    def get_illustration_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about generated illustrations.

        Returns:
            Dictionary containing illustration metadata
        """
        metadata = {
            'job_id': self.job_id,
            'output_directory': str(self.job_output_dir),
            'total_illustrations': 0,
            'cached_illustrations': 0,
            'illustrations': [],
            'cache_stats': self.cache_manager.get_cache_stats()
        }

        # Count illustrations
        for filepath in self.job_output_dir.glob("*.png"):
            metadata['total_illustrations'] += 1
            metadata['illustrations'].append({
                'filename': filepath.name,
                'path': str(filepath),
                'size': filepath.stat().st_size
            })

        return metadata

    # Expose some methods from components for backward compatibility
    def _extract_visual_elements(self, text: str, glossary: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Backward compatibility wrapper."""
        return self.visual_extractor.extract_visual_elements(text, glossary)

    def _extract_cinematic_details(self, text: str) -> Dict[str, Any]:
        """Backward compatibility wrapper."""
        return self.visual_extractor.extract_cinematic_details(text)

    def _get_character_descriptions(self, character_names: List[str], segment_text: str) -> List[str]:
        """Backward compatibility wrapper."""
        return self.visual_extractor.get_character_descriptions(character_names, segment_text)

    def _infer_world_hints(self, text: Optional[str]) -> Dict[str, str]:
        """Backward compatibility wrapper."""
        return self.visual_extractor.infer_world_hints(text)

    def _create_prompt_from_atmosphere(self, world_atmosphere, segment_text: str,
                                      glossary: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Backward compatibility wrapper."""
        return self.visual_extractor.create_prompt_from_atmosphere(world_atmosphere, segment_text, glossary)
