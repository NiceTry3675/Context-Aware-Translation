"""Analysis domain service - consolidates all analysis operations."""

import os
import json
from fastapi import HTTPException, UploadFile
from typing import Any, Dict, Tuple

from ..shared.service_base import ServiceBase
from .style_analysis import StyleAnalysis
from .glossary_analysis import GlossaryAnalysis
from .character_analysis import CharacterAnalysis
from .schemas import StyleAnalysisResponse, GlossaryAnalysisResponse, CharacterAnalysisResponse


class AnalysisService(ServiceBase):
    """Service for document analysis operations."""
    
    def __init__(self):
        super().__init__()

    @staticmethod
    def _parse_backup_api_keys(raw: Any) -> list[str] | None:
        if raw is None:
            return None
        if isinstance(raw, list):
            keys = [str(k).strip() for k in raw if k and str(k).strip()]
            return keys or None
        if not isinstance(raw, str):
            raw = str(raw)
        text = raw.strip()
        if not text:
            return None
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                keys = [str(k).strip() for k in parsed if k and str(k).strip()]
                return keys or None
        except Exception:
            pass
        # Fallback: newline/comma separated
        keys = [k.strip() for k in text.replace(",", "\n").splitlines() if k.strip()]
        return keys or None
    
    def _prepare_model(
        self,
        api_key: str,
        backup_api_keys: Any,
        requests_per_minute: int | None,
        model_name: str,
        api_provider: str,
        provider_config: Any,
    ) -> Tuple[Any, Any, str]:
        """Parse provider context and instantiate the model API."""

        provider_context = self.build_provider_context(api_provider, provider_config)
        # Use provider-specific default models
        fallback_model = "gemini-flash-lite-latest"
        if provider_context and provider_context.name == "vertex":
            fallback_model = "gemini-flash-latest"
        elif provider_context and provider_context.name == "openrouter":
            fallback_model = "google/gemini-2.5-flash-lite-preview-09-2025"

        resolved_model = (
            model_name
            or provider_context.default_model
            or self.config.get("default_model", fallback_model)
        )

        model_api = self.validate_and_create_model(
            api_key,
            resolved_model,
            provider_context=provider_context,
            backup_api_keys=self._parse_backup_api_keys(backup_api_keys),
            requests_per_minute=requests_per_minute,
        )

        return model_api, provider_context, resolved_model

    async def analyze_style(
        self,
        file: UploadFile,
        api_key: str,
        model_name: str = "gemini-flash-lite-latest",
        *,
        backup_api_keys: Any = None,
        requests_per_minute: int | None = None,
        api_provider: str = "gemini",
        provider_config: Any = None,
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
        model_api, _, _ = self._prepare_model(
            api_key,
            backup_api_keys,
            requests_per_minute,
            model_name,
            api_provider,
            provider_config,
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
        model_name: str = "gemini-flash-lite-latest",
        *,
        backup_api_keys: Any = None,
        requests_per_minute: int | None = None,
        api_provider: str = "gemini",
        provider_config: Any = None,
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
        model_api, _, _ = self._prepare_model(
            api_key,
            backup_api_keys,
            requests_per_minute,
            model_name,
            api_provider,
            provider_config,
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
        model_name: str = "gemini-flash-lite-latest",
        *,
        backup_api_keys: Any = None,
        requests_per_minute: int | None = None,
        api_provider: str = "gemini",
        provider_config: Any = None,
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
        model_api, _, _ = self._prepare_model(
            api_key,
            backup_api_keys,
            requests_per_minute,
            model_name,
            api_provider,
            provider_config,
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
