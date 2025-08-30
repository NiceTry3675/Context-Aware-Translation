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
    
    def _get_cache_key(self, text: str, style_hints: str = "") -> str:
        """
        Generate a cache key for the given text and style hints.
        
        Args:
            text: The source text
            style_hints: Optional style hints
            
        Returns:
            MD5 hash as cache key
        """
        combined = f"{text}|||{style_hints}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def create_illustration_prompt(self, 
                                  segment_text: str, 
                                  context: Optional[str] = None,
                                  style_hints: str = "",
                                  glossary: Optional[Dict[str, str]] = None) -> str:
        """
        Create an illustration prompt from segment text.
        
        Args:
            segment_text: The text segment to illustrate
            context: Optional context from previous segments
            style_hints: Style preferences for the illustration
            glossary: Optional glossary for character/place names
            
        Returns:
            Generated prompt for image generation
        """
        # Extract key visual elements from the text
        prompt_parts = []
        
        # Analyze the segment for visual elements
        visual_elements = self._extract_visual_elements(segment_text, glossary)
        
        # Build a more descriptive, image-friendly prompt
        base_description = []
        
        # Start with setting
        if visual_elements['setting']:
            base_description.append(f"A scene in {visual_elements['setting']}")
        else:
            base_description.append("A scene")
        
        # Add characters with visual descriptions
        if visual_elements['characters']:
            if len(visual_elements['characters']) == 1:
                base_description.append(f"featuring {visual_elements['characters'][0]}")
            else:
                base_description.append(f"featuring {', '.join(visual_elements['characters'])}")
        
        # Add action
        if visual_elements['action']:
            base_description.append(f"with {visual_elements['action']}")
        
        # Add mood/atmosphere
        if visual_elements['mood']:
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
        
        # Extract characters from glossary if available
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
    
    def generate_illustration(self, 
                            segment_text: str,
                            segment_index: int,
                            context: Optional[str] = None,
                            style_hints: str = "",
                            glossary: Optional[Dict[str, str]] = None,
                            max_retries: int = 3) -> Tuple[Optional[str], Optional[str]]:
        """
        Generate an illustration for a text segment using Gemini's image generation.
        
        Args:
            segment_text: The text segment to illustrate
            segment_index: Index of the segment for naming
            context: Optional context from previous segments
            style_hints: Style preferences for the illustration
            glossary: Optional glossary for names
            max_retries: Maximum number of retry attempts
            
        Returns:
            Tuple of (image_file_path, prompt_used) or (None, None) on failure
        """
        # Check cache first
        if self.enable_caching:
            cache_key = self._get_cache_key(segment_text, style_hints)
            if cache_key in self.cache:
                cached_path = self.cache[cache_key]['path']
                cached_prompt = self.cache[cache_key]['prompt']
                if Path(cached_path).exists():
                    logging.info(f"Using cached illustration for segment {segment_index}")
                    return cached_path, cached_prompt
        
        # Generate the prompt
        prompt = self.create_illustration_prompt(segment_text, context, style_hints, glossary)
        
        # Generate the actual image using Gemini
        for attempt in range(max_retries):
            try:
                # Use Gemini's image generation model
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash-image-preview",
                    contents=[prompt]
                )
                
                # Extract the image from the response
                image_generated = False
                image_filename = f"segment_{segment_index:04d}.png"
                image_filepath = self.job_output_dir / image_filename
                
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
                    json_filename = f"segment_{segment_index:04d}_prompt.json"
                    json_filepath = self.job_output_dir / json_filename
                    
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
                if self.enable_caching:
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