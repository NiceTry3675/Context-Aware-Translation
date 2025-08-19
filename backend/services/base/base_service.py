"""
Base Service

Common service functionality and patterns for backend services.
Provides shared initialization, error handling, and utility methods.
"""

import os
import traceback
from typing import Dict, Any, Union

from .model_factory import ModelAPIFactory
from ..utils.file_manager import FileManager
from core.config.loader import load_config
from core.translation.models.gemini import GeminiModel
from core.translation.models.openrouter import OpenRouterModel
from core.utils.text_segmentation import create_segments_for_text


class BaseService:
    """Base class for backend services providing common functionality."""
    
    def __init__(self):
        """Initialize base service."""
        self.config = load_config()
        self.file_manager = FileManager()
    
    def create_model_api(self, api_key: str, model_name: str) -> Union[GeminiModel, OpenRouterModel]:
        """
        Create a model API instance using the factory.
        
        Args:
            api_key: API key for the model service
            model_name: Name of the model to use
            
        Returns:
            Model API instance
        """
        return ModelAPIFactory.create_model(api_key, model_name, self.config)
    
    def validate_api_key(self, api_key: str, model_name: str) -> bool:
        """
        Validate API key using the factory.
        
        Args:
            api_key: API key to validate
            model_name: Model name to validate against
            
        Returns:
            True if valid, False otherwise
        """
        return ModelAPIFactory.validate_api_key(api_key, model_name)
    
    def handle_error(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """
        Handle errors consistently across services.
        
        Args:
            error: Exception that occurred
            context: Additional context information
            
        Returns:
            Error response dictionary
        """
        error_message = str(error)
        
        # Add context if provided
        if context:
            error_message = f"{context}: {error_message}"
        
        # Log the full traceback for debugging
        print(f"Error in {self.__class__.__name__}: {error_message}")
        print(traceback.format_exc())
        
        return {
            "error": error_message,
            "service": self.__class__.__name__,
            "context": context
        }
    
    def prepare_document_segments(self, filepath: str, method: str = "sentence", **kwargs) -> list:
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
    
    def save_structured_output(self, data: Dict[str, Any], filepath: str) -> None:
        """
        Save structured data to file.
        
        Args:
            data: Data to save
            filepath: File path to save to
        """
        import json
        
        self.file_manager.ensure_directory_exists(os.path.dirname(filepath))
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_structured_data(self, filepath: str) -> Dict[str, Any]:
        """
        Load structured data from file.
        
        Args:
            filepath: File path to load from
            
        Returns:
            Loaded data dictionary
        """
        import json
        
        if not self.file_manager.file_exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)


class BaseAnalysisService(BaseService):
    """Base class for analysis services (style, glossary, etc.)."""
    
    def analyze_document_sample(
        self, 
        filepath: str, 
        api_key: str, 
        model_name: str,
        sample_size: int = 15000
    ) -> Dict[str, Any]:
        """
        Base method for analyzing document samples.
        
        Args:
            filepath: Path to the document
            api_key: API key for the model
            model_name: Model name to use
            sample_size: Size of sample to analyze
            
        Returns:
            Analysis results dictionary
        """
        try:
            # Create model API
            model_api = self.create_model_api(api_key, model_name)
            
            # Prepare segments
            segments = self.prepare_document_segments(
                filepath, method="first_chars", count=sample_size
            )
            
            # Get filename for context
            filename = self.file_manager.get_filename_stem(filepath)
            
            return {
                "model_api": model_api,
                "segments": segments,
                "filename": filename,
                "sample_size": sample_size
            }
            
        except Exception as e:
            raise Exception(f"Failed to analyze document sample: {str(e)}")
    
    def validate_analysis_input(self, filepath: str, api_key: str, model_name: str) -> None:
        """
        Validate inputs for analysis operations.
        
        Args:
            filepath: Path to the document
            api_key: API key for the model
            model_name: Model name to use
            
        Raises:
            ValueError: If validation fails
        """
        if not filepath:
            raise ValueError("File path is required")
        
        if not self.file_manager.file_exists(filepath):
            raise ValueError(f"File not found: {filepath}")
        
        if not api_key:
            raise ValueError("API key is required")
        
        if not model_name:
            raise ValueError("Model name is required")
        
        if not self.validate_api_key(api_key, model_name):
            raise ValueError("Invalid API key for the specified model")