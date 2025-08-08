"""Document analysis API endpoints."""

import os
from fastapi import APIRouter, File, UploadFile, Form, HTTPException

from ...services.translation_service import TranslationService
from ...schemas import StyleAnalysisResponse, GlossaryAnalysisResponse

router = APIRouter(tags=["analysis"])


@router.post("/analyze-style", response_model=StyleAnalysisResponse)
async def analyze_style(
    file: UploadFile = File(...),
    api_key: str = Form(...),
    model_name: str = Form("gemini-2.5-flash-lite"),
):
    """Analyze the narrative style of a document."""
    if not TranslationService.validate_api_key(api_key, model_name):
        raise HTTPException(status_code=400, detail="Invalid API Key or unsupported model.")
    
    try:
        temp_file_path, _ = TranslationService.save_uploaded_file(file.file, file.filename)
        
        try:
            parsed_style = TranslationService.analyze_style(
                temp_file_path, api_key, model_name, file.filename
            )
            return StyleAnalysisResponse(**parsed_style)
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
    if not TranslationService.validate_api_key(api_key, model_name):
        raise HTTPException(status_code=400, detail="Invalid API Key or unsupported model.")
    
    try:
        temp_file_path, _ = TranslationService.save_uploaded_file(file.file, file.filename)
        
        try:
            parsed_glossary = TranslationService.analyze_glossary(
                temp_file_path, api_key, model_name, file.filename
            )
            return GlossaryAnalysisResponse(glossary=parsed_glossary)
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract glossary: {e}")