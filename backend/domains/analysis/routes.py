"""Analysis domain routes - plain async functions for business logic."""

from fastapi import UploadFile, Form
from typing import Optional

from .service import AnalysisService
from .schemas import StyleAnalysisResponse, GlossaryAnalysisResponse, CharacterAnalysisResponse


async def analyze_style(
    file: UploadFile,
    api_key: str = Form(...),
    model_name: str = Form("gemini-2.5-flash-lite"),
    api_provider: Optional[str] = Form(None),
    vertex_project_id: Optional[str] = Form(None),
    vertex_location: Optional[str] = Form(None),
    vertex_service_account: Optional[str] = Form(None)
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
        model_name,
        api_provider=api_provider,
        vertex_project_id=vertex_project_id,
        vertex_location=vertex_location,
        vertex_service_account=vertex_service_account,
    )


async def analyze_glossary(
    file: UploadFile,
    api_key: str = Form(...),
    model_name: str = Form("gemini-2.5-flash-lite"),
    api_provider: Optional[str] = Form(None),
    vertex_project_id: Optional[str] = Form(None),
    vertex_location: Optional[str] = Form(None),
    vertex_service_account: Optional[str] = Form(None)
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
        model_name,
        api_provider=api_provider,
        vertex_project_id=vertex_project_id,
        vertex_location=vertex_location,
        vertex_service_account=vertex_service_account,
    )


async def analyze_characters(
    file: UploadFile,
    api_key: str = Form(...),
    model_name: str = Form("gemini-2.5-flash-lite"),
    api_provider: Optional[str] = Form(None),
    vertex_project_id: Optional[str] = Form(None),
    vertex_location: Optional[str] = Form(None),
    vertex_service_account: Optional[str] = Form(None)
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
        model_name,
        api_provider=api_provider,
        vertex_project_id=vertex_project_id,
        vertex_location=vertex_location,
        vertex_service_account=vertex_service_account,
    )
