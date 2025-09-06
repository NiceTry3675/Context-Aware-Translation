"""Document analysis API endpoints - thin router layer."""

from fastapi import APIRouter, File, UploadFile, Form, Depends

from ...domains.analysis.schemas import StyleAnalysisResponse, GlossaryAnalysisResponse
from ...domains.analysis.service import AnalysisService

router = APIRouter(tags=["analysis"])


def get_analysis_service() -> AnalysisService:
    """Dependency to get analysis service instance."""
    return AnalysisService()


@router.post("/analyze-style", response_model=StyleAnalysisResponse)
async def analyze_style(
    file: UploadFile = File(...),
    api_key: str = Form(...),
    model_name: str = Form("gemini-2.5-flash-lite"),
    service: AnalysisService = Depends(get_analysis_service)
):
    """Analyze the narrative style of a document."""
    return await service.analyze_style(file, api_key, model_name)


@router.post("/analyze-glossary", response_model=GlossaryAnalysisResponse)
async def analyze_glossary(
    file: UploadFile = File(...),
    api_key: str = Form(...),
    model_name: str = Form("gemini-2.5-flash-lite"),
    service: AnalysisService = Depends(get_analysis_service)
):
    """Extract glossary terms from a document."""
    return await service.analyze_glossary(file, api_key, model_name)