"""Analysis domain routes - plain async functions for business logic."""

from typing import Optional

from fastapi import UploadFile, Form

from .service import AnalysisService
from .schemas import StyleAnalysisResponse, GlossaryAnalysisResponse, CharacterAnalysisResponse


async def analyze_style(
    file: UploadFile,
    api_key: str = Form(...),
    backup_api_keys: Optional[str] = Form(None),
    requests_per_minute: Optional[int] = Form(None),
    model_name: str = Form("gemini-flash-lite-latest"),
    api_provider: str = Form("gemini"),
    provider_config: Optional[str] = Form(None),
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
    return await service.analyze_style(
        file,
        api_key,
        backup_api_keys=backup_api_keys,
        requests_per_minute=requests_per_minute,
        model_name=model_name,
        api_provider=api_provider,
        provider_config=provider_config,
    )


async def analyze_glossary(
    file: UploadFile,
    api_key: str = Form(...),
    backup_api_keys: Optional[str] = Form(None),
    requests_per_minute: Optional[int] = Form(None),
    model_name: str = Form("gemini-flash-lite-latest"),
    api_provider: str = Form("gemini"),
    provider_config: Optional[str] = Form(None),
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
    return await service.analyze_glossary(
        file,
        api_key,
        backup_api_keys=backup_api_keys,
        requests_per_minute=requests_per_minute,
        model_name=model_name,
        api_provider=api_provider,
        provider_config=provider_config,
    )


async def analyze_characters(
    file: UploadFile,
    api_key: str = Form(...),
    backup_api_keys: Optional[str] = Form(None),
    requests_per_minute: Optional[int] = Form(None),
    model_name: str = Form("gemini-flash-lite-latest"),
    api_provider: str = Form("gemini"),
    provider_config: Optional[str] = Form(None),
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
    return await service.analyze_characters(
        file,
        api_key,
        backup_api_keys=backup_api_keys,
        requests_per_minute=requests_per_minute,
        model_name=model_name,
        api_provider=api_provider,
        provider_config=provider_config,
    )
