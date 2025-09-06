"""Analysis domain routes - handles analysis-related operations."""

from fastapi import APIRouter, File, UploadFile, Form, Depends

from .service import AnalysisService
from .schemas import StyleAnalysisResponse, GlossaryAnalysisResponse, CharacterAnalysisResponse

router = APIRouter(prefix="/analysis", tags=["analysis"])


def get_analysis_service() -> AnalysisService:
    """Dependency to get analysis service instance."""
    return AnalysisService()


@router.post("/style", response_model=StyleAnalysisResponse)
async def analyze_style(
    file: UploadFile = File(...),
    api_key: str = Form(...),
    model_name: str = Form("gemini-2.5-flash-lite"),
    service: AnalysisService = Depends(get_analysis_service)
):
    """
    Analyze the narrative style of a document.
    
    Args:
        file: Uploaded file to analyze
        api_key: API key for the AI model
        model_name: Model to use for analysis
        service: Analysis service instance
        
    Returns:
        StyleAnalysisResponse with analysis results
    """
    return await service.analyze_style(file, api_key, model_name)


@router.post("/glossary", response_model=GlossaryAnalysisResponse)
async def analyze_glossary(
    file: UploadFile = File(...),
    api_key: str = Form(...),
    model_name: str = Form("gemini-2.5-flash-lite"),
    service: AnalysisService = Depends(get_analysis_service)
):
    """
    Extract glossary terms from a document.
    
    Args:
        file: Uploaded file to analyze
        api_key: API key for the AI model
        model_name: Model to use for analysis
        service: Analysis service instance
        
    Returns:
        GlossaryAnalysisResponse with extracted terms
    """
    return await service.analyze_glossary(file, api_key, model_name)


@router.post("/characters", response_model=CharacterAnalysisResponse)
async def analyze_characters(
    file: UploadFile = File(...),
    api_key: str = Form(...),
    model_name: str = Form("gemini-2.5-flash-lite"),
    service: AnalysisService = Depends(get_analysis_service)
):
    """
    Analyze characters in a document.
    
    Args:
        file: Uploaded file to analyze
        api_key: API key for the AI model
        model_name: Model to use for analysis
        service: Analysis service instance
        
    Returns:
        CharacterAnalysisResponse with character analysis results
    """
    return await service.analyze_characters(file, api_key, model_name)