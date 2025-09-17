"""Analysis domain service - consolidates all analysis operations."""

import os
from fastapi import HTTPException, UploadFile
from typing import Dict, Any, Optional

from ..shared.service_base import ServiceBase
from .style_analysis import StyleAnalysis
from .glossary_analysis import GlossaryAnalysis
from .character_analysis import CharacterAnalysis
from .schemas import StyleAnalysisResponse, GlossaryAnalysisResponse, CharacterAnalysisResponse


class AnalysisService(ServiceBase):
    """Service for document analysis operations."""
    
    def __init__(self):
        super().__init__()
    
    async def analyze_style(
        self,
        file: UploadFile,
        api_key: str,
        model_name: str = "gemini-2.5-flash-lite",
        api_provider: Optional[str] = None,
        vertex_project_id: Optional[str] = None,
        vertex_location: Optional[str] = None,
        vertex_service_account: Optional[str] = None
    ) -> StyleAnalysisResponse:
        """
        Analyze the narrative style of a document.
        
        Args:
            file: Uploaded file
            api_key: API key for analysis
            model_name: Model to use for analysis
            
        Returns:
            StyleAnalysisResponse with analysis results
            
        Raises:
            HTTPException: If API key invalid or analysis fails
        """
        model_api = self.validate_and_create_model(
            api_key,
            model_name,
            api_provider=api_provider,
            vertex_project_id=vertex_project_id,
            vertex_location=vertex_location,
            vertex_service_account=vertex_service_account,
        )
        
        try:
            # Save uploaded file temporarily
            temp_file_path, _ = self.file_manager.save_uploaded_file(file, file.filename)
            
            try:
                # Create StyleAnalysis instance with model API
                style_service = StyleAnalysis()
                style_service.set_model_api(model_api)
                
                # Call analyze_style
                style_result = style_service.analyze_style(
                    filepath=temp_file_path,
                    user_style_data=None
                )
                # Extract style_data for the response
                return StyleAnalysisResponse(**style_result['style_data'])
                
            finally:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                    
        except ValueError as e:
            self.raise_server_error(str(e))
        except Exception as e:
            self.raise_server_error(f"Failed to analyze style: {e}")
    
    async def analyze_glossary(
        self,
        file: UploadFile,
        api_key: str,
        model_name: str = "gemini-2.5-flash-lite",
        api_provider: Optional[str] = None,
        vertex_project_id: Optional[str] = None,
        vertex_location: Optional[str] = None,
        vertex_service_account: Optional[str] = None
    ) -> GlossaryAnalysisResponse:
        """
        Extract glossary terms from a document.
        
        Args:
            file: Uploaded file
            api_key: API key for analysis
            model_name: Model to use for analysis
            
        Returns:
            GlossaryAnalysisResponse with extracted terms
            
        Raises:
            HTTPException: If API key invalid or extraction fails
        """
        model_api = self.validate_and_create_model(
            api_key,
            model_name,
            api_provider=api_provider,
            vertex_project_id=vertex_project_id,
            vertex_location=vertex_location,
            vertex_service_account=vertex_service_account,
        )
        
        try:
            # Save uploaded file temporarily
            temp_file_path, _ = self.file_manager.save_uploaded_file(file, file.filename)
            
            try:
                # Create GlossaryAnalysis instance with model API
                glossary_service = GlossaryAnalysis()
                glossary_service.set_model_api(model_api)
                
                # Call analyze_glossary
                glossary_dict = glossary_service.analyze_glossary(
                    filepath=temp_file_path,
                    user_glossary_data=None
                )
                # Convert dictionary to frontend format
                frontend_glossary = [
                    {"term": term, "translation": translation}
                    for term, translation in glossary_dict.items()
                ]
                return GlossaryAnalysisResponse(glossary=frontend_glossary)
                
            finally:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                    
        except Exception as e:
            self.raise_server_error(f"Failed to extract glossary: {e}")
    
    async def analyze_characters(
        self,
        file: UploadFile,
        api_key: str,
        model_name: str = "gemini-2.5-flash-lite",
        api_provider: Optional[str] = None,
        vertex_project_id: Optional[str] = None,
        vertex_location: Optional[str] = None,
        vertex_service_account: Optional[str] = None
    ) -> CharacterAnalysisResponse:
        """
        Analyze characters in a document.
        
        Args:
            file: Uploaded file
            api_key: API key for analysis
            model_name: Model to use for analysis
            
        Returns:
            CharacterAnalysisResponse with character analysis results
            
        Raises:
            HTTPException: If API key invalid or analysis fails
        """
        model_api = self.validate_and_create_model(
            api_key,
            model_name,
            api_provider=api_provider,
            vertex_project_id=vertex_project_id,
            vertex_location=vertex_location,
            vertex_service_account=vertex_service_account,
        )
        
        try:
            # Save uploaded file temporarily
            temp_file_path, _ = self.file_manager.save_uploaded_file(file, file.filename)
            
            try:
                # Create CharacterAnalysis instance with model API
                character_service = CharacterAnalysis()
                character_service.set_model_api(model_api)
                
                # Call analyze_characters (would need to implement this method)
                # For now, return empty structure
                return CharacterAnalysisResponse(characters=[])
                
            finally:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                    
        except Exception as e:
            self.raise_server_error(f"Failed to analyze characters: {e}")
