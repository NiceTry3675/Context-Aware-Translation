"""
Style Analysis Service

This service handles all style-related analysis operations including:
- Narrative style detection
- Protagonist identification
- Style data parsing and formatting
"""

import json
from typing import Optional, Dict, Any
from pathlib import Path

from core.translation.style_analyzer import StyleAnalyzer
from .base.base_service import BaseAnalysisService


class StyleAnalysisService(BaseAnalysisService):
    """Service layer for style analysis operations."""
    
    def __init__(self):
        """Initialize style analysis service."""
        super().__init__()
    
    def analyze_style(
        self,
        filepath: str,
        api_key: str,
        model_name: str,
        user_style_data: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze and prepare style information for translation.
        
        Args:
            filepath: Path to the source file
            api_key: API key for the model
            model_name: Name of the model to use
            user_style_data: Optional user-provided style data as JSON string
            
        Returns:
            Dictionary containing:
                - protagonist_name: Identified protagonist name
                - style_text: Formatted style text for the engine
                - style_data: Parsed style dictionary
        """
        # Validate inputs
        self.validate_analysis_input(filepath, api_key, model_name)
        
        # Get model API instance
        model_api = self.create_model_api(api_key, model_name)
        
        # Create style analyzer
        style_analyzer = StyleAnalyzer(model_api)
        
        # Process user-provided style or perform automatic analysis
        if user_style_data:
            return self._process_user_style(
                user_style_data, style_analyzer
            )
        else:
            return self._perform_automatic_analysis(
                filepath, style_analyzer
            )
    
    def _process_user_style(
        self,
        user_style_data: str,
        style_analyzer: StyleAnalyzer
    ) -> Dict[str, Any]:
        """
        Process user-provided style data.
        
        Args:
            user_style_data: JSON string containing style data
            style_analyzer: StyleAnalyzer instance
            
        Returns:
            Dictionary with processed style information
        """
        try:
            style_dict = json.loads(user_style_data)
            protagonist_name = style_dict.get('protagonist_name', 'protagonist')
            style_text = style_analyzer.format_style_for_engine(
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
        style_analyzer: StyleAnalyzer
    ) -> Dict[str, Any]:
        """
        Perform automatic style analysis on the source file.
        
        Args:
            filepath: Path to the source file
            style_analyzer: StyleAnalyzer instance
            
        Returns:
            Dictionary with analyzed style information
        """
        # Extract sample text for analysis using base class utilities
        segments = self.prepare_document_segments(
            filepath, method="first_chars", count=15000
        )
        sample_text = '\n'.join(segments)
        
        # Get filename for logging
        filename = self.file_manager.get_filename_stem(filepath)
        
        # Analyze narrative style
        style_report_text = style_analyzer.analyze_narrative_style(
            sample_text, filename
        )
        
        # Parse the analysis
        parsed_style = style_analyzer.parse_style_analysis(style_report_text)
        
        # Extract protagonist name
        protagonist_name = parsed_style.get('protagonist_name', 'protagonist')
        
        # Format for engine
        style_text = style_analyzer.format_style_for_engine(
            parsed_style, protagonist_name
        )
        
        return {
            'protagonist_name': protagonist_name,
            'style_text': style_text,
            'style_data': parsed_style,
            'source': 'automatic_analysis'
        }
    
    def extract_protagonist_name(
        self,
        filepath: str,
        api_key: str,
        model_name: str
    ) -> str:
        """
        Extract only the protagonist name from a file.
        
        Args:
            filepath: Path to the source file
            api_key: API key for the model
            model_name: Name of the model to use
            
        Returns:
            Protagonist name or fallback value
        """
        try:
            result = self.analyze_style(
                filepath, api_key, model_name
            )
            return result['protagonist_name']
        except Exception as e:
            print(f"Warning: Could not extract protagonist name: {e}")
            # Fallback to filename-based name
            return self.file_manager.get_filename_stem(filepath)
    
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