"""
Character Generator for Illustration

Handles character-specific illustration generation including base character images
and scene variations.
"""
import json
import logging
import concurrent.futures
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable
from PIL import Image
from io import BytesIO

from core.translation.usage_tracker import UsageEvent


class CharacterIllustrationGenerator:
    """Handles character-specific illustration generation."""

    def __init__(
        self,
        client,
        base_dir: Path,
        prompt_builder,
        logger=None,
        model_name: str = "gemini-2.5-flash-image-preview",
        usage_callback: Optional[Callable[[UsageEvent], None]] = None,
    ):
        """
        Initialize the character generator.

        Args:
            client: Gemini API client
            base_dir: Base directory for character illustrations
            prompt_builder: IllustrationPromptBuilder instance
            logger: Optional TranslationLogger instance
            model_name: Name of the Gemini model to use for image generation
        """
        self.client = client
        self.base_dir = base_dir
        self.prompt_builder = prompt_builder
        self.logger = logger
        self.model_name = model_name
        self.usage_callback = usage_callback
        self._setup_base_directory()

    def _setup_base_directory(self) -> Path:
        """Ensure a subdirectory exists for character base images."""
        base_dir = self.base_dir / "base"
        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir

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
            reference_image: Optional reference image as tuple of (bytes, mime_type)
            context_text: Optional context text for world inference
            max_retries: Maximum number of retry attempts

        Returns:
            List of dictionaries: {index, path, prompt, success, type}
        """
        results: List[Dict[str, Any]] = []
        base_dir = self._setup_base_directory()

        # Proactively remove previous base files for the same indices to avoid stale previews
        try:
            for i in range(1, num_variations + 1):
                for ext in ("png", "json"):
                    p = base_dir / f"base_{i:02d}.{ext}"
                    if p.exists():
                        p.unlink()
        except Exception as e:
            logging.warning(f"Failed to cleanup old base files: {e}")

        # Distinct, independent variants to allow user choice
        variant_directives = [
                "masterpiece, best quality, professional character artwork, modern anime style, intricate and clean line art, smooth vibrant coloring, beautifully detailed eyes and hair, upper body portrait",
                 "masterpiece, best quality, character concept art, expressive anime style, textured brushstrokes, painterly coloring, visible line work, close-up portrait",
                "masterpiece, best quality, stylized semi-realism, trending on Artstation, smooth digital painting, anime-style face, detailed rendering of hair and skin, waist-up portrait",
        ]

        for i in range(num_variations):
            vh = variant_directives[i % len(variant_directives)]
            prompt = self.prompt_builder.create_character_base_prompt(
                profile,
                style_hints=(style_hints + f". {vh}").strip(),
                context_text=context_text
            )

            # Log the character base prompt
            if self.logger:
                self.logger.log_translation_prompt(i, f"[CHARACTER BASE PROMPT {i+1}]\n{prompt}")

            # File targets
            image_filename = f"base_{i+1:02d}.png"
            image_filepath = base_dir / image_filename
            json_filename = f"base_{i+1:02d}_prompt.json"
            json_filepath = base_dir / json_filename

            success = False
            generated_path: Optional[str] = None

            generated_path = self._generate_single_image(
                prompt=prompt,
                image_filepath=image_filepath,
                json_filepath=json_filepath,
                reference_image=reference_image,
                max_retries=max_retries,
                index=i
            )

            success = generated_path is not None and generated_path.endswith('.png')

            results.append({
                'index': i,
                'illustration_path': generated_path,
                'prompt': prompt,
                'success': success,
                'type': 'image' if success else 'prompt',
                'used_reference': reference_image is not None
            })

        return results

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
            reference_image: Optional reference image as tuple of (bytes, mime_type)
            max_retries: Maximum number of retry attempts
            num_variations: Number of variations to generate
            add_variant_hints: Whether to add variation hints
            target_indices: Optional list of target base indices (0-based) to overwrite

        Returns:
            List of dictionaries: {index, illustration_path, prompt, success, type, used_reference}
        """
        results: List[Dict[str, Any]] = []
        base_dir = self._setup_base_directory()

        # Determine target indices for generation
        if target_indices is not None:
            indices_to_use = target_indices
        else:
            indices_to_use = list(range(num_variations))

        # Cleanup previous base files for the targeted indices
        try:
            for idx in indices_to_use:
                for ext in ("png", "json"):
                    p = base_dir / f"base_{idx+1:02d}.{ext}"
                    if p.exists():
                        p.unlink()
        except Exception as e:
            logging.warning(f"Failed to cleanup old base files: {e}")

        # Expand single prompt into multiple variant prompts if requested
        final_prompts: List[str]
        if len(prompts) == 1 and len(indices_to_use) > 1:
            if add_variant_hints:
                variant_directives = [
                    "masterpiece, best quality, professional character artwork, modern anime style, intricate and clean line art, smooth vibrant coloring, beautifully detailed eyes and hair, upper body portrait",
                     "masterpiece, best quality, character concept art, expressive anime style, textured brushstrokes, painterly coloring, visible line work, close-up portrait",
                    "masterpiece, best quality, stylized semi-realism, trending on Artstation, smooth digital painting, anime-style face, detailed rendering of hair and skin, waist-up portrait",
                    ]
                final_prompts = [
                    (prompts[0].strip() + ". " + variant_directives[i % len(variant_directives)]).strip()
                    for i in range(len(indices_to_use))
                ]
            else:
                final_prompts = [prompts[0]] * len(indices_to_use)
        else:
            final_prompts = prompts[:len(indices_to_use)]

        for prompt, idx in zip(final_prompts, indices_to_use):
            # Log the custom base prompt
            if self.logger:
                self.logger.log_translation_prompt(idx, f"[CUSTOM BASE PROMPT {idx+1}]\n{prompt}")

            image_filename = f"base_{idx+1:02d}.png"
            image_filepath = base_dir / image_filename
            json_filename = f"base_{idx+1:02d}_prompt.json"
            json_filepath = base_dir / json_filename

            generated_path = self._generate_single_image(
                prompt=prompt,
                image_filepath=image_filepath,
                json_filepath=json_filepath,
                reference_image=reference_image,
                max_retries=max_retries,
                index=idx
            )

            success = generated_path is not None and generated_path.endswith('.png')

            results.append({
                'index': idx,
                'illustration_path': generated_path,
                'prompt': prompt,
                'success': success,
                'type': 'image' if success else 'prompt',
                'used_reference': reference_image is not None
            })

        return results

    def _generate_single_image(self,
                              prompt: str,
                              image_filepath: Path,
                              json_filepath: Path,
                              reference_image: Optional[Tuple[bytes, str]] = None,
                              max_retries: int = 3,
                              index: int = 0) -> Optional[str]:
        """
        Generate a single image using the Gemini API.

        Args:
            prompt: The prompt for image generation
            image_filepath: Path to save the generated image
            json_filepath: Path to save the prompt if generation fails
            reference_image: Optional reference image
            max_retries: Maximum number of retry attempts
            index: Index for logging

        Returns:
            Path to generated file or None on failure
        """
        try:
            from google.genai import types
        except ImportError:
            logging.error("google-genai package not installed")
            return None

        for attempt in range(max_retries):
            try:
                contents: List[Any] = []
                if reference_image is not None:
                    ref_bytes, ref_mime = reference_image
                    try:
                        part = types.Part.from_bytes(data=ref_bytes, mime_type=ref_mime or 'image/png')
                        contents.append(part)
                    except Exception as e:
                        logging.warning(f"Failed to attach reference image part: {e}")
                contents.append(prompt)

                # Add timeout to prevent hanging
                def generate_with_timeout():
                    return self.client.models.generate_content(
                        model=self.model_name,
                        contents=contents
                    )

                # Use ThreadPoolExecutor with timeout
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(generate_with_timeout)
                    try:
                        # 120 second timeout for image generation
                        response = future.result(timeout=120)
                        logging.info(f"[ILLUSTRATION] Received response from Gemini API for generation")
                    except concurrent.futures.TimeoutError:
                        logging.error(f"[ILLUSTRATION] Timeout waiting for Gemini API response")
                        future.cancel()
                        raise Exception("API call timed out after 120 seconds")

                image_generated = False
                if response and hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        for part in candidate.content.parts:
                            if hasattr(part, 'inline_data') and part.inline_data is not None:
                                image = Image.open(BytesIO(part.inline_data.data))
                                image.save(image_filepath, "PNG")
                                image_generated = True
                                break

                self._emit_usage_event(response)

                if image_generated:
                    return str(image_filepath)

                # Fallback to prompt JSON
                prompt_data = {
                    "index": index,
                    "prompt": prompt,
                    "status": "image_generation_failed",
                    "note": "Image generation failed. Use this prompt with another service."
                }
                with open(json_filepath, 'w', encoding='utf-8') as f:
                    json.dump(prompt_data, f, ensure_ascii=False, indent=2)
                return str(json_filepath)

            except Exception as e:
                logging.error(f"Image generation attempt {attempt+1} failed: {e}")
                if attempt == max_retries - 1:
                    return None

        return None

    def _emit_usage_event(self, response) -> None:
        if not self.usage_callback:
            return
        if response is None:
            return
        metadata = getattr(response, "usage_metadata", None)
        if metadata is None:
            return

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

        event = UsageEvent(
            model_name=self.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

        try:
            self.usage_callback(event)
        except Exception as exc:  # pragma: no cover - defensive
            logging.debug(f"[CharacterIllustrationGenerator] Failed to emit usage event: {exc}")
