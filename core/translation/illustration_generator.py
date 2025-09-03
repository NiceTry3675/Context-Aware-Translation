"""
Illustration Generator Module

This module provides functionality to generate illustrations for translation segments
using Google's Gemini image generation API.
"""

import os
import json
import hashlib
from typing import Optional, Dict, Any, Tuple, List
from pathlib import Path
from PIL import Image
from io import BytesIO
import logging

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logging.warning("google-genai package not installed. Image generation will be disabled.")

from ..utils.logging import TranslationLogger
from ..errors import TranslationError
from ..schemas.illustration import IllustrationStyle


class IllustrationGenerator:
    """
    Handles illustration generation for translation segments using Gemini's image generation API.
    
    This class provides methods to:
    - Analyze text segments and generate appropriate image prompts
    - Generate illustrations using Gemini's image generation model
    - Store and manage generated illustrations
    - Handle errors and fallbacks
    """
    
    def __init__(self, 
                 api_key: str, 
                 job_id: Optional[int] = None,
                 output_dir: str = "illustrations",
                 enable_caching: bool = True):
        """
        Initialize the illustration generator.
        
        Args:
            api_key: Google API key for Gemini access
            job_id: Optional job ID for tracking and organization
            output_dir: Directory to store generated illustrations
            enable_caching: Whether to cache generated illustrations
        """
        if not GENAI_AVAILABLE:
            raise ImportError("google-genai package is required for illustration generation. "
                            "Please install it with: pip install google-genai")
        
        self.client = genai.Client(api_key=api_key)
        self.job_id = job_id
        self.output_dir = output_dir
        self.enable_caching = enable_caching
        self.logger = TranslationLogger(job_id, "illustration_generator") if job_id else None
        
        # Setup output directory
        self.job_output_dir = self._setup_output_directory()
        
        # Cache for generated illustrations
        self.cache = {} if enable_caching else None
        self._load_cache_metadata()
    
    def _setup_output_directory(self) -> Path:
        """
        Setup the output directory structure for illustrations.
        
        Returns:
            Path to the job-specific output directory
        """
        base_dir = Path(self.output_dir)
        if self.job_id:
            job_dir = base_dir / f"job_{self.job_id}"
        else:
            job_dir = base_dir / "default"
        
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir

    def _setup_base_directory(self) -> Path:
        """Ensure a subdirectory exists for character base images."""
        base_dir = self.job_output_dir / "base"
        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir

    def _load_cache_metadata(self):
        """Load existing cache metadata from disk if available."""
        if not self.enable_caching:
            return
        
        cache_file = self.job_output_dir / "cache_metadata.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
            except Exception as e:
                logging.warning(f"Failed to load cache metadata: {e}")
                self.cache = {}
    
    def _save_cache_metadata(self):
        """Save cache metadata to disk."""
        if not self.enable_caching or not self.cache:
            return
        
        cache_file = self.job_output_dir / "cache_metadata.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.warning(f"Failed to save cache metadata: {e}")
    
    def _get_cache_key(self, text: str, style_hints: str = "", extra: str = "") -> str:
        """
        Generate a cache key for the given text and style hints.
        
        Args:
            text: The source text
            style_hints: Optional style hints
            
        Returns:
            MD5 hash as cache key
        """
        combined = f"{text}|||{style_hints}|||{extra}"
        return hashlib.md5(combined.encode()).hexdigest()
    
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
        # Use AI-analyzed world atmosphere if available, otherwise fall back to keyword extraction
        if world_atmosphere:
            visual_elements = self._create_prompt_from_atmosphere(world_atmosphere, segment_text, glossary)
        else:
            # Fallback to simple keyword extraction
            visual_elements = self._extract_visual_elements(segment_text, glossary)
        
        # Build a more descriptive, image-friendly prompt
        base_description = []
        
        # Start with setting
        if visual_elements.get('setting'):
            base_description.append(f"A scene in {visual_elements['setting']}")
        else:
            base_description.append("A scene")
        
        # Add characters with visual descriptions (without names)
        if visual_elements.get('characters'):
            character_descriptions = self._get_character_descriptions(visual_elements['characters'], segment_text)
            if character_descriptions:
                if len(character_descriptions) == 1:
                    base_description.append(f"featuring {character_descriptions[0]}")
                else:
                    base_description.append(f"featuring {', '.join(character_descriptions)}")
        
        # Add action
        if visual_elements.get('action'):
            base_description.append(f"with {visual_elements['action']}")
        
        # Add mood/atmosphere
        if visual_elements.get('mood'):
            base_description.append(f"in a {visual_elements['mood']} atmosphere")
        
        # Combine the base description
        prompt = " ".join(base_description)
        
        # Add style hints at the beginning if provided
        if style_hints:
            prompt = f"{style_hints}. {prompt}"
        
        # Add artistic style at the end
        prompt += ". Digital illustration in anime/manga style, high quality, detailed background, vibrant colors"
        
        # Make sure prompt is safe and appropriate
        prompt = prompt.replace("violent", "dramatic")
        prompt = prompt.replace("blood", "intense")
        prompt = prompt.replace("death", "dramatic moment")
        
        logging.info(f"Generated prompt for image: {prompt[:150]}...")
        
        return prompt

    def _infer_world_hints(self, text: Optional[str]) -> Dict[str, str]:
        """Infer high-level world/genre hints from text without over-specifying details."""
        if not text:
            return {}
        t = text.lower()
        hints: Dict[str, str] = {}
        # Very lightweight heuristics
        fantasy_kw = ["castle", "kingdom", "sword", "knight", "mage", "dungeon", "dragon", "guild", "magic"]
        scifi_kw = ["starship", "spaceship", "planet", "galaxy", "alien", "android", "cyber", "neon", "hacking", "quantum"]
        historical_kw = ["emperor", "dynasty", "samurai", "shogun", "roman", "medieval", "victorian", "monarchy"]
        contemporary_kw = ["school", "classroom", "university", "subway", "smartphone", "apartment", "office", "cafe", "city"]

        def contains_any(words):
            return any(w in t for w in words)

        if contains_any(fantasy_kw):
            hints["genre"] = "fantasy"
        elif contains_any(scifi_kw):
            hints["genre"] = "sci-fi"
        elif contains_any(historical_kw):
            hints["genre"] = "historical"
        elif contains_any(contemporary_kw):
            hints["genre"] = "contemporary"

        # Very light period cue
        if "medieval" in t or "castle" in t or "knight" in t:
            hints["period"] = "medieval"
        elif "victorian" in t:
            hints["period"] = "victorian"
        elif any(k in t for k in ["neon", "cyber", "android", "ai overload"]):
            hints["period"] = "near-future"
        else:
            hints.setdefault("period", "unspecified")

        return hints

    def create_character_base_prompt(self,
                                     profile: Dict[str, Any],
                                     style_hints: str = "",
                                     context_text: Optional[str] = None) -> str:
        """Build a minimal prompt anchored on the protagonist's name only.

        Keeps details sparse to avoid over-specification and downstream lock-in.
        """
        name = str(profile.get('name') or 'Protagonist')

        parts: List[str] = []
        # Optional global style hints (kept generic if present)
        if style_hints:
            parts.append(style_hints)
        if profile.get('extra_style_hints'):
            parts.append(str(profile['extra_style_hints']))

        # High-level world hints inferred from text
        world = self._infer_world_hints(context_text)
        if world.get("genre"):
            parts.append(f"genre: {world['genre']}")
        if world.get("period") and world['period'] != 'unspecified':
            parts.append(f"period vibe: {world['period']}")

        # Minimal identity; instruct NOT to render text or name
        parts.append(
            f"Character design portrait of {name}. Neutral pose. Plain light background. No text, no watermark, do not write the name. No background elements"
        )

        # High-level style preference only
        style_pref = str(profile.get('style') or '').lower()
        if style_pref == 'anime':
            parts.append("Anime character design, clean linework, high quality")
        elif style_pref in ['watercolor', 'sketch', 'realistic', 'artistic', 'digital_art', 'vintage', 'minimalist']:
            parts.append("Digital illustration character design, high quality, consistent lighting")
        else:
            parts.append("Digital illustration character design, high quality, consistent lighting")

        return ". ".join(parts)

    def create_scene_prompt_with_profile(self,
                                         segment_text: str,
                                         context: Optional[str],
                                         profile: Dict[str, Any],
                                         style_hints: str = "") -> str:
        """Compose a scene prompt that locks the character’s appearance while varying scene/action."""
        # Consistency lock
        lock_items = []
        for key in ['hair_color', 'hair_style', 'eye_color', 'eye_shape', 'skin_tone', 'body_type', 'clothing', 'accessories']:
            val = profile.get(key)
            if val:
                lock_items.append(f"{key.replace('_', ' ')}: {val}")
        lock_text = "; ".join(lock_items)
        lock_clause = (
            f"Maintain the exact same character appearance ({lock_text}). Do not change these traits. "
            f"Use the attached reference image to preserve identity (face, hair, overall look); do not copy any reference background"
            if lock_text else
            "Maintain the same character appearance as previously defined. Use the attached reference image to preserve identity; do not copy any reference background"
        )

        # Extract visual elements to emphasize scene context
        elements = self._extract_visual_elements(segment_text, glossary=None)
        setting_txt = elements.get('setting') or 'an appropriate environment'
        action_txt = elements.get('action') or 'a context-appropriate action'
        mood_txt = elements.get('mood') or None

        # Strong scene directive (avoid portraits when scene demanded)
        scene_directives = [
            f"Place the character in {setting_txt}",
            f"showing {action_txt}",
            "compose as a medium or wide shot (not a simple portrait)",
            "include background elements matching the environment, with depth and lighting",
        ]
        if mood_txt:
            scene_directives.append(f"overall atmosphere: {mood_txt}")

        base_scene = ". ".join(scene_directives)

        # Strengthen constraints
        # Style hints come first to bias rendering
        prefix = (style_hints + ". ") if style_hints else ""
        scene_prompt = f"{prefix}{lock_clause}. {base_scene}. No text or watermark in the image."
        return scene_prompt

    def _create_prompt_from_atmosphere(self, world_atmosphere, segment_text: str, glossary: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Create visual elements from AI-analyzed world atmosphere data.

        Args:
            world_atmosphere: WorldAtmosphereAnalysis object with rich context
            segment_text: The text segment
            glossary: Optional glossary for names

        Returns:
            Dictionary of visual elements optimized for illustration
        """
        illustration_context = world_atmosphere.to_illustration_context()

        elements = {
            'setting': illustration_context.get('setting', ''),
            'characters': [],
            'mood': illustration_context.get('mood', ''),
            'action': None,
            'lighting': illustration_context.get('lighting', ''),
            'colors': illustration_context.get('colors', []),
            'weather': illustration_context.get('weather', ''),
            'time': illustration_context.get('time', ''),
            'tension': illustration_context.get('tension', ''),
            'dramatic_weight': illustration_context.get('dramatic_weight', 'medium')
        }

        # Extract characters from glossary if they appear in the text
        if glossary:
            for name in glossary.keys():
                if name in segment_text:
                    elements['characters'].append(name)

        # Determine action based on narrative focus
        focus = illustration_context.get('focus', '')
        if 'conversation' in focus.lower() or 'dialogue' in focus.lower():
            elements['action'] = 'people in conversation'
        elif 'action' in focus.lower() or 'movement' in focus.lower():
            elements['action'] = 'dynamic movement'
        elif 'contemplation' in focus.lower() or 'thinking' in focus.lower():
            elements['action'] = 'quiet contemplation'

        # Enhance mood with tension and dramatic weight
        if elements['tension'] == 'climactic' or elements['dramatic_weight'] == 'high':
            elements['mood'] = f"intense and {elements['mood']}"
        elif elements['tension'] == 'calm':
            elements['mood'] = f"peaceful and {elements['mood']}"

        return elements

    def _extract_visual_elements(self,
                                text: str, 
                                glossary: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Extract visual elements from text for illustration generation.
        
        Args:
            text: The text to analyze
            glossary: Optional glossary for names
            
        Returns:
            Dictionary of visual elements
        """
        elements = {
            'setting': None,
            'characters': [],
            'mood': None,
            'action': None
        }
        
        # Simple keyword-based extraction (can be enhanced with AI)
        text_lower = text.lower()
        
        # Extract setting
        setting_keywords = {
            'room': 'indoor room',
            'house': 'residential house',
            'street': 'urban street',
            'forest': 'forest landscape',
            'office': 'office space',
            'restaurant': 'restaurant interior',
            'park': 'public park',
            'beach': 'beach scenery',
            'mountain': 'mountain landscape'
        }
        
        for keyword, setting in setting_keywords.items():
            if keyword in text_lower:
                elements['setting'] = setting
                break
        
        # Track which characters are present (but store names for reference)
        if glossary:
            for name in glossary.keys():
                if name in text:
                    elements['characters'].append(name)
        
        # Extract mood
        mood_keywords = {
            'happy': 'joyful',
            'sad': 'melancholic',
            'angry': 'tense',
            'peaceful': 'serene',
            'mysterious': 'mysterious',
            'romantic': 'romantic',
            'dark': 'dark and moody',
            'bright': 'bright and cheerful'
        }
        
        for keyword, mood in mood_keywords.items():
            if keyword in text_lower:
                elements['mood'] = mood
                break
        
        # Extract action (simplified)
        action_keywords = {
            'running': 'person running',
            'talking': 'people in conversation',
            'walking': 'person walking',
            'sitting': 'person sitting',
            'eating': 'people dining',
            'working': 'person working',
            'reading': 'person reading'
        }
        
        for keyword, action in action_keywords.items():
            if keyword in text_lower:
                elements['action'] = action
                break
        
        return elements
    
    def _get_character_descriptions(self, character_names: List[str], segment_text: str) -> List[str]:
        """
        Convert character names to generic visual descriptions for illustration.
        Avoids using actual names to prevent them from appearing as text in images.
        
        Args:
            character_names: List of character names found in the segment
            segment_text: The text segment for context
            
        Returns:
            List of generic character descriptions
        """
        descriptions = []
        
        # Map common character archetypes based on context clues
        text_lower = segment_text.lower()
        
        # Create more varied descriptions based on the number of characters
        num_characters = len(character_names)
        
        if num_characters == 1:
            # Single character - try to be more descriptive
            if any(word in text_lower for word in ['child', 'boy', 'kid', 'young']):
                descriptions.append("a young boy")
            elif any(word in text_lower for word in ['girl', 'young woman']):
                descriptions.append("a young woman")
            elif any(word in text_lower for word in ['woman', 'lady', 'female']):
                descriptions.append("a woman")
            elif any(word in text_lower for word in ['man', 'gentleman', 'male']):
                descriptions.append("a man")
            elif any(word in text_lower for word in ['old', 'elderly', 'aged', 'senior']):
                descriptions.append("an elderly person")
            else:
                descriptions.append("a person")
                
        elif num_characters == 2:
            # Two characters - show them in conversation or interaction
            if any(word in text_lower for word in ['talking', 'conversation', 'discussing', 'arguing']):
                descriptions.append("two people in conversation")
            elif any(word in text_lower for word in ['fighting', 'combat', 'battle']):
                descriptions.append("two people in confrontation")
            elif any(word in text_lower for word in ['embracing', 'hugging', 'holding']):
                descriptions.append("two people embracing")
            else:
                descriptions.append("two people together")
                
        elif num_characters >= 3:
            # Multiple characters - describe as a group
            if any(word in text_lower for word in ['meeting', 'gathering', 'assembled']):
                descriptions.append("a group of people gathered")
            elif any(word in text_lower for word in ['crowd', 'audience']):
                descriptions.append("a crowd of people")
            elif any(word in text_lower for word in ['team', 'squad', 'group']):
                descriptions.append("a team of people")
            else:
                descriptions.append(f"a group of {num_characters} people")
        
        # If we still have no descriptions, use generic fallback
        if not descriptions:
            if num_characters == 1:
                descriptions.append("a person")
            elif num_characters == 2:
                descriptions.append("two people")
            else:
                descriptions.append("several people")
        
        return descriptions
    
    def generate_illustration(self, 
                            segment_text: str,
                            segment_index: int,
                            context: Optional[str] = None,
                            style_hints: str = "",
                            glossary: Optional[Dict[str, str]] = None,
                            world_atmosphere=None,
                            custom_prompt: Optional[str] = None,
                            reference_image: Optional[Tuple[bytes, str]] = None,
                            max_retries: int = 3) -> Tuple[Optional[str], Optional[str]]:
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
            
        Returns:
            Tuple of (image_file_path, prompt_used) or (None, None) on failure
        """
        # Initialize cache_key for later use
        cache_key = None
        
        # Check cache first
        if self.enable_caching:
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
            cache_key = self._get_cache_key(segment_text, style_hints, extra_key)
            if cache_key in self.cache:
                cached_path = self.cache[cache_key]['path']
                cached_prompt = self.cache[cache_key]['prompt']
                if Path(cached_path).exists():
                    logging.info(f"Using cached illustration for segment {segment_index}")
                    return cached_path, cached_prompt
        
        # Generate the prompt
        if custom_prompt:
            prompt = custom_prompt
        else:
            prompt = self.create_illustration_prompt(segment_text, context, style_hints, glossary, world_atmosphere)
        
        # Generate the actual image using Gemini
        for attempt in range(max_retries):
            try:
                # Prepare output paths and remove stale files before generation
                image_filename = f"segment_{segment_index:04d}.png"
                image_filepath = self.job_output_dir / image_filename
                json_filename = f"segment_{segment_index:04d}_prompt.json"
                json_filepath = self.job_output_dir / json_filename
                try:
                    if image_filepath.exists():
                        image_filepath.unlink()
                except Exception:
                    pass
                try:
                    if json_filepath.exists():
                        json_filepath.unlink()
                except Exception:
                    pass
                # Use Gemini's image generation model, optionally with reference image
                contents: List[Any] = []
                if reference_image is not None:
                    ref_bytes, ref_mime = reference_image
                    try:
                        part = types.Part.from_bytes(data=ref_bytes, mime_type=ref_mime or 'image/png')
                        contents.append(part)
                    except Exception as e:
                        logging.warning(f"Failed to attach reference image for segment {segment_index}: {e}")
                contents.append(prompt)

                response = self.client.models.generate_content(
                    model="gemini-2.5-flash-image-preview",
                    contents=contents
                )

                # Extract the image from the response
                image_generated = False
                
                # Check if response has candidates and content
                if response and hasattr(response, 'candidates') and response.candidates:
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
                                image_generated = True
                                logging.info(f"Successfully generated image for segment {segment_index}")
                                break
                else:
                    logging.warning(f"No candidates in response for segment {segment_index}")
                    if response:
                        logging.debug(f"Response object: {response}")
                
                if not image_generated:
                    # Fallback: Save prompt as JSON if no image was generated
                    logging.warning(f"No image generated for segment {segment_index}, saving prompt instead")
                    logging.debug(f"Prompt that failed: {prompt[:200]}...")
                    # json_filename/json_filepath prepared above
                    
                    # Determine the failure reason
                    failure_reason = "unknown"
                    if response and hasattr(response, 'candidates') and response.candidates:
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'finish_reason'):
                            finish_reason = str(candidate.finish_reason)
                            if 'SAFETY' in finish_reason or 'BLOCKED' in finish_reason:
                                failure_reason = f"content_filtering: {finish_reason}"
                            elif 'STOP' in finish_reason:
                                failure_reason = "model_chose_not_to_generate_image"
                    
                    prompt_data = {
                        "segment_index": segment_index,
                        "prompt": prompt,
                        "segment_text": segment_text[:500],
                        "style_hints": style_hints,
                        "status": "image_generation_failed",
                        "failure_reason": failure_reason,
                        "note": "Image generation failed. Use this prompt with another service.",
                        "attempt": attempt + 1
                    }
                    
                    with open(json_filepath, 'w', encoding='utf-8') as f:
                        json.dump(prompt_data, f, ensure_ascii=False, indent=2)
                    
                    return str(json_filepath), prompt
                
                # Update cache
                if self.enable_caching and cache_key is not None:
                    self.cache[cache_key] = {
                        'path': str(image_filepath),
                        'prompt': prompt,
                        'segment_index': segment_index
                    }
                    self._save_cache_metadata()
                
                return str(image_filepath), prompt
                
            except Exception as e:
                logging.error(f"Attempt {attempt + 1} failed to generate illustration for segment {segment_index}: {e}")
                if attempt == max_retries - 1:
                    if self.logger:
                        self.logger.log_error(e, segment_index, "image_generation")
                    return None, None
                continue
    
    def generate_batch_illustrations(self, 
                                   segments: List[Dict[str, Any]],
                                   style_hints: str = "",
                                   glossary: Optional[Dict[str, str]] = None,
                                   parallel: bool = False) -> List[Dict[str, Any]]:
        """
        Generate illustrations for multiple segments.
        
        Args:
            segments: List of segment dictionaries with 'text' and 'index' keys
            style_hints: Style preferences for all illustrations
            glossary: Optional glossary for names
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
            
            # Generate illustration
            illustration_path, prompt = self.generate_illustration(
                segment_text=segment_text,
                segment_index=segment_index,
                context=context,
                style_hints=style_hints,
                glossary=glossary
            )
            
            results.append({
                'segment_index': segment_index,
                'illustration_path': illustration_path,
                'prompt': prompt,
                'success': illustration_path is not None
            })
        
        return results

    def generate_character_bases(self,
                                 profile: Dict[str, Any],
                                 num_variations: int = 3,
                                 style_hints: str = "",
                                 reference_image: Optional[Tuple[bytes, str]] = None,
                                 context_text: Optional[str] = None,
                                 max_retries: int = 3) -> List[Dict[str, Any]]:
        """Generate N base character images focusing on appearance only.

        Returns a list of dicts: {index, path, prompt, success, type}
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
            "clean line art, flat colors, head-and-shoulders portrait",
            "soft painterly shading, bust portrait, subtle rim light",
            "semi-realistic rendering, three-quarter view waist-up, balanced studio lighting",
        ]

        for i in range(num_variations):
            vh = variant_directives[i % len(variant_directives)]
            prompt = self.create_character_base_prompt(profile, style_hints=(style_hints + f". {vh}").strip(), context_text=context_text)

            # File targets
            image_filename = f"base_{i+1:02d}.png"
            image_filepath = base_dir / image_filename
            json_filename = f"base_{i+1:02d}_prompt.json"
            json_filepath = base_dir / json_filename

            success = False
            generated_path: Optional[str] = None

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

                    response = self.client.models.generate_content(
                        model="gemini-2.5-flash-image-preview",
                        contents=contents
                    )

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

                    if image_generated:
                        success = True
                        generated_path = str(image_filepath)
                        break

                    # Fallback to prompt JSON
                    prompt_data = {
                        "index": i,
                        "prompt": prompt,
                        "status": "image_generation_failed",
                        "note": "Image generation failed. Use this prompt with another service."
                    }
                    with open(json_filepath, 'w', encoding='utf-8') as f:
                        json.dump(prompt_data, f, ensure_ascii=False, indent=2)
                    generated_path = str(json_filepath)
                    break
                except Exception as e:
                    logging.error(f"Base image attempt {attempt+1} failed: {e}")
                    if attempt == max_retries - 1:
                        generated_path = None
                        success = False
            results.append({
                'index': i,
                'illustration_path': generated_path,
                'prompt': prompt,
                'success': success,
                'type': 'image' if (generated_path and generated_path.endswith('.png')) else 'prompt',
                'used_reference': reference_image is not None
            })

        return results

    def generate_bases_from_prompts(
        self,
        prompts: List[str],
        reference_image: Optional[Tuple[bytes, str]] = None,
        max_retries: int = 3,
        num_variations: int = 3,
        add_variant_hints: bool = True
    ) -> List[Dict[str, Any]]:
        """Generate base images directly from provided prompts.

        Returns list of {index, illustration_path, prompt, success, type, used_reference}.
        """
        results: List[Dict[str, Any]] = []
        base_dir = self._setup_base_directory()

        # Cleanup previous base files for the targeted indices
        try:
            for i in range(1, len(prompts) + 1):
                for ext in ("png", "json"):
                    p = base_dir / f"base_{i:02d}.{ext}"
                    if p.exists():
                        p.unlink()
        except Exception as e:
            logging.warning(f"Failed to cleanup old base files: {e}")

        # Expand single prompt into multiple variant prompts if requested
        final_prompts: List[str]
        if len(prompts) == 1 and num_variations > 1:
            if add_variant_hints:
                variant_directives = [
                    "clean line art, flat colors, head-and-shoulders portrait",
                    "soft painterly shading, bust portrait, subtle rim light",
                    "semi-realistic rendering, three-quarter view waist-up, balanced studio lighting",
                ]
                final_prompts = [
                    (prompts[0].strip() + ". " + variant_directives[i % len(variant_directives)]).strip()
                    for i in range(num_variations)
                ]
            else:
                final_prompts = [prompts[0]] * num_variations
        else:
            final_prompts = prompts[:num_variations]

        for i, prompt in enumerate(final_prompts):
            image_filename = f"base_{i+1:02d}.png"
            image_filepath = base_dir / image_filename
            json_filename = f"base_{i+1:02d}_prompt.json"
            json_filepath = base_dir / json_filename

            success = False
            generated_path: Optional[str] = None

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

                    response = self.client.models.generate_content(
                        model="gemini-2.5-flash-image-preview",
                        contents=contents
                    )

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

                    if image_generated:
                        success = True
                        generated_path = str(image_filepath)
                        break

                    # Fallback: store prompt JSON
                    prompt_data = {
                        "index": i,
                        "prompt": prompt,
                        "status": "image_generation_failed",
                        "note": "Image generation failed. Use this prompt with another service."
                    }
                    with open(json_filepath, 'w', encoding='utf-8') as f:
                        json.dump(prompt_data, f, ensure_ascii=False, indent=2)
                    generated_path = str(json_filepath)
                    break
                except Exception as e:
                    logging.error(f"Base-from-prompt attempt {attempt+1} failed: {e}")
                    if attempt == max_retries - 1:
                        generated_path = None
                        success = False

            results.append({
                'index': i,
                'illustration_path': generated_path,
                'prompt': prompt,
                'success': success,
                'type': 'image' if (generated_path and generated_path.endswith('.png')) else 'prompt',
                'used_reference': reference_image is not None
            })

        return results
    
    def cleanup_old_illustrations(self, keep_days: int = 30):
        """
        Clean up old illustration files.
        
        Args:
            keep_days: Number of days to keep illustrations
        """
        import time
        from datetime import datetime, timedelta
        
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
            'illustrations': []
        }
        
        # Count illustrations
        for filepath in self.job_output_dir.glob("*.png"):
            metadata['total_illustrations'] += 1
            metadata['illustrations'].append({
                'filename': filepath.name,
                'path': str(filepath),
                'size': filepath.stat().st_size
            })
        
        if self.cache:
            metadata['cached_illustrations'] = len(self.cache)
        
        return metadata
