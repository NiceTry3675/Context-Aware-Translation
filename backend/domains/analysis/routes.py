"""Analysis domain routes - plain async functions for business logic."""

from fastapi import UploadFile

from .service import AnalysisService
from .schemas import StyleAnalysisResponse, GlossaryAnalysisResponse, CharacterAnalysisResponse


async def analyze_style(
    file: UploadFile,
    api_key: str,
    model_name: str = "gemini-2.5-flash-lite"
) -> StyleAnalysisResponse:
    """
    Analyze the narrative style of a document.
    
    Args:
        file: Uploaded file to analyze
        api_key: API key for the AI model
        model_name: Model to use for analysis
        
    Returns:
        StyleAnalysisResponse with analysis results
    """
    service = AnalysisService()
    return await service.analyze_style(file, api_key, model_name)


async def analyze_glossary(
    file: UploadFile,
    api_key: str,
    model_name: str = "gemini-2.5-flash-lite"
) -> GlossaryAnalysisResponse:
    """
    Extract glossary terms from a document.
    
    Args:
        file: Uploaded file to analyze
        api_key: API key for the AI model
        model_name: Model to use for analysis
        
    Returns:
        GlossaryAnalysisResponse with extracted terms
    """
    service = AnalysisService()
    return await service.analyze_glossary(file, api_key, model_name)


async def analyze_characters(
    file: UploadFile,
    api_key: str,
    model_name: str = "gemini-2.5-flash-lite"
) -> CharacterAnalysisResponse:
    """
    Analyze characters in a document.
    
    Args:
        file: Uploaded file to analyze
        api_key: API key for the AI model
        model_name: Model to use for analysis
        
    Returns:
        CharacterAnalysisResponse with character analysis results
    """
    service = AnalysisService()
    return await service.analyze_characters(file, api_key, model_name)