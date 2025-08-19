"""
Glossary Analysis Service

This service handles all glossary-related operations including:
- Extracting key terms from source text
- Translating terms to target language
- Managing glossary updates during translation
"""

import json
from typing import Optional, Dict, List, Any
from pathlib import Path

from core.translation.style_analyzer import StyleAnalyzer
from core.config.loader import load_config


class GlossaryAnalysisService:
    """Service layer for glossary analysis operations."""
    
    @staticmethod
    def analyze_glossary(
        filepath: str,
        api_key: str,
        model_name: str,
        user_glossary_data: Optional[str] = None,
        sample_size: int = 15000
    ) -> Dict[str, str]:
        """
        Analyze and prepare glossary for translation.
        
        Args:
            filepath: Path to the source file
            api_key: API key for the model
            model_name: Name of the model to use
            user_glossary_data: Optional user-provided glossary as JSON string
            sample_size: Size of text sample to analyze for glossary extraction
            
        Returns:
            Dictionary mapping source terms to translations
        """
        # Process user-provided glossary if available
        if user_glossary_data:
            return GlossaryAnalysisService._process_user_glossary(user_glossary_data)
        
        # Otherwise, perform automatic extraction
        return GlossaryAnalysisService._extract_automatic_glossary(
            filepath, api_key, model_name, sample_size
        )
    
    @staticmethod
    def _process_user_glossary(user_glossary_data: str) -> Dict[str, str]:
        """
        Process user-provided glossary data.
        
        Args:
            user_glossary_data: JSON string containing glossary
            
        Returns:
            Dictionary of term mappings
        """
        try:
            glossary = json.loads(user_glossary_data)
            
            # Validate glossary format
            if not isinstance(glossary, dict):
                raise ValueError("Glossary must be a dictionary mapping terms to translations")
            
            # Ensure all values are strings
            validated_glossary = {}
            for key, value in glossary.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    print(f"Warning: Skipping invalid glossary entry: {key} -> {value}")
                    continue
                validated_glossary[key] = value
            
            print(f"Loaded user glossary with {len(validated_glossary)} terms")
            return validated_glossary
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid glossary JSON: {e}")
    
    @staticmethod
    def _extract_automatic_glossary(
        filepath: str,
        api_key: str,
        model_name: str,
        sample_size: int
    ) -> Dict[str, str]:
        """
        Automatically extract and translate glossary terms from source file.
        
        Args:
            filepath: Path to the source file
            api_key: API key for the model
            model_name: Name of the model to use
            sample_size: Size of text sample to analyze
            
        Returns:
            Dictionary of extracted term mappings
        """
        from .translation_service import TranslationService
        
        # Get model API instance
        config = load_config()
        model_api = TranslationService.get_model_api(api_key, model_name, config)
        
        # Create style analyzer (which includes glossary methods)
        style_analyzer = StyleAnalyzer(model_api)
        
        # Extract sample text
        sample_text = style_analyzer.extract_sample_text(
            filepath, method="first_chars", count=sample_size
        )
        
        # Get filename for logging
        filename = Path(filepath).stem
        
        try:
            # Analyze glossary (extract and translate terms)
            glossary_text = style_analyzer.analyze_glossary(sample_text, filename)
            
            # Parse the results
            glossary_list = style_analyzer.parse_glossary_analysis(glossary_text)
            
            # Convert list format to dictionary
            glossary_dict = {}
            for item in glossary_list:
                if isinstance(item, dict) and 'source' in item and 'korean' in item:
                    glossary_dict[item['source']] = item['korean']
            
            print(f"Extracted automatic glossary with {len(glossary_dict)} terms")
            return glossary_dict
            
        except Exception as e:
            print(f"Warning: Could not extract automatic glossary: {e}")
            return {}
    
    @staticmethod
    def merge_glossaries(
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
    
    @staticmethod
    def filter_glossary_for_segment(
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
        import re
        
        filtered = {}
        for term, translation in full_glossary.items():
            # Check if term appears in segment (case-insensitive)
            if re.search(r'\b' + re.escape(term) + r'\b', segment_text, re.IGNORECASE):
                filtered[term] = translation
        
        return filtered
    
    @staticmethod
    def validate_glossary(glossary: Dict[str, str]) -> List[str]:
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
    
    @staticmethod
    def export_glossary_to_json(
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
    
    @staticmethod
    def import_glossary_from_json(
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