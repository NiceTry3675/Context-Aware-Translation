"""Document analysis API endpoints."""

import os
from fastapi import APIRouter, File, UploadFile, Form, HTTPException

from ...services.base.model_factory import ModelAPIFactory
from ...services.utils.file_manager import FileManager
from ...services.style_analysis_service import StyleAnalysisService
from ...services.glossary_analysis_service import GlossaryAnalysisService
from ...schemas import StyleAnalysisResponse, GlossaryAnalysisResponse

router = APIRouter(tags=["analysis"])


@router.post("/analyze-style", response_model=StyleAnalysisResponse)
async def analyze_style(
    file: UploadFile = File(...),
    api_key: str = Form(...),
    model_name: str = Form("gemini-2.5-flash-lite"),
):
    """Analyze the narrative style of a document."""
    if not ModelAPIFactory.validate_api_key(api_key, model_name):
        raise HTTPException(status_code=400, detail="Invalid API Key or unsupported model.")
    
    try:
        temp_file_path, _ = FileManager.save_uploaded_file(file, file.filename)
        
        try:
            style_service = StyleAnalysisService()
            style_result = style_service.analyze_style(
                filepath=temp_file_path,
                api_key=api_key,
                model_name=model_name,
                user_style_data=None
            )
            # Extract style_data for the response
            return StyleAnalysisResponse(**style_result['style_data'])
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze style: {e}")


@router.post("/analyze-glossary", response_model=GlossaryAnalysisResponse)
async def analyze_glossary(
    file: UploadFile = File(...),
    api_key: str = Form(...),
    model_name: str = Form("gemini-2.5-flash-lite"),
):
    """Extract glossary terms from a document."""
    if not ModelAPIFactory.validate_api_key(api_key, model_name):
        raise HTTPException(status_code=400, detail="Invalid API Key or unsupported model.")
    
    try:
        temp_file_path, _ = FileManager.save_uploaded_file(file, file.filename)
        
        try:
            glossary_service = GlossaryAnalysisService()
            glossary_dict = glossary_service.analyze_glossary(
                filepath=temp_file_path,
                api_key=api_key,
                model_name=model_name,
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
        raise HTTPException(status_code=500, detail=f"Failed to extract glossary: {e}")