"""
Glossary Analysis Module

This module handles all glossary-related operations including:
- Extracting key terms from source text
- Translating terms to target language
- Managing glossary updates during translation

Refactored from backend/services/glossary_analysis_service.py
"""

import json
import re
from typing import Optional, Dict, List, Any
from pathlib import Path

from core.config.glossary import GlossaryManager
from core.translation.models.gemini import GeminiModel
from core.config.loader import load_config
from core.utils.text_segmentation import create_segments_for_text


class GlossaryAnalysis:
    """Utility class for glossary analysis operations."""
    
    def __init__(self, model_api=None):
        """
        Initialize glossary analysis.
        
        Args:
            model_api: Optional pre-configured model API instance
        """
        self.config = load_config()
        self._model_api = model_api
        self._glossary_manager = None
    
    def set_model_api(self, model_api):
        """Set or update the model API instance."""
        self._model_api = model_api
        self._glossary_manager = None  # Reset manager when API changes
    
    def analyze_glossary(
        self,
        filepath: str,
        user_glossary_data: Optional[str] = None,
        sample_size: int = 15000
    ) -> Dict[str, str]:
        """
        Analyze and prepare glossary for translation.
        
        Args:
            filepath: Path to the source file
            user_glossary_data: Optional user-provided glossary as JSON string
            sample_size: Size of text sample to analyze for glossary extraction
            
        Returns:
            Dictionary mapping source terms to translations
        """
        # Process user-provided glossary if available
        if user_glossary_data:
            return self._process_user_glossary(user_glossary_data)
        
        # Validate inputs for automatic extraction
        if not filepath:
            raise ValueError("File path is required")
        
        if not Path(filepath).exists():
            raise ValueError(f"File not found: {filepath}")
        
        # Perform automatic extraction
        return self._extract_automatic_glossary(filepath, sample_size)
    
    def _process_user_glossary(self, user_glossary_data: str) -> Dict[str, str]:
        """
        Process user-provided glossary data.
        Supports multiple formats:
        1. Dictionary: {"term": "translation", ...}
        2. Array of objects with source/korean: [{"source": "term", "korean": "translation"}, ...]
        3. Array of objects with term/translation: [{"term": "term", "translation": "translation"}, ...]
        4. Array of single-key objects: [{"term": "translation"}, ...]
        
        Args:
            user_glossary_data: JSON string containing glossary
            
        Returns:
            Dictionary of term mappings
        """
        try:
            glossary = json.loads(user_glossary_data)
            validated_glossary = {}
            
            # Handle dictionary format
            if isinstance(glossary, dict):
                # Standard dictionary format {"term": "translation"}
                for key, value in glossary.items():
                    if not isinstance(key, str) or not isinstance(value, str):
                        print(f"Warning: Skipping invalid glossary entry: {key} -> {value}")
                        continue
                    validated_glossary[key] = value
            
            # Handle array formats
            elif isinstance(glossary, list):
                for item in glossary:
                    if not isinstance(item, dict):
                        print(f"Warning: Skipping non-dict item in glossary array: {item}")
                        continue
                    
                    # Format 1: {"source": "term", "korean": "translation"}
                    if "source" in item and "korean" in item:
                        term = item["source"]
                        translation = item["korean"]
                        if isinstance(term, str) and isinstance(translation, str):
                            validated_glossary[term] = translation
                        else:
                            print(f"Warning: Skipping invalid glossary entry: {term} -> {translation}")
                    
                    # Format 2: {"term": "term", "translation": "translation"}
                    elif "term" in item and "translation" in item:
                        term = item["term"]
                        translation = item["translation"]
                        if isinstance(term, str) and isinstance(translation, str):
                            validated_glossary[term] = translation
                        else:
                            print(f"Warning: Skipping invalid glossary entry: {term} -> {translation}")
                    
                    # Format 3: Single-key object {"term": "translation"}
                    elif len(item) == 1:
                        # Get the single key-value pair
                        term, translation = next(iter(item.items()))
                        if isinstance(term, str) and isinstance(translation, str):
                            validated_glossary[term] = translation
                        else:
                            print(f"Warning: Skipping invalid glossary entry: {term} -> {translation}")
                    
                    else:
                        print(f"Warning: Skipping glossary item with unrecognized format: {item}")
            
            else:
                raise ValueError(f"Glossary must be a dictionary or array, got {type(glossary).__name__}")
            
            print(f"Loaded user glossary with {len(validated_glossary)} terms")
            return validated_glossary
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid glossary JSON: {e}")
    
    def _extract_automatic_glossary(
        self,
        filepath: str,
        sample_size: int
    ) -> Dict[str, str]:
        """
        Automatically extract and translate glossary terms from source file.
        
        Args:
            filepath: Path to the source file
            sample_size: Size of text sample to analyze
            
        Returns:
            Dictionary of extracted term mappings
        """
        if self._model_api is None:
            raise ValueError("Model API not configured. Call set_model_api() first.")
        
        # Extract sample text
        segments = self._prepare_document_segments(
            filepath, method="first_chars", count=sample_size
        )
        sample_text = '\n'.join(segments)
        
        # Get filename for logging
        filename = Path(filepath).stem
        
        try:
            # Use structured-output capable models (Gemini natively, or routed via OpenRouter)
            if hasattr(self._model_api, 'generate_structured'):
                glossary_manager = GlossaryManager(self._model_api, filename)
            else:
                print("Warning: Selected model does not support structured output. Glossary extraction skipped.")
                return {}

            # Update glossary with the sample text
            glossary_dict = glossary_manager.update_glossary(sample_text)
            
            print(f"Extracted automatic glossary with {len(glossary_dict)} terms")
            return glossary_dict
            
        except Exception as e:
            print(f"Warning: Could not extract automatic glossary: {e}")
            return {}
    
    def _prepare_document_segments(
        self,
        filepath: str,
        method: str = "sentence",
        **kwargs
    ) -> list:
        """
        Prepare document segments for processing.
        
        Args:
            filepath: Path to the document
            method: Segmentation method to use
            **kwargs: Additional arguments for segmentation
            
        Returns:
            List of segments
        """
        try:
            if method == "first_chars":
                # Get the desired character count
                count = kwargs.get("count", 15000)
                # Create segments with target size
                segments = create_segments_for_text(filepath, target_size=count)
                # Return just the text content from the first segment(s) up to count chars
                result = []
                total_chars = 0
                for segment in segments:
                    if total_chars + len(segment.text) <= count:
                        result.append(segment.text)
                        total_chars += len(segment.text)
                    else:
                        # Add partial segment to reach count
                        remaining = count - total_chars
                        if remaining > 0:
                            result.append(segment.text[:remaining])
                        break
                return result
            else:
                # For sentence method, return all segment contents
                segments = create_segments_for_text(filepath)
                return [segment.text for segment in segments]
        except Exception as e:
            raise Exception(f"Failed to prepare document segments: {str(e)}")
    
    def merge_glossaries(
        self,
        base_glossary: Dict[str, str],
        new_glossary: Dict[str, str],
        prefer_new: bool = True
    ) -> Dict[str, str]:
        """
        Merge two glossaries, handling conflicts.
        
        Args:
            base_glossary: Existing glossary
            new_glossary: New glossary to merge
            prefer_new: If True, prefer new glossary values on conflict
            
        Returns:
            Merged glossary
        """
        if prefer_new:
            # New values override base
            merged = base_glossary.copy()
            merged.update(new_glossary)
        else:
            # Base values are preserved
            merged = new_glossary.copy()
            merged.update(base_glossary)
        
        return merged
    
    def filter_glossary_for_segment(
        self,
        full_glossary: Dict[str, str],
        segment_text: str
    ) -> Dict[str, str]:
        """
        Filter glossary to only include terms present in a segment.
        
        Args:
            full_glossary: Complete glossary
            segment_text: Text segment to check
            
        Returns:
            Filtered glossary relevant to the segment
        """
        filtered = {}
        for term, translation in full_glossary.items():
            # Check if term appears in segment (case-insensitive)
            if re.search(r'\b' + re.escape(term) + r'\b', segment_text, re.IGNORECASE):
                filtered[term] = translation
        
        return filtered
    
    def validate_glossary(self, glossary: Dict[str, str]) -> List[str]:
        """
        Validate glossary entries and return list of issues.
        
        Args:
            glossary: Glossary to validate
            
        Returns:
            List of validation issues (empty if valid)
        """
        issues = []
        
        # Check for empty glossary
        if not glossary:
            issues.append("Glossary is empty")
            return issues
        
        # Check for problematic entries
        for term, translation in glossary.items():
            if not term.strip():
                issues.append(f"Empty source term found")
            if not translation.strip():
                issues.append(f"Empty translation for term: {term}")
            if len(term) > 100:
                issues.append(f"Term too long (>100 chars): {term[:50]}...")
            if len(translation) > 200:
                issues.append(f"Translation too long (>200 chars) for: {term}")
        
        return issues
    
    def export_glossary_to_json(
        self,
        glossary: Dict[str, str],
        filepath: Optional[str] = None
    ) -> str:
        """
        Export glossary to JSON format.
        
        Args:
            glossary: Glossary to export
            filepath: Optional file path to save to
            
        Returns:
            JSON string representation
        """
        json_str = json.dumps(glossary, ensure_ascii=False, indent=2)
        
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(json_str)
            print(f"Glossary exported to: {filepath}")
        
        return json_str
    
    def import_glossary_from_json(
        self,
        json_str: Optional[str] = None,
        filepath: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Import glossary from JSON format.
        
        Args:
            json_str: JSON string to parse
            filepath: File path to read from
            
        Returns:
            Glossary dictionary
        """
        if filepath:
            with open(filepath, 'r', encoding='utf-8') as f:
                json_str = f.read()
        
        if not json_str:
            raise ValueError("No JSON string or filepath provided")
        
        glossary = json.loads(json_str)
        
        # Validate format
        if not isinstance(glossary, dict):
            raise ValueError("Glossary must be a dictionary")
        
        return glossary