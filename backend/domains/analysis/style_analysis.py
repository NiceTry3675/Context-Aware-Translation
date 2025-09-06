"""
Style Analysis Module

This module handles all style-related analysis operations including:
- Narrative style detection
- Protagonist identification
- Style data parsing and formatting

Refactored from backend/services/style_analysis_service.py
"""

import json
from typing import Optional, Dict, Any
from pathlib import Path

from core.translation.style_analyzer import StyleAnalyzer
from core.config.loader import load_config
from core.utils.text_segmentation import create_segments_for_text


class StyleAnalysis:
    """Utility class for style analysis operations."""
    
    def __init__(self, model_api=None):
        """
        Initialize style analysis.
        
        Args:
            model_api: Optional pre-configured model API instance
        """
        self.config = load_config()
        self._model_api = model_api
        self._style_analyzer = None
    
    def set_model_api(self, model_api):
        """Set or update the model API instance."""
        self._model_api = model_api
        self._style_analyzer = None  # Reset analyzer when API changes
    
    @property
    def style_analyzer(self) -> StyleAnalyzer:
        """Get or create StyleAnalyzer instance."""
        if self._style_analyzer is None:
            if self._model_api is None:
                raise ValueError("Model API not configured. Call set_model_api() first.")
            self._style_analyzer = StyleAnalyzer(self._model_api)
        return self._style_analyzer
    
    def analyze_style(
        self,
        filepath: str,
        user_style_data: Optional[str] = None,
        sample_size: int = 15000
    ) -> Dict[str, Any]:
        """
        Analyze and prepare style information for translation.
        
        Args:
            filepath: Path to the source file
            user_style_data: Optional user-provided style data as JSON string
            sample_size: Number of characters to sample for analysis
            
        Returns:
            Dictionary containing:
                - protagonist_name: Identified protagonist name
                - style_text: Formatted style text for the engine
                - style_data: Parsed style dictionary
                - source: 'user_provided' or 'automatic_analysis'
        """
        # Validate inputs
        if not filepath:
            raise ValueError("File path is required")
        
        if not Path(filepath).exists():
            raise ValueError(f"File not found: {filepath}")
        
        # Process user-provided style or perform automatic analysis
        if user_style_data:
            return self._process_user_style(user_style_data)
        else:
            return self._perform_automatic_analysis(filepath, sample_size)
    
    def _process_user_style(
        self,
        user_style_data: str
    ) -> Dict[str, Any]:
        """
        Process user-provided style data.
        
        Args:
            user_style_data: JSON string containing style data
            
        Returns:
            Dictionary with processed style information
        """
        try:
            style_dict = json.loads(user_style_data)
            protagonist_name = style_dict.get('protagonist_name', 'protagonist')
            style_text = self.style_analyzer.format_style_for_engine(
                style_dict, protagonist_name
            )
            
            return {
                'protagonist_name': protagonist_name,
                'style_text': style_text,
                'style_data': style_dict,
                'source': 'user_provided'
            }
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid style data JSON: {e}")
    
    def _perform_automatic_analysis(
        self,
        filepath: str,
        sample_size: int
    ) -> Dict[str, Any]:
        """
        Perform automatic style analysis on the source file.
        
        Args:
            filepath: Path to the source file
            sample_size: Number of characters to sample
            
        Returns:
            Dictionary with analyzed style information
        """
        # Extract sample text for analysis
        segments = self._prepare_document_segments(
            filepath, method="first_chars", count=sample_size
        )
        sample_text = '\n'.join(segments)
        
        # Get filename for logging
        filename = Path(filepath).stem
        
        # Analyze narrative style
        style_report_text = self.style_analyzer.analyze_narrative_style(
            sample_text, filename
        )
        
        # Parse the analysis
        parsed_style = self.style_analyzer.parse_style_analysis(style_report_text)
        
        # Extract protagonist name
        protagonist_name = parsed_style.get('protagonist_name', 'protagonist')
        
        # Format for engine
        style_text = self.style_analyzer.format_style_for_engine(
            parsed_style, protagonist_name
        )
        
        return {
            'protagonist_name': protagonist_name,
            'style_text': style_text,
            'style_data': parsed_style,
            'source': 'automatic_analysis'
        }
    
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
    
    def extract_protagonist_name(
        self,
        filepath: str
    ) -> str:
        """
        Extract only the protagonist name from a file.
        
        Args:
            filepath: Path to the source file
            
        Returns:
            Protagonist name or fallback value
        """
        try:
            result = self.analyze_style(filepath)
            return result['protagonist_name']
        except Exception as e:
            print(f"Warning: Could not extract protagonist name: {e}")
            # Fallback to filename-based name
            return Path(filepath).stem
    
    def validate_style_data(self, style_data: Dict[str, Any]) -> bool:
        """
        Validate that style data contains required fields.
        
        Args:
            style_data: Style data dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['protagonist_name']
        recommended_fields = [
            'narration_style_endings',
            'tone_keywords',
            'stylistic_rule'
        ]
        
        # Check required fields
        for field in required_fields:
            if field not in style_data or not style_data[field]:
                return False
        
        # Log warning for missing recommended fields
        missing_recommended = [
            f for f in recommended_fields 
            if f not in style_data or not style_data[f]
        ]
        if missing_recommended:
            print(f"Warning: Style data missing recommended fields: {missing_recommended}")
        
        return True
    
    def format_style_for_engine(
        self,
        style_data: Dict[str, Any],
        protagonist_name: str
    ) -> str:
        """
        Format style data for the translation engine.
        
        Args:
            style_data: Style data dictionary
            protagonist_name: Name of the protagonist
            
        Returns:
            Formatted style text
        """
        if not self.validate_style_data(style_data):
            raise ValueError("Invalid style data provided")
        
        return self.style_analyzer.format_style_for_engine(
            style_data, protagonist_name
        )