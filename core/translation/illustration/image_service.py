"""
Image Service for Illustration Generation

Handles actual image generation via Gemini API, including batch processing,
timeout handling, and error management.
"""
import json
import logging
import hashlib
import base64
import concurrent.futures
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List, Callable, Union
from PIL import Image
from io import BytesIO
from datetime import datetime

from core.translation.usage_tracker import UsageEvent


class ImageGenerationService:
    """Handles actual image generation via Gemini API."""

    def __init__(
        self,
        client,
        output_dir: Path,
        cache_manager,
        logger=None,
        model_name: str = "gemini-2.5-flash-image-preview",
        usage_callback: Optional[Callable[[UsageEvent], None]] = None,
    ):
        """
        Initialize the image generation service.

        Args:
            client: Gemini API client
            output_dir: Output directory for generated images
            cache_manager: IllustrationCacheManager instance
            logger: Optional TranslationLogger instance
            model_name: Name of the Gemini model to use for image generation
        """
        self.client = client
        self.output_dir = output_dir
        self.cache_manager = cache_manager
        self.logger = logger
        self.model_name = model_name
        self.usage_callback = usage_callback

    def generate_illustration(self,
                            segment_text: str,
                            segment_index: int,
                            prompt: str,
                            style_hints: str = "",
                            custom_prompt: Optional[str] = None,
                            reference_image: Optional[Tuple[bytes, str]] = None,
                            max_retries: int = 3,
                            glossary: Optional[Dict[str, str]] = None,
                            world_atmosphere=None,
                            character_styles: Optional[Dict[str, str]] = None,
                            return_base64: bool = False) -> Union[Tuple[Optional[str], Optional[str]], Tuple[Optional[Dict], Optional[str]]]:
        """
        Generate an illustration for a text segment using Gemini's image generation.

        Args:
            segment_text: The text segment to illustrate
            segment_index: Index of the segment for naming
            prompt: The generated prompt
            style_hints: Style preferences for the illustration
            custom_prompt: Optional custom prompt to override automatic generation
            reference_image: Optional reference image as tuple of (bytes, mime_type)
            max_retries: Maximum number of retry attempts
            glossary: Optional glossary dictionary (context data, not directly used here)
            world_atmosphere: Optional world atmosphere analysis (context data, not directly used here)
            character_styles: Optional character styles dictionary (context data, not directly used here)
            return_base64: If True, returns base64 data dict instead of file path

        Returns:
            If return_base64 is False: Tuple of (image_file_path, prompt_used) or (None, None) on failure
            If return_base64 is True: Tuple of (data_dict, prompt_used) where data_dict contains base64 image
        """
        # Use custom prompt if provided
        final_prompt = custom_prompt if custom_prompt else prompt

        # Check cache first
        cache_key = None
        if self.cache_manager.enable_caching:
            extra_key = ""
            if custom_prompt:
                extra_key += hashlib.md5(custom_prompt.encode()).hexdigest()
            # If reference image present, add its digest
            if reference_image is not None:
                try:
                    ref_bytes, _ = reference_image
                    extra_key += hashlib.md5(ref_bytes).hexdigest()
                except Exception:
                    pass
            cache_key = self.cache_manager.get_cache_key(segment_text, style_hints, extra_key)

            # Check if we have a cached result
            cached_result = self.cache_manager.get_cached_illustration(cache_key)
            if cached_result:
                cached_path, cached_prompt = cached_result
                logging.info(f"Using cached illustration for segment {segment_index}")
                return cached_path, cached_prompt

        # Log the prompt (context logging is now handled in generator.py)
        if self.logger:
            self.logger.log_translation_prompt(segment_index, f"[ILLUSTRATION PROMPT]\n{final_prompt}")

        # Generate the actual image using Gemini
        for attempt in range(max_retries):
            try:
                result = self._generate_single_illustration(
                    final_prompt, segment_index, reference_image, attempt, max_retries, return_base64
                )

                if result:
                    if return_base64:
                        image_data, prompt_used = result
                        # Note: We don't cache base64 data to avoid memory issues
                        return image_data, prompt_used
                    else:
                        image_filepath, prompt_used = result
                        # Update cache
                        if self.cache_manager.enable_caching and cache_key is not None:
                            self.cache_manager.add_to_cache(cache_key, str(image_filepath),
                                                           prompt_used, segment_index)
                        return str(image_filepath), prompt_used

            except Exception as e:
                logging.error(f"Attempt {attempt + 1} failed to generate illustration for segment {segment_index}: {e}")
                if attempt == max_retries - 1:
                    if self.logger:
                        self.logger.log_error(e, segment_index, "image_generation")
                    return None, None

        return None, None

    def _generate_single_illustration(
        self,
        prompt: str,
        segment_index: int,
        reference_image: Optional[Tuple[bytes, str]],
        attempt: int,
        max_retries: int,
        return_base64: bool = False,
    ) -> Optional[Union[Tuple[Path, str], Tuple[Dict, str]]]:
        """
        Generate a single illustration.

        Args:
            prompt: The prompt for generation
            segment_index: Index of the segment
            reference_image: Optional reference image
            attempt: Current attempt number
            max_retries: Maximum number of retries
            return_base64: If True, returns base64 data instead of saving to disk

        Returns:
            If return_base64 is False: Tuple of (image_path, prompt) or None on failure
            If return_base64 is True: Tuple of (data_dict, prompt) or None on failure
        """
        try:
            from google.genai import types
        except ImportError:
            logging.error("google-genai package not installed")
            return None

        # Prepare output paths and remove stale files before generation
        image_filename = f"segment_{segment_index:04d}.png"
        image_filepath = self.output_dir / image_filename
        json_filename = f"segment_{segment_index:04d}_prompt.json"
        json_filepath = self.output_dir / json_filename

        # Clean up existing files
        for filepath in [image_filepath, json_filepath]:
            try:
                if filepath.exists():
                    filepath.unlink()
            except Exception:
                pass

        # Prepare contents for API call
        contents: List[Any] = []
        if reference_image is not None:
            ref_bytes, ref_mime = reference_image
            try:
                part = types.Part.from_bytes(data=ref_bytes, mime_type=ref_mime or 'image/png')
                contents.append(part)
            except Exception as e:
                logging.warning(f"Failed to attach reference image for segment {segment_index}: {e}")
        contents.append(prompt)

        logging.info(f"[ILLUSTRATION] Calling Gemini API for segment {segment_index}, attempt {attempt + 1}/{max_retries}")
        logging.info(f"[ILLUSTRATION] Using model: {self.model_name}")
        logging.info(f"[ILLUSTRATION] Prompt length: {len(prompt)} chars")

        # Generate with timeout
        response = self._call_api_with_timeout(contents, timeout=120)
        if response is None:
            # Timeout occurred - save prompt as fallback
            if attempt == max_retries - 1:
                return self._save_prompt_fallback(json_filepath, segment_index, prompt,
                                                 "API call timed out after 120 seconds")
            return None

        self._emit_usage_event(response)

        # Process response
        if return_base64:
            image_data = self._extract_image_as_base64(response, segment_index)
            if image_data:
                logging.info(f"Successfully generated image as base64 for segment {segment_index}")
                return image_data, prompt
            else:
                # Return prompt data as fallback
                failure_reason = self._get_failure_reason(response)
                prompt_data = {
                    "segment_index": segment_index,
                    "status": "image_generation_failed",
                    "failure_reason": failure_reason,
                    "note": "Image generation failed. Use this prompt with another service.",
                    "timestamp": datetime.now().isoformat()
                }
                return prompt_data, prompt
        else:
            image_generated = self._extract_image_from_response(response, image_filepath, segment_index)
            if image_generated:
                logging.info(f"Successfully generated image for segment {segment_index}")
                return image_filepath, prompt
            else:
                # Save prompt as fallback
                failure_reason = self._get_failure_reason(response)
                return self._save_prompt_fallback(json_filepath, segment_index, prompt, failure_reason)

    def _call_api_with_timeout(self, contents: List[Any], timeout: int = 120):
        """
        Call Gemini API with timeout.

        Args:
            contents: Content to send to API
            timeout: Timeout in seconds

        Returns:
            API response or None on timeout
        """
        def generate_with_timeout():
            return self.client.models.generate_content(
                model=self.model_name,
                contents=contents
            )

        # Use ThreadPoolExecutor with timeout
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(generate_with_timeout)
            try:
                response = future.result(timeout=timeout)
                logging.info("[ILLUSTRATION] Received response from Gemini API")
                return response
            except concurrent.futures.TimeoutError:
                logging.error("[ILLUSTRATION] Timeout waiting for Gemini API response")
                future.cancel()
                return None

    def _extract_image_from_response(self, response, image_filepath: Path, segment_index: int) -> bool:
        """
        Extract image from API response and save it.

        Args:
            response: API response
            image_filepath: Path to save the image
            segment_index: Segment index for logging

        Returns:
            True if image was successfully extracted and saved
        """
        if not response or not hasattr(response, 'candidates') or not response.candidates:
            logging.warning(f"No candidates in response for segment {segment_index}")
            return False

        candidate = response.candidates[0]

        # Check for content filtering
        if hasattr(candidate, 'finish_reason'):
            finish_reason = str(candidate.finish_reason)
            if 'SAFETY' in finish_reason or 'BLOCKED' in finish_reason:
                logging.warning(f"Content filtering triggered for segment {segment_index}: {finish_reason}")
                if hasattr(candidate, 'safety_ratings'):
                    logging.warning(f"Safety ratings: {candidate.safety_ratings}")

        if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
            for part in candidate.content.parts:
                # Log text responses (often contain explanations)
                if hasattr(part, 'text') and part.text:
                    logging.info(f"Text response for segment {segment_index}: {part.text[:200]}")

                # Check for image data
                if hasattr(part, 'inline_data') and part.inline_data is not None:
                    # Save the generated image
                    image = Image.open(BytesIO(part.inline_data.data))
                    image.save(image_filepath, "PNG")
                    return True

        return False

    def _extract_image_as_base64(self, response, segment_index: int) -> Optional[Dict]:
        """
        Extract image from API response and return as base64 data.

        Args:
            response: API response
            segment_index: Segment index for logging

        Returns:
            Dictionary with base64 image data or None if extraction failed
        """
        if not response or not hasattr(response, 'candidates') or not response.candidates:
            logging.warning(f"No candidates in response for segment {segment_index}")
            return None

        candidate = response.candidates[0]

        # Check for content filtering
        if hasattr(candidate, 'finish_reason'):
            finish_reason = str(candidate.finish_reason)
            if 'SAFETY' in finish_reason or 'BLOCKED' in finish_reason:
                logging.warning(f"Content filtering triggered for segment {segment_index}: {finish_reason}")
                if hasattr(candidate, 'safety_ratings'):
                    logging.warning(f"Safety ratings: {candidate.safety_ratings}")

        if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
            for part in candidate.content.parts:
                # Log text responses (often contain explanations)
                if hasattr(part, 'text') and part.text:
                    logging.info(f"Text response for segment {segment_index}: {part.text[:200]}")

                # Check for image data
                if hasattr(part, 'inline_data') and part.inline_data is not None:
                    # Convert image to base64
                    try:
                        # Get the raw bytes
                        image_bytes = part.inline_data.data

                        # Convert to PIL Image to ensure it's valid and to standardize format
                        image = Image.open(BytesIO(image_bytes))

                        # Save to BytesIO in PNG format
                        buffer = BytesIO()
                        image.save(buffer, format="PNG")
                        buffer.seek(0)

                        # Convert to base64
                        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

                        return {
                            "segment_index": segment_index,
                            "type": "image",
                            "data": image_base64,
                            "mime_type": "image/png",
                            "timestamp": datetime.now().isoformat()
                        }
                    except Exception as e:
                        logging.error(f"Failed to convert image to base64 for segment {segment_index}: {e}")
                        return None

        return None

    def _get_failure_reason(self, response) -> str:
        """
        Determine the reason for generation failure.

        Args:
            response: API response

        Returns:
            Failure reason string
        """
        if response and hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'finish_reason'):
                finish_reason = str(candidate.finish_reason)
                if 'SAFETY' in finish_reason or 'BLOCKED' in finish_reason:
                    return f"content_filtering: {finish_reason}"
                elif 'STOP' in finish_reason:
                    return "model_chose_not_to_generate_image"
        return "unknown"

    def _save_prompt_fallback(self, json_filepath: Path, segment_index: int,
                             prompt: str, failure_reason: str) -> Tuple[str, str]:
        """
        Save prompt as JSON fallback when image generation fails.

        Args:
            json_filepath: Path to save the JSON
            segment_index: Segment index
            prompt: The prompt that failed
            failure_reason: Reason for failure

        Returns:
            Tuple of (json_path, prompt)
        """
        logging.warning(f"No image generated for segment {segment_index}, saving prompt instead")
        logging.debug(f"Prompt that failed: {prompt[:200]}...")

        prompt_data = {
            "segment_index": segment_index,
            "prompt": prompt,
            "status": "image_generation_failed",
            "failure_reason": failure_reason,
            "note": "Image generation failed. Use this prompt with another service.",
            "timestamp": datetime.now().isoformat()
        }

        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(prompt_data, f, ensure_ascii=False, indent=2)

        return str(json_filepath), prompt

    def _log_generation_context(self, segment_index: int, segment_text: str,
                               style_hints: str, custom_prompt: Optional[str],
                               reference_image: Optional[Tuple[bytes, str]]):
        """Log context information for generation.

        Note: This method is deprecated. Context logging is now handled in generator.py
        to include full context data (glossary, world_atmosphere, character_styles).
        This method is kept for backward compatibility.
        """
        # Context logging is now handled in generator.py
        pass

    def generate_batch_illustrations(self,
                                    segments: List[Dict[str, Any]],
                                    prompt_builder,
                                    style_hints: str = "",
                                    glossary: Optional[Dict[str, str]] = None,
                                    world_atmosphere=None,
                                    parallel: bool = False) -> List[Dict[str, Any]]:
        """
        Generate illustrations for multiple segments.

        Args:
            segments: List of segment dictionaries with 'text' and 'index' keys
            prompt_builder: IllustrationPromptBuilder instance
            style_hints: Style preferences for all illustrations
            glossary: Optional glossary for names
            world_atmosphere: World atmosphere analysis data
            parallel: Whether to generate in parallel (not implemented yet)

        Returns:
            List of dictionaries with illustration data
        """
        results = []

        for i, segment in enumerate(segments):
            segment_text = segment.get('text', '')
            segment_index = segment.get('index', i)

            # Get context from previous segment if available
            context = segments[i-1].get('text', '') if i > 0 else None

            # Create prompt
            prompt = prompt_builder.create_illustration_prompt(
                segment_text=segment_text,
                context=context,
                style_hints=style_hints,
                glossary=glossary,
                world_atmosphere=world_atmosphere
            )

            # Generate illustration
            illustration_path, prompt_used = self.generate_illustration(
                segment_text=segment_text,
                segment_index=segment_index,
                prompt=prompt,
                style_hints=style_hints
            )

            results.append({
                'segment_index': segment_index,
                'illustration_path': illustration_path,
                'prompt': prompt_used,
                'success': illustration_path is not None
            })

        # Log completion
        if self.logger:
            successful_count = sum(1 for r in results if r['success'])
            self.logger.log_completion(len(segments), None)
            logging.info(f"Illustration batch generation completed: {successful_count}/{len(segments)} successful")

        return results

    def _emit_usage_event(self, response) -> None:
        if not self.usage_callback:
            return
        event = self._extract_usage_event(response)
        if event is None:
            return
        try:
            self.usage_callback(event)
        except Exception as exc:  # pragma: no cover - defensive logging
            logging.debug(f"[ImageGenerationService] Failed to emit usage event: {exc}")

    def _extract_usage_event(self, response) -> Optional[UsageEvent]:
        metadata = getattr(response, "usage_metadata", None)
        if metadata is None:
            return None

        prompt = getattr(metadata, "prompt_token_count", None)
        if prompt is None:
            prompt = getattr(metadata, "input_token_count", None)

        completion = getattr(metadata, "candidates_token_count", None)
        if completion is None:
            completion = getattr(metadata, "output_token_count", None)
        if completion is None:
            completion = getattr(metadata, "completion_token_count", None)

        total = getattr(metadata, "total_token_count", None)

        def _coerce(value) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0

        prompt_tokens = _coerce(prompt)
        completion_tokens = _coerce(completion)
        total_tokens = _coerce(total) if total is not None else prompt_tokens + completion_tokens

        return UsageEvent(
            model_name=self.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            timestamp=datetime.utcnow(),
        )
